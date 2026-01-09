"""Hierarchical Context Manager for Novel Analysis.

다단계 요약 시스템을 통한 계층적 맥락 관리.
Phase 4 of Context Maintenance System.
"""
import structlog
from typing import Any, Optional

logger = structlog.get_logger()


class HierarchicalContextManager:
    """계층적 맥락 관리자.
    
    전체/권/챕터 레벨의 요약을 조합하여
    LLM에 제공할 컨텍스트를 구축합니다.
    """
    
    LEVELS = {
        1: "NOVEL",    # 전체 소설 요약
        2: "VOLUME",   # 권/파트 요약
        3: "CHAPTER"   # 챕터 요약
    }
    
    def __init__(self, summary_service, context_builder=None):
        """Initialize with services.
        
        Args:
            summary_service: ChapterSummaryService instance
            context_builder: Optional EntityCentricContextBuilder
        """
        self._summary_service = summary_service
        self._context_builder = context_builder
    
    async def build_hierarchical_context(
        self,
        project_id: str,
        current_document_id: str = None,
        mentioned_characters: list[str] = None,
        max_recent_chapters: int = 5
    ) -> dict[str, Any]:
        """분석 시 사용할 계층적 컨텍스트 구축.
        
        Args:
            project_id: Project UUID
            current_document_id: 현재 분석 중인 문서 ID
            mentioned_characters: 현재 텍스트에서 언급된 캐릭터 이름들
            max_recent_chapters: 포함할 최근 챕터 요약 수
            
        Returns:
            Dict with hierarchical context
        """
        context = {
            "novel_summary": None,
            "volume_summary": None,
            "recent_chapters": [],
            "entity_context": None,
            "context_text": ""
        }
        
        try:
            # Level 1: 전체 소설 요약
            novel_summaries = await self._summary_service.get_summaries_for_project(
                project_id, level=1
            )
            if novel_summaries:
                context["novel_summary"] = novel_summaries[0].get("summary")
            
            # Level 2: 현재 권/파트 요약 (document_id 기반)
            if current_document_id:
                volume_summaries = await self._summary_service.get_summaries_for_project(
                    project_id, level=2
                )
                # TODO: 현재 문서의 상위 폴더 찾아서 해당 권 요약 조회
                if volume_summaries:
                    context["volume_summary"] = volume_summaries[0].get("summary")
            
            # Level 3: 최근 챕터 요약들
            recent_chapters = await self._summary_service.get_recent_chapter_summaries(
                project_id, current_document_id, max_recent_chapters
            )
            context["recent_chapters"] = recent_chapters
            
            # 엔티티 중심 컨텍스트 (Phase 2 통합)
            if mentioned_characters and self._context_builder:
                entity_ctx = await self._context_builder.build_context(
                    project_id, mentioned_characters
                )
                context["entity_context"] = entity_ctx
            
            # 통합 컨텍스트 텍스트 생성
            context["context_text"] = self._format_context(context)
            
            logger.info(
                "Hierarchical context built",
                has_novel_summary=bool(context["novel_summary"]),
                has_volume_summary=bool(context["volume_summary"]),
                recent_chapters_count=len(context["recent_chapters"]),
                has_entity_context=bool(context["entity_context"])
            )
            
        except Exception as e:
            logger.error("Failed to build hierarchical context", error=str(e))
        
        return context
    
    def _format_context(self, context: dict) -> str:
        """컨텍스트를 LLM 프롬프트용 텍스트로 포맷팅.
        
        Args:
            context: build_hierarchical_context에서 반환된 컨텍스트
            
        Returns:
            포맷된 문자열
        """
        parts = []
        
        # 전체 소설 요약
        if context.get("novel_summary"):
            parts.append(f"## 전체 줄거리\n{context['novel_summary']}")
        
        # 현재 권 요약
        if context.get("volume_summary"):
            parts.append(f"## 현재 권 요약\n{context['volume_summary']}")
        
        # 최근 챕터 요약들
        if context.get("recent_chapters"):
            parts.append("## 최근 챕터")
            for i, summary in enumerate(context["recent_chapters"], 1):
                parts.append(f"{i}. {summary}")
        
        # ===== 캐릭터 중심 섹션 (Phase 6-2) =====
        if context.get("entity_context"):
            entity_ctx = context["entity_context"]
            mentioned_chars = entity_ctx.get("mentioned_characters", [])
            char_histories = entity_ctx.get("character_histories", [])
            
            if char_histories:
                parts.append("\n## === 등장 캐릭터 상세 정보 ===")
                
                for char_hist in char_histories:
                    char_name = char_hist.get("name", "Unknown")
                    char_section = [f"\n### 📌 {char_name}에 대해 알아야 할 것"]
                    
                    # 1. 현재 상태 (타임라인 최신)
                    recent_events = char_hist.get("recent_events", [])
                    if recent_events:
                        latest_chapter = max((e.get("chapter", 0) for e in recent_events), default=0)
                        char_section.append(f"\n**📍 현재 상태 (Chapter {latest_chapter})**")
                        char_section.append(f"- 역할: {char_hist.get('role', 'Unknown')}")
                        char_section.append(f"- 상태: {char_hist.get('status', 'Unknown')}")
                    
                    # 2. 배경 스토리
                    backstory = char_hist.get("backstory", "")
                    if backstory:
                        char_section.append(f"\n**📖 배경**")
                        char_section.append(f"{backstory[:200]}...")
                    
                    # 3. 최근 활동
                    if recent_events:
                        char_section.append(f"\n**📅 최근 활동**")
                        for evt in recent_events[:3]:  # 최대 3개
                            summary = evt.get("summary", evt.get("description", ""))
                            evt_type = evt.get("event_type", "")
                            if summary:
                                char_section.append(f"- Ch.{evt.get('chapter', '?')}: {summary[:80]}...")
                    
                    # 4. 주요 관계 (해당 캐릭터 관련만)
                    relationships = entity_ctx.get("relationships", [])
                    char_rels = [
                        r for r in relationships 
                        if r.get("source") == char_name or r.get("target") == char_name
                    ]
                    if char_rels:
                        char_section.append(f"\n**👥 주요 관계**")
                        for rel in char_rels[:3]:  # 최대 3개
                            if rel.get("source") == char_name:
                                other = rel.get("target")
                                rel_type = rel.get("rel_type", "RELATED_TO")
                            else:
                                other = rel.get("source")
                                rel_type = "←" + rel.get("rel_type", "RELATED_TO")
                            
                            strength = rel.get("strength", 5)
                            char_section.append(f"- {other}: {rel_type} (강도: {strength}/10)")
                    
                    # 5. 성격/일관성 힌트
                    aliases = char_hist.get("aliases", [])
                    if aliases:
                        char_section.append(f"\n**ℹ️ 별칭**: {', '.join(aliases)}")
                    
                    parts.append("\n".join(char_section))
            
            # 장소 컨텍스트 (간략하게)
            setting_contexts = entity_ctx.get("setting_contexts", [])
            if setting_contexts:
                parts.append("\n## 장소 정보")
                for setting in setting_contexts[:2]:  # 최대 2개
                    parts.append(f"- **{setting.get('name')}**: {setting.get('description', '')[:100]}")
        
        return "\n\n".join(parts)
    
    async def get_context_for_analysis(
        self,
        project_id: str,
        current_text: str,
        current_document_id: str = None
    ) -> str:
        """분석용 통합 컨텍스트 조회 (편의 메서드).
        
        Args:
            project_id: Project UUID
            current_text: 현재 분석 중인 텍스트
            current_document_id: 현재 문서 ID
            
        Returns:
            LLM 프롬프트에 삽입할 컨텍스트 문자열
        """
        # 현재 텍스트에서 캐릭터 이름 추출 (간단한 휴리스틱)
        # 실제 구현에서는 NER 또는 DB 매칭 사용 권장
        mentioned_chars = await self._extract_mentioned_characters(
            project_id, current_text
        )
        
        context = await self.build_hierarchical_context(
            project_id=project_id,
            current_document_id=current_document_id,
            mentioned_characters=mentioned_chars
        )
        
        return context.get("context_text", "")
    
    async def _extract_mentioned_characters(
        self,
        project_id: str,
        text: str
    ) -> list[str]:
        """텍스트에서 알려진 캐릭터 이름 추출.
        
        Args:
            project_id: Project UUID
            text: 분석할 텍스트
            
        Returns:
            발견된 캐릭터 이름 리스트
        """
        mentioned = []
        
        try:
            # Neo4j에서 프로젝트의 모든 캐릭터 이름 조회
            if self._summary_service._db_service._neo4j_driver:
                async with self._summary_service._db_service._neo4j_driver.session() as session:
                    result = await session.run(
                        """
                        MATCH (c:Character {project_id: $pid})
                        RETURN c.name as name, COALESCE(c.aliases, []) as aliases
                        """,
                        pid=project_id
                    )
                    
                    async for record in result:
                        name = record.get("name")
                        aliases = record.get("aliases", []) or []
                        
                        # 본명 체크
                        if name and name in text:
                            mentioned.append(name)
                        else:
                            # 별칭 체크
                            for alias in aliases:
                                if alias and alias in text:
                                    mentioned.append(name)
                                    break
                                    
        except Exception as e:
            logger.error("Failed to extract mentioned characters", error=str(e))
        
        return mentioned


# Singleton
_hierarchical_manager: Optional[HierarchicalContextManager] = None


async def get_hierarchical_context_manager(
    summary_service=None,
    context_builder=None
) -> HierarchicalContextManager:
    """Get or create hierarchical context manager singleton."""
    global _hierarchical_manager
    
    if _hierarchical_manager is None or summary_service is not None:
        if summary_service is None:
            from app.services.summary_service import get_summary_service
            summary_service = await get_summary_service()
        
        if context_builder is None:
            from app.services.context_builder import get_context_builder
            context_builder = await get_context_builder()
        
        _hierarchical_manager = HierarchicalContextManager(
            summary_service, context_builder
        )
    
    return _hierarchical_manager
