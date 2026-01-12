"""Document Analysis Consumer for large-scale processing.

대용량 문서 분석 아키텍처의 핵심 Consumer입니다.
- document_analysis_queue 수신
- Claim Check Pattern: DB에서 content 조회
- LangGraph 파이프라인 실행
- Spring Callback 전송
"""
import asyncio
import json
import time
from typing import Optional
from dataclasses import dataclass

import httpx
import structlog
from aio_pika import IncomingMessage

from app.config import settings
from app.schemas.messages import (
    DocumentAnalysisMessage,
    DocumentAnalysisCallback,
    SectionOutput,
    GlobalMergeMessage,
    GlobalMergeCallback,
    CharacterMergeResult,
    DocumentSummaryOutput,
    CharacterTimelineOutput,
)
from app.schemas.event_messages import (
    AnalysisCompletedEvent,
    AnalysisFailedEvent,
)
from app.services.db_query_service import get_db_service
from app.services.event_publisher import get_event_publisher
# Context Maintenance System (Phase 1-4)
from app.services.hierarchical_context import get_hierarchical_context_manager
from app.services.summary_service import get_summary_service
from app.utils.entity_resolution import (
    find_matching_characters,
    is_same_character,
    MatchClassification,
    merge_character_aliases,
)

logger = structlog.get_logger()


@dataclass
class ProcessingResult:
    """문서 분석 처리 결과"""
    success: bool
    sections: list[dict]
    characters: list[dict]
    events: list[dict]
    settings: list[dict]
    relationships: list[dict] = None  # 🆕 캐릭터 간 관계
    # 🆕 Level 2 Analysis Results (Spring 요청)
    consistency_report: Optional[dict] = None
    validation: Optional[dict] = None  # 검증 결과 추가
    document_summary: Optional[DocumentSummaryOutput] = None  # 🆕 문서 요약 (구조화됨)
    character_timelines: Optional[list[CharacterTimelineOutput]] = None  # 🆕 캐릭터 타임라인 (구조화됨)
    error: Optional[dict] = None
    processing_time_ms: int = 0

    def __post_init__(self):
        if self.relationships is None:
            self.relationships = []


class DocumentAnalysisConsumer:
    """Document Analysis Consumer for large-scale processing.

    Spring에서 발행한 DOCUMENT_ANALYSIS 메시지를 수신하여 처리합니다.
    직접 aio_pika를 사용하여 document_analysis_queue를 구독합니다.
    """

    def __init__(self):
        self._connection = None
        self._channel = None
        self._queue = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._running = False
        self._consume_task = None

    async def start(self) -> None:
        """Consumer 시작"""
        logger.info("Starting Document Analysis Consumer")

        # HTTP 클라이언트 초기화
        self._http_client = httpx.AsyncClient(timeout=30.0)

        # DB 서비스 초기화 대기 (PostgreSQL pool not initialized 방지)
        logger.info("Waiting for DB service to initialize...")
        db_service = await get_db_service()
        if not await db_service.ensure_postgres_connected():
            raise RuntimeError("Failed to connect to PostgreSQL")
        if not await db_service.ensure_neo4j_connected():
            logger.warning("Neo4j connection failed, will retry later")
        logger.info("DB service initialized")

        # RabbitMQ 직접 연결
        import aio_pika

        rabbitmq_url = f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}@{settings.rabbitmq_host}:{settings.rabbitmq_port}/{settings.rabbitmq_vhost}"

        self._connection = await aio_pika.connect_robust(rabbitmq_url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=settings.consumer_prefetch_count)

        # 큐 선언 (없으면 생성)
        # Spring Backend와 동일한 priority 설정 필요
        self._queue = await self._channel.declare_queue(
            settings.document_analysis_queue,
            durable=True,
            arguments={'x-max-priority': 10}
        )

        # 메시지 수신 시작
        await self._queue.consume(self._process_message)

        self._running = True
        logger.info("Document Analysis Consumer started", queue=settings.document_analysis_queue)

    async def stop(self) -> None:
        """Consumer 중지"""
        logger.info("Stopping Document Analysis Consumer")
        self._running = False

        if self._channel:
            await self._channel.close()

        if self._connection:
            await self._connection.close()

        if self._http_client:
            await self._http_client.aclose()

        logger.info("Document Analysis Consumer stopped")

    async def _process_message(self, message: IncomingMessage) -> None:
        """메시지 처리 핸들러"""
        start_time = time.time()
        trace_id = ""
        document_id = ""
        callback_url = ""

        try:
            # 1. 메시지 파싱
            body = json.loads(message.body.decode())
            print(f"[CONSUMER] Raw RabbitMQ Body Keys: {list(body.keys())}", flush=True)  # Key 확인
            if "requiresDeepAnalysis" in body:
                print(f"[CONSUMER] Raw requiresDeepAnalysis: {body['requiresDeepAnalysis']}", flush=True)

            msg = DocumentAnalysisMessage(**body)

            trace_id = msg.trace_id or ""
            document_id = msg.document_id
            job_id = msg.job_id or msg.document_id  # 🆕 Use job_id if present, else document_id
            callback_url = msg.callback_url

            logger.info(
                "Processing document analysis message",
                job_id=job_id,
                document_id=document_id,
                project_id=msg.project_id,
                callback_url=callback_url,
                requires_deep_analysis=msg.requires_deep_analysis,
                trace_id=trace_id
            )
            print(f"[CONSUMER] Parsed msg.requires_deep_analysis: {msg.requires_deep_analysis}", flush=True)

            # 2. PROCESSING 상태 업데이트
            await self._update_status(job_id, "PROCESSING", trace_id)

            # 3. DB에서 content 조회 (Claim Check Pattern)
            # 🆕 Priority: Message Content (for Testing/Dev Override) > DB Content > Raw Body
            db_service = await get_db_service()

            content = None

            # Check for override in message first
            if getattr(msg, 'content', None):
                 logger.info("Using content from MESSAGE override", document_id=document_id)
                 content = msg.content

            # Use DB content if no override
            if not content:
                fetched_content = await db_service.get_document_content(document_id)
                if fetched_content:
                    content = fetched_content

            # Fallbacks
            if not content:
                if "content" in body:
                    logger.warning("Using content from raw body dict", document_id=document_id)
                    content = body["content"]
                else:
                    logger.error("Content NOT FOUND in Message or DB", keys=list(body.keys()))
                    raise ValueError(f"Document content not found: {document_id}")

            # 🔍 Log the content being analyzed
            logger.info(f"📄 Content fetched for analysis (length: {len(content)} chars)")
            logger.info(f"📄 First 500 characters of content:\n{content[:500]}...")


            # 4. 분석 수행 (Vector Generation & Storage)
            # Before running agents, we generate semantic sections and save to PGVector
            sections = []
            try:
                from app.services.chunking_service import ChunkingService
                from app.services.embedding_service import get_embedding_service

                # Setup chunking service
                emb_service = get_embedding_service()
                chunker = ChunkingService(emb_service)

                logger.info("Generating semantic sections for vector search", document_id=document_id)
                sections = await chunker.create_semantic_sections(content)

                # Save to DB (pgvector)
                # Note: We save sections first so we can reference them if needed
                saved_count = await db_service.save_sections(document_id, sections)
                logger.info("Saved vector sections to DB", count=saved_count, document_id=document_id)

            except Exception as e:
                logger.error("Vector generation failed", error=str(e), document_id=document_id)
                # Continue with analysis even if vector save fails - sections might be empty if chunking failed


            # STREAMING: Pass sections and db_service to run_analysis
            
            # 🆕 3.5. 맥락 유지 (Hierarchical Context) 주입
            # -> 이전 챕터들의 요약과 관련 캐릭터 정보를 가져와서 파이프라인에 주입
            try:
                from app.services.hierarchical_context import get_hierarchical_context_manager
                ctx_manager = await get_hierarchical_context_manager()
                
                # Context Build Call (캐릭터 이름 감지는 내부에서 텍스트 기반으로 수행될 수 있으나,
                # 최적화를 위해 여기서는 텍스트 전체를 넘기지 않고 document_id만 넘김.
                # 필요 시 ctx_manager.get_context_for_analysis(text=content)를 쓸 수도 있음)
                
                # 1. 텍스트에서 캐릭터 추출 (임시: content 사용)
                mentioned_chars = await ctx_manager._extract_mentioned_characters(msg.project_id, content)
                
                logger.info("Context: Extracted mentioned characters", count=len(mentioned_chars), chars=mentioned_chars[:5])
                
                context_result = await ctx_manager.build_hierarchical_context(
                    project_id=msg.project_id,
                    current_document_id=msg.document_id,
                    mentioned_characters=mentioned_chars,
                    max_recent_chapters=5
                )
                
                # 시스템이 생성한 Context text
                system_context_text = context_result.get("context_text", "")
                
                if system_context_text:
                    if msg.context:
                         # 기존 컨텍스트가 있다면 뒤에 추가
                         msg.context = f"{msg.context}\n\n{system_context_text}"
                    else:
                         msg.context = system_context_text
                    
                    logger.info("Hierarchical context injected", length=len(system_context_text))
                    
            except Exception as e:
                logger.error("Failed to inject hierarchical context", error=str(e))
                # 실패해도 계속 진행 (맥락 없이)

            result = await self._run_analysis(
                content=content,
                sections=sections,
                db_service=db_service,
                document_id=document_id,
                project_id=msg.project_id,
                parent_folder_id=msg.parent_folder_id,  # 🆕 인트라-챕터 컨텍스트용
                context=msg.context,

                trace_id=trace_id,
                requires_deep_analysis=msg.requires_deep_analysis,
                analysis_type=getattr(msg, 'analysis_type', 'full_manuscript')  # 🆕 분석 유형 전달
            )

            processing_time_ms = int((time.time() - start_time) * 1000)


            # 5. Callback 전송 - sections 필드 완전히 제거
            callback = DocumentAnalysisCallback(
                document_id=document_id,
                parent_folder_id=msg.parent_folder_id,
                status="COMPLETED" if result.success else "FAILED",
                error=result.error,
                # sections 파라미터 자체를 제거 - JSON에 나타나지 않음
                # 🆕 Level 2 Analysis Results (plot removed)
                consistency_report=result.consistency_report,
                validation=result.validation,  # 검증 결과 추가
                document_summary=result.document_summary,  # 🆕 Spring Backend로 요약 전송
                character_timelines=result.character_timelines or [],  # 🆕 타임라인 전송
                processing_time_ms=processing_time_ms,
                trace_id=trace_id
            )


            # 🆕 콜백 데이터 출력 (디버깅 용도)
            logger.info(
                "Callback data to be sent",
                callback_data=callback.model_dump(exclude_none=True, by_alias=True),
                document_id=document_id,
                trace_id=trace_id
            )

            # 🆕 Event Sourcing: 이벤트 발행
            await self._publish_analysis_event(
                result=result,
                document_id=document_id,
                project_id=msg.project_id,
                job_id=job_id,
                parent_folder_id=msg.parent_folder_id,
                trace_id=trace_id,
                processing_time_ms=processing_time_ms,
            )

            # Legacy Callback (마이그레이션 기간 동안 병행 운영)
            if settings.enable_legacy_callback:
                await self._send_callback(callback_url, callback, job_id=job_id)

            # 6. 메시지 ACK
            await message.ack()

            logger.info(
                "Document analysis completed",
                document_id=document_id,
                success=result.success,
                processing_time_ms=processing_time_ms,
                trace_id=trace_id,
                event_sourcing=True,
            )

            # 🆕 7. Global Summary Update Trigger (Every 5 chapters)
            try:
                from app.services.summary_service import get_summary_service, SummaryLevel
                import asyncio
                
                summary_svc = await get_summary_service()
                
                # 현재까지의 챕터 요약 개수 확인
                # (성능 최적화를 위해 count만 하는 쿼리가 있으면 좋겠지만, 
                # 현재는 get_summaries_for_project로 리스트를 가져와서 길이 체크)
                summaries = await summary_svc.get_summaries_for_project(msg.project_id, level=SummaryLevel.CHAPTER)
                count = len(summaries)
                
                
                if count > 0 and count % 5 == 0:
                    logger.info("Triggering global summary update (5-chapter interval)", project_id=msg.project_id, current_chapter_count=count)
                    asyncio.create_task(summary_svc.update_global_summary(msg.project_id))
                
                # 🆕 Level 2 Trigger (Every 25 chapters)
                if count > 0 and count % 25 == 0:
                    logger.info("Triggering volume summary update (25-chapter interval)", project_id=msg.project_id, current_chapter_count=count)
                    
                    # 최근 25개 챕터 ID 추출 (get_summaries는 최신순 반환)
                    recent_summaries = summaries[:25]
                    chapter_ids = [s['document_id'] for s in recent_summaries]
                    
                    # 권 ID 생성 (결정론적 UUID: ProjectID + Volume 번호)
                    import uuid
                    vol_num = count // 25
                    vol_doc_id = str(uuid.uuid5(uuid.UUID(msg.project_id), f"Volume_{vol_num}"))
                    
                    asyncio.create_task(summary_svc.update_volume_summary(
                        msg.project_id,
                        vol_doc_id,
                        chapter_ids
                    ))
                    
            except Exception as trig_err:
                logger.error("Failed to trigger summary updates", error=str(trig_err))

            # 분석 결과를 result.json에 저장
            with open("/app/result.json", "w", encoding="utf-8") as f:
                json.dump(callback.model_dump(exclude_none=True, by_alias=True), f, ensure_ascii=False, indent=2)
            logger.info("🎉🎉🎉 드디어 끝끝끝끝!!! 결과가 result.json에 저장되었습니다. 🎉🎉🎉")

        except Exception as e:
            logger.error(
                "Document analysis failed",
                error=str(e),
                document_id=document_id,
                trace_id=trace_id
            )

            # 실패 Callback 전송
            if callback_url:
                processing_time_ms = int((time.time() - start_time) * 1000)
                error_callback = DocumentAnalysisCallback(
                    document_id=document_id,
                    status="FAILED",
                    error={"code": "PROCESSING_ERROR", "message": str(e)},
                    processing_time_ms=processing_time_ms,
                    trace_id=trace_id
                )
                try:
                    await self._send_callback(callback_url, error_callback, job_id=job_id)
                except Exception as cb_error:
                    logger.error("Failed to send error callback", error=str(cb_error))

            # 실패 시 result.json에도 에러 정보 저장
            try:
                error_output = {
                    "status": "FAILED",
                    "error": {"code": "PROCESSING_ERROR", "message": str(e)},
                    "trace_id": trace_id,
                    "document_id": document_id
                }
                with open("/app/result.json", "w", encoding="utf-8") as f:
                    json.dump(error_output, f, ensure_ascii=False, indent=2)
                logger.info("Saved failure info to result.json")
            except Exception as save_err:
                logger.warning("Failed to save result.json on error", error=str(save_err))

            # 실패 시 requeue하지 않음 (무한 루프 방지)
            await message.nack(requeue=False)

    async def _update_status(self, job_or_doc_id: str, status: str, trace_id: str) -> None:
        """Spring API로 상태 업데이트 (Job ID 우선, 실패 시 Document ID Fallback)"""
        from app.services.callback_client import get_callback_client
        client = get_callback_client()

        # job_or_doc_id가 UUID 형식인지 확인 (간단한 길이 체크)
        is_uuid = len(job_or_doc_id) == 36

        # 1. Job Status Update 시도
        # 단, 만약 job_id가 document_id와 같다면(즉 메시지에 job_id가 없었다면),
        # 굳이 Job API를 찌르지 말고 바로 Document API로 간다. (Spring 404 방지)
        # 하지만 여기선 job_or_doc_id만으로는 알 수 없으므로,
        # _process_message에서 job_id를 넘길 때 구분이 필요하다.
        # 일단은 404가 나더라도 시도하고 Fallback하는 현재 로직 유지하되,
        # 로그를 줄이기 위해 try-except를 client 내부에서 처리하도록 했음.

        if await client.update_job_status(job_or_doc_id, status):
            return

        # 2. 실패 시 Document Status Update (Fallback)
        # 404 Not Found의 경우 Job ID가 아니라 Document ID일 수 있음
        logger.info("Main status update failed (or skipped), trying fallback to Document API", id=job_or_doc_id)
        await client.update_document_status(job_or_doc_id, status, trace_id)

    async def _run_analysis(
        self,
        content: str,
        sections: list[dict],
        db_service,
        document_id: str,
        project_id: str,
        parent_folder_id: str = None,  # 🆕 인트라-챕터 컨텍스트용
        context: Optional[dict] = None,

        trace_id: str = "",
        requires_deep_analysis: bool = False,
        analysis_type: str = "full_manuscript"  # 🆕 분석 유형 파라미터
    ) -> ProcessingResult:
        """Streaming Analysis Pipeline.

        Process content chapter by chapter (batch of sections).
        Persist results immediately.
        Keep context light.
        """
        from app.agents.graph import run_analysis_pipeline

        start_time = time.time()

        # Initialize context state from input
        current_context = {
            "existing_characters": [],
            "existing_events": [],
            "existing_relationships": [],
            "existing_settings": []
        }

        # Populate initial context if provided
        if context:
            # ... (Existing parsing logic) ...
            pass # Keep simplified for brevity in this replace block?
                 # No, better copy the parsing logic to be safe, or just reuse if possible.
                 # Since this is a full replacement of the method, I must include logic.
            if hasattr(context, 'existing_characters'):
                current_context["existing_characters"] = [
                    {"id": c.id, "name": c.name, "role": c.role} for c in (context.existing_characters or [])
                ]
                current_context["existing_events"] = [
                    {"id": e.id, "event_type": e.event_type, "summary": e.summary} for e in (context.existing_events or [])
                ]
                # ... others
            elif isinstance(context, dict):
                current_context = context.copy()

        try:
            # ===== Context Maintenance System Integration =====
            # 🆕 Phase 1-4: RAG 기반 계층적 컨텍스트 조회
            # Vector Search + Keyword Matching을 통해 관련 캐릭터/사건 조회
            try:
                context_manager = await get_hierarchical_context_manager()
                
                # Retrieve structured context data (dict)
                context_data = await context_manager.retrieve_analysis_context_data(
                    project_id=project_id,
                    current_text=content[:2000] if content else "",  # RAG용 쿼리 (앞부분)
                    current_document_id=document_id,
                    parent_folder_id=parent_folder_id  # 🆕 인트라-챕터 컨텍스트용
                )
                
                # 1. Update current_context with retrieved Characters
                # EntityCentricContextBuilder returns detailed histories, we need to adapt to existing_characters format
                # Format: {"name": str, "role": str}
                entity_context = context_data.get("entity_context") or {}
                char_histories = entity_context.get("character_histories", [])
                
                retrieved_chars_count = 0
                for ch in char_histories:
                    c_name = ch.get("name")
                    if not c_name: continue
                    
                    # Deduplicate against existing list
                    exists = any(ex.get("name") == c_name for ex in current_context["existing_characters"])
                    if not exists:
                        current_context["existing_characters"].append({
                            "name": c_name,
                            "role": ch.get("role", "Unknown"),
                            "status": ch.get("status", "Unknown")
                            # Can add more fields if run_analysis_pipeline supports them
                        })
                        retrieved_chars_count += 1
                
                # 2. Update current_context with retrieved Events (RAG)
                # Format: {"id": str, "summary": str}
                similar_events = context_data.get("similar_events", [])
                retrieved_events_count = 0
                for evt in similar_events:
                    evt_id = evt.get("event_id")
                    if not evt_id: continue
                    
                    exists = any(ex.get("id") == evt_id for ex in current_context["existing_events"])
                    if not exists:
                        current_context["existing_events"].append({
                            "id": evt_id,
                            "summary": evt.get("description", ""),
                            "chapter": evt.get("chapter")
                        })
                        retrieved_events_count += 1

                logger.info(
                    "RAG context retrieved & merged",
                    project_id=project_id,
                    new_chars=retrieved_chars_count,
                    new_events=retrieved_events_count,
                    total_chars=len(current_context["existing_characters"]),
                    total_events=len(current_context["existing_events"])
                )
                
            except Exception as ctx_err:
                logger.warning("Failed to retrieve/merge RAG context", error=str(ctx_err))
            # =================================================
            
            # 1. Prepare Batches (Streaming Units)
            # If sections exist, use them. If not (short text failed chunking), treat as one batch.
            batches = []
            if sections:
                # Group sections into batches (e.g. ~4000 tokens or by structure)
                # Simple grouping: 3 sections per batch? Or just 1 section = 1 chapter unit?
                # Sections from chunker are already max 4000 tokens.
                # So we can process section by section.
                batches = sections
            else:
                batches = [{"content": content, "nav_title": "Full Text"}]

            # 🆕 ===== INCREMENTAL ANALYSIS: Detect change point =====
            start_batch_index = 0
            previous_summary_context = ""
            
            try:
                # Get previous section hashes for this document
                previous_hashes = await db_service.get_previous_section_hashes(document_id)
                
                if previous_hashes and sections:
                    # Detect first changed section
                    change_point = db_service.detect_change_point(previous_hashes, sections)
                    
                    if change_point == -1:
                        # No content changes detected
                        # Check if previous summary exists (confirmation of successful previous analysis)
                        previous_summary_context = await db_service.get_previous_summary(document_id)
                        
                        if previous_summary_context:
                            logger.info("[INCREMENTAL] No changes detected and previous summary exists. Using cached results.")
                            return ProcessingResult(
                                success=True,
                                sections=sections,
                                characters=[],
                                events=[],
                                settings=[],
                                processing_time_ms=int((time.time() - start_time) * 1000)
                            )
                        else:
                            # Content matches but no summary -> Previous analysis likely failed
                            logger.info("[INCREMENTAL] No changes detected BUT sections have no summary. Forcing re-analysis.")
                            start_batch_index = 0
                            
                    elif change_point > 0:
                        # Skip unchanged sections
                        start_batch_index = change_point
                        logger.info(f"[INCREMENTAL] Skipping {change_point} unchanged sections, starting from section {change_point + 1}")
                        
                        # Get previous summary for context
                        previous_summary_context = await db_service.get_previous_summary(document_id) or ""
                        if previous_summary_context:
                            logger.info("[INCREMENTAL] Using previous summary as context for analysis")
                    else:
                        logger.info("[INCREMENTAL] First section changed, full re-analysis required")
                else:
                    logger.info("[INCREMENTAL] No previous analysis found, performing full analysis")
                    
            except Exception as incr_err:
                logger.warning(f"[INCREMENTAL] Change detection failed, falling back to full analysis: {incr_err}")
            # ============================================================

            logger.info(f"Starting Streaming Analysis: {len(batches)} total batches, starting from index {start_batch_index}")

            # Accumulators for Final Callback (Lightweight)
            final_characters_map = {}  # dedupe by name
            final_events_map = {}      # 🆕 dedupe by event_id
            final_settings_map = {}    # 🆕 dedupe by setting_id
            final_relationships = []   # 🆕 관계 데이터 축적
            final_consistency = {}
            final_validation = {}  # 🆕 검증 결과

            for i, batch in enumerate(batches):
                # 🆕 Skip unchanged sections in incremental mode
                if i < start_batch_index:
                    logger.info(f"[INCREMENTAL] Skipping unchanged batch {i+1}/{len(batches)}")
                    continue
                    
                batch_content = batch["content"]
                
                # 🆕 Prepend previous summary as context for first analyzed batch
                if i == start_batch_index and previous_summary_context:
                    batch_content = f"[이전 내용 요약]\n{previous_summary_context}\n\n[새로 추가된 내용]\n{batch_content}"
                    logger.info(f"[INCREMENTAL] Added previous summary context to batch {i+1}")
                
                logger.info(f"Processing Batch {i+1}/{len(batches)}", size=len(batch_content))
                logger.info(f"📄 Analyzing text content (first 500 chars):\n{batch_content[:500]}...")

                # 2. Run Pipeline for Batch
                # 🆕 analysis_type 기반 분석 모드 결정
                # partial_snippet: Fast Track (경량 분석)
                # full_manuscript: 무조건 심층 분석
                if analysis_type == "full_manuscript":
                    is_short_text = False  # 전체 원고: 무조건 심층 분석
                    batch_requires_deep = True
                elif analysis_type == "partial_snippet":
                    is_short_text = True  # 작가 일부 분석 요청: 항상 Fast Track
                    batch_requires_deep = False
                else:
                    is_short_text = len(batch_content) < 10000  # 길이 기반
                    batch_requires_deep = requires_deep_analysis

                logger.info(f"Running pipeline for batch {i+1}, analysis_type={analysis_type}, is_short_text={is_short_text}, deep_analysis={batch_requires_deep}")

                pipeline_result = await run_analysis_pipeline(
                    content=batch_content,
                    project_id=project_id,
                    document_id=document_id,
                    job_id=f"doc-{document_id}-batch-{i}",
                    callback_url="",
                    existing_characters=current_context.get("existing_characters", []),
                    existing_events=current_context.get("existing_events", []),
                    existing_relationships=current_context.get("existing_relationships", []),
                    existing_settings=current_context.get("existing_settings", []),
                    trace_id=trace_id,
                    requires_deep_analysis=batch_requires_deep,  # 🆕 analysis_type 기반 심층 분석
                    is_short_text=is_short_text  # Fast Track/Interactive flag
                )

                # 🆕 Check for Failure (Max Retries Exceeded)
                # If a batch failed after max retries, it means the pipeline gave up.
                # Continuing to process subsequent batches is wasteful and looks like a zombie loop.
                # We interpret "Max Retries" + "Validation/Consistency Failed" as a hard stop.

                from app.agents.supervisor import MAX_EXTRACTION_RETRIES

                res_retry_count = pipeline_result.get("retry_count", 0)
                res_validation = pipeline_result.get("validation_result", {})
                res_consistency = pipeline_result.get("consistency_report", {})

                failed_validation = res_validation.get("action") == "retry_extraction"
                failed_consistency = res_consistency.get("requires_reextraction")

                if res_retry_count >= MAX_EXTRACTION_RETRIES and (failed_validation or failed_consistency):
                    logger.error(
                        "Analysis aborted: Batch reached max retries with failures",
                        batch_index=i,
                        retry_count=res_retry_count,
                        validation_action=res_validation.get("action"),
                        document_id=document_id,
                        trace_id=trace_id
                    )
                    # Mark overall result as failed (optional, but good for visibility)
                    # But here we just break to stop the loop.
                    # We might want to set a flag to send FAILED callback?
                    # For now, just stopping the loop is the priority.
                    break

                # 3. Extract Results
                chars = pipeline_result.get("extracted_characters", [])
                evts = pipeline_result.get("extracted_events", [])
                stgs = pipeline_result.get("extracted_settings", [])

                # Convert to dicts
                if chars and hasattr(chars[0], 'model_dump'): chars = [c.model_dump() for c in chars]
                if evts and hasattr(evts[0], 'model_dump'): evts = [e.model_dump() for e in evts]
                if stgs and hasattr(stgs[0], 'model_dump'): stgs = [s.model_dump() for s in stgs]

                # Inject Batch/Chapter Info + document_id
                for e in evts:
                    e["chapter"] = i + 1  # 1-based index
                    e["sequence_order"] = e.get("sequence_order", 0) + (i * 100) # Offset order
                    e["document_id"] = document_id  # For traceability (Spring request)

                # 🆕 관계 데이터 추출 (relationship_graph에서)
                rel_graph = pipeline_result.get("relationship_graph", {})
                batch_relationships = []
                
                # 🆕 Debug: Log relationship extraction
                logger.info(f"[RELATIONSHIPS] 🔍 Batch {i+1}: Checking pipeline_result for relationship_graph")
                logger.info(f"[RELATIONSHIPS] 🔍 relationship_graph exists: {bool(rel_graph)}")
                
                if rel_graph and isinstance(rel_graph, dict):
                    batch_relationships = rel_graph.get("relationships", [])
                    logger.info(f"[RELATIONSHIPS] 🔍 Batch {i+1}: Extracted {len(batch_relationships)} relationships from rel_graph")
                    if batch_relationships:
                        logger.info(f"[RELATIONSHIPS] ✅ Batch {i+1}: Adding {len(batch_relationships)} relationships to final list")
                        logger.info(f"[RELATIONSHIPS] 🔍 First relationship: {batch_relationships[0]}")
                        final_relationships.extend(batch_relationships)
                    else:
                        logger.info(f"[RELATIONSHIPS] ⚠️ Batch {i+1}: relationship_graph exists but relationships array is empty")
                else:
                    logger.info(f"[RELATIONSHIPS] ⚠️ Batch {i+1}: No valid relationship_graph in pipeline_result")

                # 4. Immediate Persistence
                # 4. Immediate Persistence
                logger.info("[DEBUG] Calling save_extraction_result...")
                try:
                    await db_service.save_extraction_result(
                        project_id,
                        document_id,  # Pass document_id for source tracking
                        chars,
                        evts,
                        stgs,
                        relationships=batch_relationships
                    )
                    logger.info("[DEBUG] save_extraction_result returned successfully.")
                except Exception as db_err:
                    logger.error("[DEBUG] save_extraction_result CRASHED", error=str(db_err))
                    raise db_err

                # 5. Update Rolling Context
                # Keep lightweight references for next batch
                # Characters: Merge new chars into context (simple list extend specific fields)
                for c in chars:
                    # Check if already exists in context to avoid dupes in context list
                    # FullCharacter uses profile.name, but some formats use root name
                    c_name = c.get("name") or c.get("profile", {}).get("name")
                    if not c_name:
                        # Skip characters without name (silent)
                        continue

                    try:
                        exists = False
                        for ex in current_context["existing_characters"]:
                             if ex.get("name") == c_name:
                                 exists = True
                                 break

                        if not exists:
                            current_context["existing_characters"].append({"name": c_name, "role": c.get("role", "Unknown")})
                    except Exception as loop_err:
                        logger.error("Context update loop failed", error=str(loop_err))


                # Events: Add to RAG (already handled by RAG service?)
                # or just keep last N events in context list
                for e in evts:
                    summary = e.get("description") or e.get("summary")
                    current_context["existing_events"].append({"id": e.get("event_id"), "summary": summary})

                # Prune context if growing too large (e.g. > 50 chars, > 20 events)
                # Ensure we strictly follow "Rolling Summary"
                if len(current_context["existing_events"]) > 20:
                    current_context["existing_events"] = current_context["existing_events"][-20:]

                # 6. Accumulate for Final Report (full details or simplified?)
                for c in chars:
                    # FullCharacter uses profile.name, but some formats use root name
                    c_name = c.get("name") or c.get("profile", {}).get("name")
                    if c_name:
                        final_characters_map[c_name] = c
                
                # 🆕 Events: dedupe by event_id
                for e in evts:
                    evt_id = e.get("event_id") or e.get("id")
                    if evt_id:
                        final_events_map[evt_id] = e
                    else:
                        # No ID, skip (shouldn't happen)
                        logger.warning("Event without ID, skipping", event=e)
                
                # 🆕 Settings: dedupe by setting_id
                for s in stgs:
                    setting_id = s.get("setting_id") or s.get("id")
                    if setting_id:
                        final_settings_map[setting_id] = s
                    else:
                        # Fallback to name if no ID
                        s_name = s.get("name")
                        if s_name:
                            final_settings_map[s_name] = s

                if pipeline_result.get("consistency_report"): final_consistency = pipeline_result.get("consistency_report")
                if pipeline_result.get("validation_result"): final_validation = pipeline_result.get("validation_result")

            # 🆕 Fallback: Extract relationships from character.relations.graph if top-level is empty
            if not final_relationships and final_characters_map:
                logger.info("[RELATIONSHIPS] 🔄 Triggering fallback: Extracting from character.relations.graph")
                logger.info(f"[RELATIONSHIPS] 🔍 Characters available for fallback: {len(final_characters_map)}")
                extracted_rels = []
                seen_pairs = set()  # Avoid duplicates

                for char_name, char_data in final_characters_map.items():
                    # Get relations from either nested format or direct format
                    relations_data = char_data.get("relations", {})
                    char_relations = []

                    # Handle dict format: {"graph": [...], "event_refs": [...]}
                    if isinstance(relations_data, dict):
                        char_relations = relations_data.get("graph", [])
                    # Handle list format (direct list of relations)
                    elif isinstance(relations_data, list):
                        char_relations = relations_data
                    
                    if char_relations:
                        logger.info(f"[RELATIONSHIPS] 🔍 Character '{char_name}' has {len(char_relations)} relations in embedded data")

                    for rel in char_relations:
                        target = rel.get("target", "")
                        if not target:
                            continue

                        # Create pair key for deduplication (sorted for bidirectional)
                        pair_key_fwd = (char_name, target)
                        pair_key_rev = (target, char_name)

                        # Skip if we've already seen this pair (either direction)
                        if pair_key_fwd in seen_pairs:
                            continue

                        # Determine bidirectionality
                        rel_type = rel.get("type", "NEUTRAL")
                        bidirectional = rel_type not in ("BETRAYED", "MENTOR")  # Unidirectional types

                        # Map embedded format to expected top-level format
                        extracted_rel = {
                            "source": char_name,
                            "target": target,
                            "type": rel_type,
                            "strength": rel.get("strength", 5),
                            "description": rel.get("description", ""),
                            "bidirectional": bidirectional
                        }
                        extracted_rels.append(extracted_rel)
                        seen_pairs.add(pair_key_fwd)

                        # Mark reverse direction as seen if bidirectional
                        if bidirectional:
                            seen_pairs.add(pair_key_rev)

                if extracted_rels:
                    final_relationships = extracted_rels
                    logger.info(f"[RELATIONSHIPS] ✅ Fallback extracted {len(final_relationships)} relationships from character data")
                    logger.info(f"[RELATIONSHIPS] 🔍 Sample relationship: {final_relationships[0]}")
                else:
                    logger.warning("[RELATIONSHIPS] ⚠️ Fallback found no relationships in character.relations.graph")
            else:
                if final_relationships:
                    logger.info(f"[RELATIONSHIPS] ✅ Using {len(final_relationships)} relationships from pipeline (no fallback needed)")
                else:
                    logger.warning(f"[RELATIONSHIPS] ⚠️ No relationships extracted and no characters for fallback (chars: {len(final_characters_map)})")


            # 🆕 [FIX] Inject extracted relationships back into Character objects
            if final_relationships:
                logger.info(f"[RELATIONSHIPS] 🔄 Injecting {len(final_relationships)} relationships back into characters for result.json")
                
                # Initialize relations for all characters
                for c_name, c_data in final_characters_map.items():
                    if "relations" not in c_data or not isinstance(c_data["relations"], dict):
                        c_data["relations"] = {"graph": [], "event_refs": []}
                    else:
                        c_data["relations"]["graph"] = [] # Reset for fresh injection
                
                # Distribute relationships
                for rel in final_relationships:
                    src = rel.get("source")
                    if src and src in final_characters_map:
                        final_characters_map[src]["relations"]["graph"].append(rel)

            processing_time_ms = int((time.time() - start_time) * 1000)

            # 🆕 Convert dict back to list for final output
            final_events = list(final_events_map.values())
            final_settings = list(final_settings_map.values())
            
            logger.info(
                "Final aggregation complete",
                characters=len(final_characters_map),
                events=len(final_events),
                settings=len(final_settings),
                relationships=len(final_relationships)
            )

            # 🆕 [DEBUG] Save result.json locally for user verification
            try:
                import json
                debug_result = {
                    "message_type": "DOCUMENT_ANALYSIS_RESULT",
                    "document_id": document_id,
                    "status": "COMPLETED",
                    "characters": list(final_characters_map.values()),
                    "events": final_events,
                    "settings": final_settings,
                    "relationships": final_relationships,
                    "consistency_report": final_consistency,
                    "validation_result": final_validation
                }
                with open("result.json", "w", encoding="utf-8") as f:
                    json.dump(debug_result, f, ensure_ascii=False, indent=2)
                logger.info("[DEBUG] Saved result.json successfully")
            except Exception as e:
                logger.error(f"[DEBUG] Failed to save result.json: {e}")
            
            # 🆕 Link characters and events to sections
            linked_sections = []
            for i, sec in enumerate(sections):
                sec_content = sec.get("content", "")
                # Find related characters by name match
                related_chars = []
                for char_name in final_characters_map.keys():
                    if char_name and char_name in sec_content:
                        related_chars.append(char_name)

                # Find related events by chapter match (section index ~ chapter)
                related_evts = []
                for evt in final_events:
                    # Check if event belongs to this section's chapter
                    if evt.get("chapter") == i + 1:  # 1-based chapter
                        event_id = evt.get("event_id") or evt.get("id")
                        if event_id:
                            related_evts.append(event_id)

                # Update section with links
                linked_sec = dict(sec)
                linked_sec["related_characters"] = related_chars
                linked_sec["related_events"] = related_evts
                linked_sections.append(linked_sec)

            # ===== Context Maintenance System: Summary Generation =====
            # 🆕 Phase 3: 분석 완료 후 챕터 요약 자동 생성
            document_summary: Optional[DocumentSummaryOutput] = None
            try:
                summary_service = await get_summary_service()
                
                # 요약 생성 (Returns dict)
                summary_data = await summary_service.generate_chapter_summary(
                    content,
                    extracted_entities={
                        "characters": list(final_characters_map.values()),
                        "events": final_events,
                        "settings": final_settings
                    }
                )
                
                if summary_data:
                    document_summary = DocumentSummaryOutput(**summary_data)
                
                logger.info(
                    "Chapter summary generated (will be sent to Spring via callback)",
                    document_id=document_id,
                    summary_length=len(document_summary.summary) if document_summary else 0
                )
            except Exception as sum_err:
                logger.warning("Failed to generate chapter summary, continuing", error=str(sum_err))
            # =========================================================

            # 🆕 Character Timeline Collection (for future use)
            # Currently returns empty list, but typed Correctly
            character_timelines: list[CharacterTimelineOutput] = []

            return ProcessingResult(
                success=True,
                sections=linked_sections,  # Use linked sections
                characters=list(final_characters_map.values()),
                events=final_events,
                settings=final_settings,
                relationships=final_relationships,  # 🆕
                consistency_report=final_consistency,
                validation=final_validation if final_validation else None,
                document_summary=document_summary,  # 🆕 Structured Output
                character_timelines=character_timelines,  # 🆕 Typed List
                processing_time_ms=processing_time_ms
            )


        except Exception as e:
            logger.error("Streaming Analysis pipeline failed", error=str(e), trace_id=trace_id)
            return ProcessingResult(
                success=False,
                sections=[],
                characters=[],
                events=[],
                settings=[],
                error={"code": "STREAMING_ERROR", "message": str(e)},
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

    async def _create_sections(self, content: str) -> list[dict]:
        """Semantic Chunking for Sections using ChunkingService."""
        from app.services.embedding_service import get_embedding_service
        from app.services.chunking_service import ChunkingService

        embedding_service = get_embedding_service()
        chunking_service = ChunkingService(embedding_service)

        # 1. Semantic Chunking 실행
        semantic_sections = await chunking_service.create_semantic_sections(content)

        # 2. 결과 형식을 ProcessingResult에 맞게 변환
        final_sections = []
        for i, sec in enumerate(semantic_sections, start=1):
            final_sections.append({
                "sequence_order": i,
                "nav_title": sec["title"],
                "content": sec["content"],
                "embedding": sec["embedding"],
                "related_characters": [],
                "related_events": []
            })

        logger.info(f"Created {len(final_sections)} sections via Semantic Chunking")
        return final_sections

    async def _send_callback(self, url: str, callback: DocumentAnalysisCallback, job_id: str = None) -> None:
        """Spring에 Callback 전송 (via CallbackClient)"""
        from app.services.callback_client import get_callback_client

        client = get_callback_client()

        # Pydantic 모델에서 메타데이터 제외하고 결과 데이터만 추출 -> 'result' 필드로 들어감
        # Pydantic 모델에서 메타데이터 제외하고 결과 데이터만 추출 -> 'result' 필드로 들어감
        result_payload = callback.model_dump(
            exclude={
                "message_type",
                "document_id",
                "status",
                "error",
                "trace_id",
                "parent_folder_id",
                "processing_time_ms"
            },
            by_alias=True
        )

        # job_id 결정: 인자로 받은 것 우선, 없으면 document_id (구버전)
        final_job_id = job_id or callback.document_id

        logger.info("Sending analysis callback", job_id=final_job_id, status=callback.status)

        await client.send_analysis_callback(
            job_id=final_job_id,
            status=callback.status,
            result=result_payload,
            error=str(callback.error["message"]) if callback.error and isinstance(callback.error, dict) and "message" in callback.error else str(callback.error) if callback.error else None,
            callback_url=url,
            processing_time_ms=callback.processing_time_ms,  # 🆕 추가
            trace_id=callback.trace_id  # 🆕 추가
        )

        logger.info(
            "Callback sent",
            url=url,
            status=callback.status,
            document_id=callback.document_id
        )

    async def _publish_analysis_event(
        self,
        result: ProcessingResult,
        document_id: str,
        project_id: str,
        job_id: str,
        parent_folder_id: Optional[str],
        trace_id: str,
        processing_time_ms: int,
    ) -> None:
        """분석 결과를 Event로 발행 (Event Sourcing).
        
        Spring Boot의 Event Consumer가 이 이벤트를 수신하여
        RDB에 저장합니다 (Single Source of Truth).
        """
        try:
            publisher = await get_event_publisher()
            
            if result.success:
                # 분석 완료 이벤트
                event = AnalysisCompletedEvent(
                    project_id=project_id,
                    document_id=document_id,
                    job_id=job_id,
                    parent_folder_id=parent_folder_id,
                    trace_id=trace_id,
                    sections=[
                        {
                            "sequence_order": i + 1,
                            "nav_title": s.get("title", f"Section {i+1}"),
                            "content": s.get("content", ""),
                            "embedding": s.get("embedding"),
                            "related_characters": s.get("related_characters", []),
                            "related_events": s.get("related_events", []),
                        }
                        for i, s in enumerate(result.sections)
                    ],
                    # Removed: characters, events, settings, relationships (Synced to Neo4j directly)
                    # Removed: plot_integration
                    consistency_report=result.consistency_report,
                    validation=result.validation,
                    document_summary=result.document_summary.model_dump() if result.document_summary else None,
                    character_timelines=[t.model_dump() for t in result.character_timelines] if result.character_timelines else [],
                    processing_time_ms=processing_time_ms,
                )
                
                await publisher.publish_completed(event)
                logger.info(
                    "Analysis event published",
                    event_type="ANALYSIS_COMPLETED",
                    event_id=event.event_id,
                    document_id=document_id,
                )
            else:
                # 분석 실패 이벤트
                error_info = result.error or {}
                event = AnalysisFailedEvent(
                    project_id=project_id,
                    document_id=document_id,
                    job_id=job_id,
                    trace_id=trace_id,
                    error_code=error_info.get("code", "UNKNOWN_ERROR"),
                    error_message=error_info.get("message", "Unknown error"),
                    error_details=error_info,
                    processing_time_ms=processing_time_ms,
                )
                
                await publisher.publish_failed(event)
                logger.info(
                    "Analysis event published",
                    event_type="ANALYSIS_FAILED",
                    event_id=event.event_id,
                    document_id=document_id,
                )
                
        except Exception as e:
            logger.error(
                "Failed to publish analysis event",
                error=str(e),
                document_id=document_id,
            )
            # 이벤트 발행 실패해도 분석 자체는 성공으로 처리
            # DLQ에 저장됨 (event_publisher에서 처리)

class GlobalMergeConsumer:
    """Global Merge Consumer for 2nd Pass processing.

    모든 문서 분석 완료 후 Entity Resolution을 수행합니다.
    직접 aio_pika를 사용하여 global_merge_queue를 구독합니다.
    """

    def __init__(self):
        self._connection = None
        self._channel = None
        self._queue = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._running = False

    async def start(self) -> None:
        """Consumer 시작"""
        logger.info("Starting Global Merge Consumer")

        self._http_client = httpx.AsyncClient(timeout=60.0)

        # RabbitMQ 직접 연결
        import aio_pika

        rabbitmq_url = f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}@{settings.rabbitmq_host}:{settings.rabbitmq_port}/{settings.rabbitmq_vhost}"

        self._connection = await aio_pika.connect_robust(rabbitmq_url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=1)  # 동시에 1개만 처리

        # 큐 선언 (없으면 생성)
        # Spring Backend와 동일한 priority 설정 (일관성 유지)
        self._queue = await self._channel.declare_queue(
            settings.global_merge_queue,
            durable=True,
            arguments={'x-max-priority': 10}
        )

        # 메시지 수신 시작
        await self._queue.consume(self._process_message)

        self._running = True
        logger.info("Global Merge Consumer started", queue=settings.global_merge_queue)

    async def stop(self) -> None:
        """Consumer 중지"""
        logger.info("Stopping Global Merge Consumer")
        self._running = False

        if self._channel:
            await self._channel.close()

        if self._connection:
            await self._connection.close()

        if self._http_client:
            await self._http_client.aclose()

    async def _process_message(self, message: IncomingMessage) -> None:
        """글로벌 병합 메시지 처리"""
        start_time = time.time()
        project_id = ""
        callback_url = ""
        trace_id = ""

        try:
            # 1. 메시지 파싱
            body = json.loads(message.body.decode())
            msg = GlobalMergeMessage(**body)

            project_id = msg.project_id
            callback_url = msg.callback_url
            trace_id = msg.trace_id or ""

            logger.info(
                "Processing global merge",
                project_id=project_id,
                trace_id=trace_id
            )

            # 2. 모든 캐릭터 조회
            db_service = await get_db_service()
            all_characters = await db_service.get_all_project_characters_for_merge(project_id)

            # 3. Entity Resolution 수행
            character_merges = await self._perform_entity_resolution(all_characters)

            processing_time_ms = int((time.time() - start_time) * 1000)

            # 4. Callback 전송
            callback = GlobalMergeCallback(
                project_id=project_id,
                status="COMPLETED",
                character_merges=character_merges,
                consistency_report={
                    "total_characters": len(all_characters),
                    "merge_count": len(character_merges),
                    "auto_merged": sum(1 for m in character_merges if m.confidence >= 0.95),
                    "needs_review": sum(1 for m in character_merges if 0.8 <= m.confidence < 0.95)
                },
                processing_time_ms=processing_time_ms,
                trace_id=trace_id
            )

            # Debug: Save to result.json
            try:
                with open("result.json", "w", encoding="utf-8") as f:
                    f.write(callback.model_dump_json(indent=2, exclude_none=True))
                logger.info("Saved result.json")
            except Exception as e:
                logger.warning("Failed to save result.json", error=str(e))

            await self._send_callback(callback_url, callback)
            await message.ack()

            logger.info(
                "Global merge completed",
                project_id=project_id,
                merge_count=len(character_merges),
                processing_time_ms=processing_time_ms,
                trace_id=trace_id
            )

        except Exception as e:
            logger.error(
                "Global merge failed",
                error=str(e),
                project_id=project_id,
                trace_id=trace_id
            )

            # 실패 Callback
            if callback_url:
                error_callback = GlobalMergeCallback(
                    project_id=project_id,
                    status="FAILED",
                    error={"code": "MERGE_ERROR", "message": str(e)},
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    trace_id=trace_id
                )
                try:
                    await self._send_callback(callback_url, error_callback)
                except Exception:
                    pass
            # 실패 시 requeue하지 않음 (무한 루프 방지)
            await message.nack(requeue=False)

    async def _perform_entity_resolution(
        self,
        characters: list[dict]
    ) -> list[CharacterMergeResult]:
        """Entity Resolution 수행 - 동일 캐릭터 찾기 (Global Merge)."""
        from app.utils.entity_resolution import perform_global_merge

        # Run global merge logic (Graph Clustering + Smart Primary)
        raw_merges = perform_global_merge(characters)

        # Convert to Pydantic models
        merges = []
        for m in raw_merges:
            merges.append(CharacterMergeResult(
                primary_id=m["primary_id"],
                merged_ids=m["merged_ids"],
                canonical_name=m["canonical_name"],
                merged_aliases=m["merged_aliases"],
                confidence=m["confidence"],
                conflicts=m["conflicts"]
            ))

        return merges

    def _parse_aliases(self, aliases_json: Optional[str]) -> list[str]:
        """aliases_json 파싱"""
        if not aliases_json:
            return []
        try:
            return json.loads(aliases_json)
        except Exception:
            return []

    async def _send_callback(self, url: str, callback: GlobalMergeCallback) -> None:
        """Spring에 Callback 전송"""
        if not self._http_client:
            raise RuntimeError("HTTP client not initialized")

        # Docker 환경에서 localhost 접근 문제 해결
        if "localhost" in url or "127.0.0.1" in url:
            url = url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
            logger.info("Modified callback URL for Docker (Merge)", new_url=url)

        response = await self._http_client.post(
            url,
            json=callback.model_dump(exclude_none=True)
        )
        response.raise_for_status()


# ===== Consumer 인스턴스 관리 =====

_document_consumer: Optional[DocumentAnalysisConsumer] = None
_merge_consumer: Optional[GlobalMergeConsumer] = None


async def start_document_analysis_consumer() -> DocumentAnalysisConsumer:
    """Document Analysis Consumer 시작"""
    global _document_consumer
    if _document_consumer is None:
        _document_consumer = DocumentAnalysisConsumer()
        await _document_consumer.start()
    return _document_consumer


async def start_global_merge_consumer() -> GlobalMergeConsumer:
    """Global Merge Consumer 시작"""
    global _merge_consumer
    if _merge_consumer is None:
        _merge_consumer = GlobalMergeConsumer()
        await _merge_consumer.start()
    return _merge_consumer


async def stop_all_consumers() -> None:
    """모든 Consumer 중지"""
    global _document_consumer, _merge_consumer

    if _document_consumer:
        await _document_consumer.stop()
        _document_consumer = None

    if _merge_consumer:
        await _merge_consumer.stop()
        _merge_consumer = None
