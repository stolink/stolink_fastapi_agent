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
)
from app.services.db_query_service import get_db_service
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
    error: Optional[dict] = None
    processing_time_ms: int = 0


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
        
        # RabbitMQ 직접 연결
        import aio_pika
        
        rabbitmq_url = f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}@{settings.rabbitmq_host}:{settings.rabbitmq_port}/{settings.rabbitmq_vhost}"
        
        self._connection = await aio_pika.connect_robust(rabbitmq_url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=settings.consumer_prefetch_count)
        
        # 큐 선언 (없으면 생성)
        self._queue = await self._channel.declare_queue(
            settings.document_analysis_queue,
            durable=True
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
            msg = DocumentAnalysisMessage(**body)
            
            trace_id = msg.trace_id or ""
            document_id = msg.document_id
            callback_url = msg.callback_url
            
            logger.info(
                "Processing document analysis message",
                document_id=document_id,
                project_id=msg.project_id,
                trace_id=trace_id
            )
            
            # 2. PROCESSING 상태 업데이트
            await self._update_status(document_id, "PROCESSING", trace_id)
            
            # 3. DB에서 content 조회 (Claim Check Pattern)
            db_service = await get_db_service()
            document = await db_service.get_document_content(document_id)
            
            if not document or not document.get("content"):
                raise ValueError(f"Document content not found: {document_id}")
            
            content = document["content"]
            
            # 4. 분석 수행
            result = await self._run_analysis(
                content=content,
                document_id=document_id,
                project_id=msg.project_id,
                context=msg.context,
                trace_id=trace_id
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # 5. Callback 전송
            callback = DocumentAnalysisCallback(
                document_id=document_id,
                parent_folder_id=msg.parent_folder_id,
                status="COMPLETED" if result.success else "FAILED",
                error=result.error,
                sections=[SectionOutput(**s) for s in result.sections],
                characters=result.characters,
                events=result.events,
                settings=result.settings,
                processing_time_ms=processing_time_ms,
                trace_id=trace_id
            )
            
            await self._send_callback(callback_url, callback)
            
            # 6. 메시지 ACK
            await message.ack()
            
            logger.info(
                "Document analysis completed",
                document_id=document_id,
                success=result.success,
                processing_time_ms=processing_time_ms,
                trace_id=trace_id
            )
            
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
                    await self._send_callback(callback_url, error_callback)
                except Exception as cb_error:
                    logger.error("Failed to send error callback", error=str(cb_error))
            
            # 메시지 NACK (재시도 가능)
            await message.nack(requeue=True)
    
    async def _update_status(self, document_id: str, status: str, trace_id: str) -> None:
        """Spring API로 상태 업데이트"""
        if not self._http_client:
            return
        
        url = f"{settings.spring_backend_url}/api/documents/{document_id}/analysis-status"
        
        try:
            response = await self._http_client.patch(
                url,
                json={"status": status, "traceId": trace_id}
            )
            response.raise_for_status()
            logger.debug("Status updated", document_id=document_id, status=status)
        except Exception as e:
            logger.warning("Failed to update status", error=str(e), document_id=document_id)
    
    async def _run_analysis(
        self,
        content: str,
        document_id: str,
        project_id: str,
        context: Optional[dict],
        trace_id: str
    ) -> ProcessingResult:
        """LangGraph 파이프라인으로 분석 수행.
        
        1. Section 생성 (Semantic Chunking + 임베딩)
        2. LangGraph 파이프라인 실행 (캐릭터, 이벤트, 배경 추출)
        3. 결과 취합
        """
        from app.agents.graph import run_analysis_pipeline
        
        start_time = time.time()
        
        try:
            # 1. Section 생성 (임베딩 포함)
            sections = await self._create_sections(content)
            
            # 2. context에서 기존 데이터 추출
            existing_characters = []
            existing_events = []
            existing_relationships = []
            existing_settings = []
            
            if context:
                # context가 AnalysisContext 객체인 경우
                if hasattr(context, 'existing_characters'):
                    existing_characters = [
                        {"id": c.id, "name": c.name, "role": c.role}
                        for c in (context.existing_characters or [])
                    ]
                    existing_events = [
                        {"id": e.id, "event_type": e.event_type, "summary": e.summary}
                        for e in (context.existing_events or [])
                    ]
                    existing_relationships = [
                        {"source_name": r.source_name, "target_name": r.target_name, "relation_type": r.relation_type}
                        for r in (context.existing_relationships or [])
                    ]
                    existing_settings = [
                        {"id": s.id, "name": s.name, "location_type": s.location_type}
                        for s in (context.existing_settings or [])
                    ]
                # context가 dict인 경우
                elif isinstance(context, dict):
                    existing_characters = context.get("existing_characters", [])
                    existing_events = context.get("existing_events", [])
                    existing_relationships = context.get("existing_relationships", [])
                    existing_settings = context.get("existing_settings", [])
            
            # 3. LangGraph 파이프라인 실행
            logger.info(
                "Starting LangGraph pipeline",
                document_id=document_id,
                content_length=len(content),
                trace_id=trace_id
            )
            
            pipeline_result = await run_analysis_pipeline(
                content=content,
                project_id=project_id,
                document_id=document_id,
                job_id=f"doc-{document_id}",  # job_id 생성
                callback_url="",  # Consumer가 직접 callback 처리
                existing_characters=existing_characters,
                existing_events=existing_events,
                existing_relationships=existing_relationships,
                existing_settings=existing_settings,
                trace_id=trace_id
            )
            
            # 4. 결과 추출
            characters = pipeline_result.get("extracted_characters", [])
            events = pipeline_result.get("extracted_events", [])
            settings_list = pipeline_result.get("extracted_settings", [])
            
            # 캐릭터를 dict로 변환 (Pydantic 모델인 경우)
            if characters and hasattr(characters[0], 'model_dump'):
                characters = [c.model_dump() for c in characters]
            
            if events and hasattr(events[0], 'model_dump'):
                events = [e.model_dump() for e in events]
                
            if settings_list and hasattr(settings_list[0], 'model_dump'):
                settings_list = [s.model_dump() for s in settings_list]
            
            # 5. 에러 체크
            errors = pipeline_result.get("errors", [])
            if errors:
                logger.warning("Pipeline completed with errors", errors=errors, trace_id=trace_id)
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "LangGraph pipeline completed",
                document_id=document_id,
                characters_count=len(characters),
                events_count=len(events),
                settings_count=len(settings_list),
                sections_count=len(sections),
                processing_time_ms=processing_time_ms,
                trace_id=trace_id
            )
            
            return ProcessingResult(
                success=True,
                sections=sections,
                characters=characters,
                events=events,
                settings=settings_list,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            logger.error("Analysis pipeline failed", error=str(e), trace_id=trace_id)
            return ProcessingResult(
                success=False,
                sections=[],
                characters=[],
                events=[],
                settings=[],
                error={"code": "PIPELINE_ERROR", "message": str(e)},
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
    
    async def _send_callback(self, url: str, callback: DocumentAnalysisCallback) -> None:
        """Spring에 Callback 전송"""
        if not self._http_client:
            raise RuntimeError("HTTP client not initialized")
        
        response = await self._http_client.post(
            url,
            json=callback.model_dump(exclude_none=True)
        )
        response.raise_for_status()
        
        logger.info(
            "Callback sent",
            url=url,
            status=callback.status,
            document_id=callback.document_id
        )


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
        self._queue = await self._channel.declare_queue(
            settings.global_merge_queue,
            durable=True
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
            
            await message.nack(requeue=True)
    
    async def _perform_entity_resolution(
        self,
        characters: list[dict]
    ) -> list[CharacterMergeResult]:
        """Entity Resolution 수행 - 동일 캐릭터 찾기"""
        merges = []
        processed_ids = set()
        
        for i, char1 in enumerate(characters):
            if char1["id"] in processed_ids:
                continue
            
            char1_aliases = self._parse_aliases(char1.get("aliases_json"))
            merge_candidates = []
            
            for char2 in characters[i + 1:]:
                if char2["id"] in processed_ids:
                    continue
                
                char2_aliases = self._parse_aliases(char2.get("aliases_json"))
                
                result = is_same_character(
                    char1["name"],
                    char2["name"],
                    char1_aliases,
                    char2_aliases
                )
                
                if result.classification in (MatchClassification.AUTO_MERGE, MatchClassification.NEEDS_REVIEW):
                    merge_candidates.append({
                        "character": char2,
                        "score": result.score,
                        "aliases": char2_aliases
                    })
                    processed_ids.add(char2["id"])
            
            if merge_candidates:
                # 병합 결과 생성
                all_aliases = merge_character_aliases(
                    char1_aliases,
                    [alias for c in merge_candidates for alias in c["aliases"]]
                )
                
                avg_score = sum(c["score"] for c in merge_candidates) / len(merge_candidates)
                
                merges.append(CharacterMergeResult(
                    primary_id=char1["id"],
                    merged_ids=[c["character"]["id"] for c in merge_candidates],
                    canonical_name=char1["name"],
                    merged_aliases=all_aliases,
                    confidence=avg_score / 100.0  # 0-1 범위로 변환
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
