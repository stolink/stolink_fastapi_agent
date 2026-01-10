"""Chapter Summary Service for Novel Analysis.

챕터별 요약 자동 생성 및 저장.
Phase 3 of Context Maintenance System.
"""
import structlog
from datetime import datetime
from typing import Any, Optional

logger = structlog.get_logger()


class SummaryLevel:
    """요약 레벨 상수."""
    NOVEL = 1      # 전체 소설
    VOLUME = 2     # 권/파트
    CHAPTER = 3    # 챕터


class ChapterSummaryService:
    """챕터별 요약 생성 및 저장 서비스."""
    
    def __init__(self, db_service, llm_service=None):
        """Initialize with database service.
        
        Args:
            db_service: DatabaseQueryService instance
            llm_service: Optional LLM service for summary generation
        """
        self._db_service = db_service
        self._llm_service = llm_service
    
    async def generate_chapter_summary(
        self,
        chapter_content: str,
        extracted_entities: dict,
        max_sentences: int = 5
    ) -> dict:
        """챕터 분석 완료 후 요약 생성.
        
        Args:
            chapter_content: 챕터 원문 (또는 일부)
            extracted_entities: 추출된 엔티티 (characters, events, settings)
            max_sentences: 최대 문장 수
            
        Returns:
            dict: {
                "summary": str,
                "key_characters": list[str],
                "key_events": list[str],
                "level": int
            }
        """
        # 캐릭터 이름 추출
        char_names = []
        for c in extracted_entities.get("characters", []):
            name = c.get("name") or (c.get("profile", {}) or {}).get("name")
            if name:
                char_names.append(name)
        
        # 이벤트 요약 추출
        event_summaries = []
        for e in extracted_entities.get("events", []):
            summary = e.get("narrative_summary") or e.get("description", "")
            if summary:
                event_summaries.append(summary[:100])
        
        # 장소 이름 추출 (사용하지 않더라도 추출 로직 유지)
        setting_names = []
        for s in extracted_entities.get("settings", []):
            name = s.get("name")
            if name:
                setting_names.append(name)
        
        summary_text = ""
        # LLM 사용 시
        if self._llm_service:
            summary_text = await self._generate_with_llm(
                chapter_content, char_names, event_summaries, setting_names, max_sentences
            )
        else:
            # 폴백: 간단한 템플릿 기반 요약
            summary_text = self._generate_fallback_summary(
                char_names, event_summaries, setting_names
            )
            
        return {
            "summary": summary_text,
            "key_characters": char_names[:10],  # 상위 10개로 제한
            "key_events": event_summaries[:5],  # 상위 5개로 제한
            "level": SummaryLevel.CHAPTER
        }
    
    async def _generate_with_llm(
        self,
        content: str,
        characters: list[str],
        events: list[str],
        settings: list[str],
        max_sentences: int
    ) -> str:
        """LLM을 사용한 요약 생성."""
        prompt = f"""다음 챕터의 핵심 내용을 {max_sentences}문장 이내로 요약하세요.

등장인물: {', '.join(characters[:10])}
주요 이벤트: {'; '.join(events[:5])}
장소: {', '.join(settings[:5])}

내용 (일부):
{content[:2000]}

요약:"""
        
        try:
            response = await self._llm_service.generate(prompt)
            return response.strip()
        except Exception as e:
            logger.error("LLM summary generation failed", error=str(e))
            return self._generate_fallback_summary(characters, events, settings)
    
    def _generate_fallback_summary(
        self,
        characters: list[str],
        events: list[str],
        settings: list[str]
    ) -> str:
        """템플릿 기반 폴백 요약 생성."""
        parts = []
        
        if characters:
            parts.append(f"등장인물: {', '.join(characters[:5])}")
        
        if events:
            parts.append(f"주요 사건: {events[0][:100]}")
        
        if settings:
            parts.append(f"배경: {', '.join(settings[:3])}")
        
        return ". ".join(parts) if parts else "요약 없음"
    
    async def save_summary(
        self,
        document_id: str,
        project_id: str,
        summary: str,
        level: int = SummaryLevel.CHAPTER,
        key_characters: list[str] = None,
        key_events: list[str] = None
    ) -> Optional[str]:
        """요약 저장 (DEPRECATED - No longer saves to PostgreSQL).
        
        ⚠️ MIGRATION NOTE:
        This method no longer saves summaries to AI Backend PostgreSQL.
        Summaries are now sent to Spring Backend via callback payload.
        
        This method is kept for backward compatibility but only returns
        a generated UUID without performing any database operations.
        
        Args:
            document_id: Document UUID
            project_id: Project UUID
            summary: 요약 텍스트
            level: 요약 레벨 (1=전체, 2=파트, 3=챕터)
            key_characters: 핵심 캐릭터 이름들
            key_events: 핵심 이벤트 ID들
            
        Returns:
            Generated UUID (no DB write performed)
        """
        import uuid
        
        logger.info(
            "save_summary called (DEPRECATED - no DB write)",
            document_id=document_id,
            level=level,
            summary_length=len(summary)
        )
        
        # Return a UUID for compatibility, but don't save to DB
        return str(uuid.uuid4())
    
    async def get_summaries_for_project(
        self,
        project_id: str,
        level: int = None
    ) -> list[dict[str, Any]]:
        """프로젝트의 요약 목록 조회.
        
        Args:
            project_id: Project UUID
            level: 특정 레벨만 조회 (None이면 전체)
            
        Returns:
            요약 리스트
        """
        if not self._db_service._pg_pool:
            return []
        
        if level:
            query = """
                SELECT id, document_id, level, summary, key_characters, key_events, created_at
                FROM document_summaries
                WHERE project_id = $1 AND level = $2
                ORDER BY created_at DESC
            """
            params = [project_id, level]
        else:
            query = """
                SELECT id, document_id, level, summary, key_characters, key_events, created_at
                FROM document_summaries
                WHERE project_id = $1
                ORDER BY level, created_at DESC
            """
            params = [project_id]
        
        try:
            async with self._db_service._pg_pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
        except Exception as e:
            if "document_summaries" not in str(e):
                logger.error("Failed to get summaries", error=str(e))
            return []
    
    async def get_recent_chapter_summaries(
        self,
        project_id: str,
        current_document_id: str = None,
        limit: int = 5
    ) -> list[str]:
        """최근 챕터 요약들 조회.
        
        Args:
            project_id: Project UUID
            current_document_id: 현재 문서 ID (제외용)
            limit: 최대 개수
            
        Returns:
            요약 문자열 리스트
        """
        if not self._db_service._pg_pool:
            return []
        
        query = """
            SELECT summary
            FROM document_summaries
            WHERE project_id = $1 
                AND level = $2
                AND ($3::uuid IS NULL OR document_id != $3)
            ORDER BY created_at DESC
            LIMIT $4
        """
        
        try:
            async with self._db_service._pg_pool.acquire() as conn:
                rows = await conn.fetch(
                    query, 
                    project_id, 
                    SummaryLevel.CHAPTER,
                    current_document_id,
                    limit
                )
                return [row["summary"] for row in rows]

        except Exception as e:
            if "document_summaries" not in str(e):
                logger.error("Failed to get recent summaries", error=str(e))
            return []

    async def update_global_summary(self, project_id: str) -> str:
        """모든 챕터 요약을 취합하여 전체 줄거리(Level 1) 갱신.
        
        Args:
            project_id: Project UUID
            
        Returns:
            생성된 전체 줄거리
        """
        if not self._llm_service:
            logger.warning("LLM service not available for global summary")
            return ""

        # 1. 모든 챕터 요약 가져오기 (오래된 순으로 정렬)
        summaries = await self.get_summaries_for_project(project_id, level=SummaryLevel.CHAPTER)
        # get_summaries_for_project returns DESC -> reverse to ASC (Chapter 1 -> N)
        summaries.reverse()
        
        if not summaries:
            logger.info("No chapter summaries found for global update", project_id=project_id)
            return ""

        # 2. 텍스트 프롬프트 구성
        # 토큰 제한 고려: 너무 길면 챕터 번호와 핵심만 요약
        combined_text_parts = []
        for s in summaries:
            # TODO: 실제 구현 시에는 document_id로 챕터 번호를 조회하거나, 순서 정보를 활용해야 함
            # 여기서는 단순히 시간순으로 나열
            combined_text_parts.append(f"- {s.get('summary', '')}")
            
        combined_text = "\n".join(combined_text_parts)
        
        # 3. LLM 요청
        prompt = f"""다음은 소설의 각 챕터별 요약 모음입니다. 이를 바탕으로 소설 전체를 관통하는 '종합 줄거리'를 작성하세요.
서론, 본론, 결론이 포함된 하나의 자연스러운 글로 요약해야 합니다. 분량은 A4 1장 이내(약 2000자)로 제한합니다.

[챕터별 요약]
{combined_text}

전체 종합 줄거리:"""

        try:
            global_summary = await self._llm_service.generate(prompt)
            global_summary = global_summary.strip()
            
            # 4. 저장 (Level 1)
            # document_id는 Project ID를 사용하여 '전체'임을 표시 (또는 별도 컨벤션)
            await self.save_summary(
                document_id=project_id,
                project_id=project_id,
                summary=global_summary,
                level=SummaryLevel.NOVEL
            )
            
            return global_summary
            
        except Exception as e:
            logger.error("Failed to generate global summary", error=str(e))
            return ""

    async def update_volume_summary(
        self, 
        project_id: str, 
        volume_document_id: str,
        chapter_document_ids: list[str]
    ) -> str:
        """특정 권(Volume)에 속한 챕터들을 요약하여 권 줄거리(Level 2) 갱신."""
        
        if not self._llm_service or not chapter_document_ids:
            return ""
            
        # 1. 대상 챕터들의 요약 조회
        # (개별 조회라 쿼리가 많을 수 있음 -> 최적화 필요하지만 일단 구현)
        chapter_summaries = []
        for doc_id in chapter_document_ids:
            # 임시: get_summaries_for_project 대신 특정 doc의 summary 조회 로직 필요
            # 현재 API로는 전체 가져와서 필터링해야 함. 비효율적이나 일단 전체 로드
            pass 
        
        # 효율을 위해 쿼리 직접 실행 권장
        if not self._db_service._pg_pool:
            return ""
            
        query = """
            SELECT summary FROM document_summaries 
            WHERE document_id = ANY($1::uuid[]) AND level = $2
            ORDER BY created_at ASC
        """
        
        try:
            async with self._db_service._pg_pool.acquire() as conn:
                rows = await conn.fetch(query, chapter_document_ids, SummaryLevel.CHAPTER)
                summaries = [row["summary"] for row in rows]
                
            if not summaries:
                return ""
                
            combined_text = "\n".join([f"- {s}" for s in summaries])
            
            prompt = f"""다음은 한 권(Volume)에 포함된 챕터들의 요약입니다. 이를 바탕으로 '해당 권의 줄거리'를 요약하세요.
            
[챕터 요약]
{combined_text}

권 줄거리:"""

            volume_summary = await self._llm_service.generate(prompt)
            volume_summary = volume_summary.strip()
            
            # 저장 (Level 2)
            await self.save_summary(
                document_id=volume_document_id, # 권의 폴더 ID 등
                project_id=project_id,
                summary=volume_summary,
                level=SummaryLevel.VOLUME
            )
            
            return volume_summary
            
        except Exception as e:
            logger.error("Failed to update volume summary", error=str(e))
            return ""


# SQL for table creation (run manually or via migration)
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS document_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    project_id UUID NOT NULL,
    level INT NOT NULL DEFAULT 3,
    summary TEXT NOT NULL,
    key_characters TEXT[] DEFAULT '{}',
    key_events TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(document_id, level)
);

CREATE INDEX IF NOT EXISTS idx_summaries_project_level 
ON document_summaries(project_id, level);
"""


# Singleton
_summary_service: Optional[ChapterSummaryService] = None


async def get_summary_service(db_service=None) -> ChapterSummaryService:
    """Get or create summary service singleton."""
    global _summary_service
    
    if _summary_service is None or db_service is not None:
        if db_service is None:
            from app.services.db_query_service import get_db_service
            db_service = await get_db_service()
        _summary_service = ChapterSummaryService(db_service)
    
    return _summary_service
