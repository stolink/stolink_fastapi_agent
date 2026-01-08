"""Entity-Centric Context Builder for Novel Analysis.

현재 분석 중인 텍스트에서 언급된 엔티티(캐릭터, 장소)를 기반으로
관련 히스토리를 조회하여 컨텍스트를 구축합니다.

Phase 2 of Context Maintenance System.
"""
import structlog
from typing import Any, Optional

logger = structlog.get_logger()


class EntityCentricContextBuilder:
    """엔티티 중심 컨텍스트 빌더.
    
    현재 텍스트에 등장하는 캐릭터/장소를 기반으로
    Neo4j에서 관련 히스토리를 조회합니다.
    """
    
    def __init__(self, db_service):
        """Initialize with database service.
        
        Args:
            db_service: DatabaseQueryService instance
        """
        self._db_service = db_service
    
    async def build_context(
        self,
        project_id: str,
        mentioned_characters: list[str],
        mentioned_settings: list[str] = None,
        max_events_per_char: int = 5,
        max_relationships: int = 10
    ) -> dict[str, Any]:
        """엔티티 중심 컨텍스트 구축.
        
        Args:
            project_id: Project UUID
            mentioned_characters: 현재 텍스트에서 언급된 캐릭터 이름들
            mentioned_settings: 현재 텍스트에서 언급된 장소 이름들
            max_events_per_char: 캐릭터당 최대 이벤트 수
            max_relationships: 최대 관계 수
            
        Returns:
            Dict with character histories, relationships, settings
        """
        context = {
            "character_histories": [],
            "relationships": [],
            "setting_contexts": [],
            "mentioned_characters": mentioned_characters,
            "mentioned_settings": mentioned_settings or []
        }
        
        if not self._db_service._neo4j_driver:
            logger.warning("Neo4j not available for entity context")
            return context
        
        try:
            # 1. 각 캐릭터의 히스토리 조회
            for char_name in mentioned_characters:
                char_history = await self._get_character_history(
                    project_id, char_name, max_events_per_char
                )
                if char_history:
                    context["character_histories"].append(char_history)
            
            # 2. 캐릭터 간 관계 조회
            if len(mentioned_characters) >= 1:
                relationships = await self._get_character_relationships(
                    project_id, mentioned_characters, max_relationships
                )
                context["relationships"] = relationships
            
            # 3. 장소 컨텍스트 조회
            for setting_name in (mentioned_settings or []):
                setting_context = await self._get_setting_context(
                    project_id, setting_name
                )
                if setting_context:
                    context["setting_contexts"].append(setting_context)
            
            logger.info(
                "Entity-centric context built",
                chars=len(context["character_histories"]),
                relationships=len(context["relationships"]),
                settings=len(context["setting_contexts"])
            )
            
        except Exception as e:
            logger.error("Failed to build entity context", error=str(e))
        
        return context
    
    async def _get_character_history(
        self,
        project_id: str,
        char_name: str,
        max_events: int = 5
    ) -> Optional[dict]:
        """캐릭터의 히스토리 조회.
        
        Args:
            project_id: Project UUID
            char_name: 캐릭터 이름
            max_events: 최대 이벤트 수
            
        Returns:
            캐릭터 정보 및 최근 이벤트
        """
        try:
            async with self._db_service._neo4j_driver.session() as session:
                # 캐릭터 기본 정보 조회
                result = await session.run(
                    """
                    MATCH (c:Character {project_id: $pid, name: $name})
                    RETURN c.role as role, c.status as status, 
                           c.backstory as backstory, c.aliases as aliases
                    """,
                    pid=project_id,
                    name=char_name
                )
                char_record = await result.single()
                
                if not char_record:
                    return None
                
                # 캐릭터의 최근 이벤트 조회
                result = await session.run(
                    """
                    MATCH (c:Character {project_id: $pid, name: $name})-[:PARTICIPATES_IN]->(e:Event)
                    RETURN e.eventId as event_id, e.narrativeSummary as summary,
                           e.description as description, e.chapter as chapter,
                           e.eventType as event_type
                    ORDER BY e.chapter DESC, e.sequenceOrder DESC
                    LIMIT $limit
                    """,
                    pid=project_id,
                    name=char_name,
                    limit=max_events
                )
                events = [dict(record) async for record in result]
                
                return {
                    "name": char_name,
                    "role": char_record.get("role"),
                    "status": char_record.get("status"),
                    "backstory": char_record.get("backstory"),
                    "aliases": char_record.get("aliases", []),
                    "recent_events": events
                }
                
        except Exception as e:
            logger.error("Failed to get character history", char=char_name, error=str(e))
            return None
    
    async def _get_character_relationships(
        self,
        project_id: str,
        char_names: list[str],
        max_relationships: int = 10
    ) -> list[dict]:
        """캐릭터들 간의 관계 조회.
        
        Args:
            project_id: Project UUID
            char_names: 캐릭터 이름 리스트
            max_relationships: 최대 관계 수
            
        Returns:
            관계 리스트
        """
        try:
            async with self._db_service._neo4j_driver.session() as session:
                # 언급된 캐릭터들과 연결된 모든 관계 조회
                result = await session.run(
                    """
                    MATCH (a:Character {project_id: $pid})-[r]->(b:Character {project_id: $pid})
                    WHERE a.name IN $names OR b.name IN $names
                    AND type(r) <> 'PARTICIPATES_IN'
                    RETURN a.name as source, b.name as target, 
                           type(r) as rel_type, r.description as description,
                           r.strength as strength
                    LIMIT $limit
                    """,
                    pid=project_id,
                    names=char_names,
                    limit=max_relationships
                )
                relationships = [dict(record) async for record in result]
                
                return relationships
                
        except Exception as e:
            logger.error("Failed to get relationships", error=str(e))
            return []
    
    async def _get_setting_context(
        self,
        project_id: str,
        setting_name: str
    ) -> Optional[dict]:
        """장소의 컨텍스트 조회.
        
        Args:
            project_id: Project UUID
            setting_name: 장소 이름
            
        Returns:
            장소 정보 및 관련 이벤트
        """
        try:
            async with self._db_service._neo4j_driver.session() as session:
                # 장소 기본 정보 조회
                result = await session.run(
                    """
                    MATCH (s:Setting {project_id: $pid, name: $name})
                    RETURN s.locationType as location_type, 
                           s.description as description,
                           s.atmosphere as atmosphere,
                           s.significance as significance
                    """,
                    pid=project_id,
                    name=setting_name
                )
                setting_record = await result.single()
                
                if not setting_record:
                    return None
                
                # 해당 장소에서 발생한 최근 이벤트 조회
                result = await session.run(
                    """
                    MATCH (e:Event)-[:HAPPENED_AT]->(s:Setting {project_id: $pid, name: $name})
                    RETURN e.narrativeSummary as summary, e.eventType as event_type
                    ORDER BY e.chapter DESC
                    LIMIT 3
                    """,
                    pid=project_id,
                    name=setting_name
                )
                related_events = [dict(record) async for record in result]
                
                return {
                    "name": setting_name,
                    "location_type": setting_record.get("location_type"),
                    "description": setting_record.get("description"),
                    "atmosphere": setting_record.get("atmosphere"),
                    "significance": setting_record.get("significance"),
                    "related_events": related_events
                }
                
        except Exception as e:
            logger.error("Failed to get setting context", setting=setting_name, error=str(e))
            return None
    
    def format_context_for_llm(self, context: dict) -> str:
        """LLM 프롬프트용 컨텍스트 포맷팅.
        
        Args:
            context: build_context에서 반환된 컨텍스트
            
        Returns:
            포맷된 문자열
        """
        parts = []
        
        # 캐릭터 히스토리
        if context.get("character_histories"):
            parts.append("## 등장 캐릭터 히스토리")
            for char in context["character_histories"]:
                char_info = f"### {char['name']} ({char.get('role', 'Unknown')})"
                if char.get("backstory"):
                    char_info += f"\n배경: {char['backstory'][:200]}"
                if char.get("recent_events"):
                    events_summary = "; ".join([
                        e.get("summary", e.get("description", ""))[:50] 
                        for e in char["recent_events"][:3]
                    ])
                    char_info += f"\n최근 활동: {events_summary}"
                parts.append(char_info)
        
        # 관계
        if context.get("relationships"):
            parts.append("\n## 캐릭터 관계")
            for rel in context["relationships"]:
                rel_str = f"- {rel['source']} → {rel['target']}: {rel['rel_type']}"
                if rel.get("description"):
                    rel_str += f" ({rel['description'][:50]})"
                parts.append(rel_str)
        
        # 장소
        if context.get("setting_contexts"):
            parts.append("\n## 장소 컨텍스트")
            for setting in context["setting_contexts"]:
                setting_info = f"### {setting['name']} ({setting.get('location_type', 'Unknown')})"
                if setting.get("description"):
                    setting_info += f"\n{setting['description'][:150]}"
                parts.append(setting_info)
        
        return "\n".join(parts)


# Singleton instance
_context_builder: Optional[EntityCentricContextBuilder] = None


async def get_context_builder(db_service=None) -> EntityCentricContextBuilder:
    """Get or create context builder singleton."""
    global _context_builder
    
    if _context_builder is None or db_service is not None:
        if db_service is None:
            from app.services.db_query_service import get_db_service
            db_service = await get_db_service()
        _context_builder = EntityCentricContextBuilder(db_service)
    
    return _context_builder
