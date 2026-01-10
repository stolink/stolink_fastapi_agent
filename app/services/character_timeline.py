"""Character Timeline Tracking System.

캐릭터의 상태 변화를 시간순으로 추적합니다.
Phase 6-1 of Context Maintenance System.
"""
import structlog
from datetime import datetime
from typing import Any, Optional

logger = structlog.get_logger()


class CharacterTimeline:
    """캐릭터 타임라인 추적기.
    
    챕터별 캐릭터 상태를 기록하고 변화 과정을 추적합니다.
    """
    
    def __init__(self, db_service):
        """Initialize with database service.
        
        Args:
            db_service: DatabaseQueryService instance
        """
        self._db_service = db_service
    
    async def track_character_state(
        self,
        project_id: str,
        character_name: str,
        chapter: int,
        document_id: str = None,
        state_snapshot: dict = None
    ) -> Optional[str]:
        """캐릭터 상태 스냅샷 저장 (DEPRECATED - No longer saves to PostgreSQL).
        
        ⚠️ MIGRATION NOTE:
        This method no longer saves character timelines to AI Backend PostgreSQL.
        Timeline data should be sent to Spring Backend via callback payload instead.
        
        This method is kept for backward compatibility but only returns
        a generated UUID without performing any database operations.
        
        Args:
            project_id: Project UUID
            character_name: 캐릭터 이름
            chapter: 챕터 번호
            document_id: 문서 ID
            state_snapshot: 상태 정보
                {
                    "health": "healthy/injured/critical",
                    "mood": "happy/sad/angry/neutral",
                    "location": "장소명",
                    "state_changes": {"health": "healthy->injured"}
                }
        
        Returns:
            Generated UUID (no DB write performed)
        """
        import uuid
        
        logger.info(
            "track_character_state called (DEPRECATED - no DB write)",
            character=character_name,
            chapter=chapter,
            project_id=project_id
        )
        
        # Return a UUID for compatibility, but don't save to DB
        return str(uuid.uuid4())
    
    async def get_character_arc(
        self,
        project_id: str,
        character_name: str,
        limit: int = 20
    ) -> list[dict]:
        """캐릭터 아크 (변화 과정) 조회.
        
        Args:
            project_id: Project UUID
            character_name: 캐릭터 이름
            limit: 최대 개수
        
        Returns:
            시간순 상태 변화 리스트
        """
        if not self._db_service._pg_pool:
            return []
        
        query = """
            SELECT chapter, health_status, emotional_state, 
                   current_location, state_changes, created_at
            FROM character_timeline
            WHERE project_id = $1 AND character_name = $2
            ORDER BY chapter ASC
            LIMIT $3
        """
        
        try:
            async with self._db_service._pg_pool.acquire() as conn:
                rows = await conn.fetch(query, project_id, character_name, limit)
                return [
                    {
                        "chapter": row["chapter"],
                        "health": row["health_status"],
                        "mood": row["emotional_state"],
                        "location": row["current_location"],
                        "changes": row["state_changes"],
                        "timestamp": row["created_at"]
                    }
                    for row in rows
                ]
        except Exception as e:
            if "character_timeline" not in str(e):
                logger.error("Failed to get character arc", error=str(e))
            return []
    
    async def detect_state_change(
        self,
        project_id: str,
        character_name: str,
        current_chapter: int,
        current_state: dict
    ) -> dict:
        """상태 변화 감지.
        
        Args:
            project_id: Project UUID
            character_name: 캐릭터 이름
            current_chapter: 현재 챕터
            current_state: 현재 상태
        
        Returns:
            변화 정보 dict
        """
        arc = await self.get_character_arc(project_id, character_name)
        
        if not arc:
            return {"has_change": False}
        
        # 가장 최근 상태
        last_state = arc[-1]
        
        changes = {}
        
        # Health 변화
        if current_state.get("health") != last_state.get("health"):
            changes["health"] = f"{last_state.get('health', 'unknown')}->{current_state.get('health', 'unknown')}"
        
        # Mood 변화
        if current_state.get("mood") != last_state.get("mood"):
            changes["mood"] = f"{last_state.get('mood', 'neutral')}->{current_state.get('mood', 'neutral')}"
        
        # Location 변화
        if current_state.get("location") != last_state.get("location"):
            changes["location"] = f"{last_state.get('location', '')}->{current_state.get('location', '')}"
        
        return {
            "has_change": bool(changes),
            "changes": changes,
            "previous_state": last_state,
            "current_state": current_state
        }


# SQL for table creation
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS character_timeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    character_name VARCHAR(255) NOT NULL,
    chapter INT NOT NULL,
    document_id UUID,
    
    -- 상태 추적
    health_status VARCHAR(50),
    emotional_state VARCHAR(50),
    current_location VARCHAR(255),
    
    -- 변화 기록
    state_changes JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(project_id, character_name, chapter)
);

CREATE INDEX IF NOT EXISTS idx_timeline_character 
ON character_timeline(project_id, character_name);

CREATE INDEX IF NOT EXISTS idx_timeline_chapter 
ON character_timeline(project_id, chapter);
"""


# Singleton
_character_timeline: Optional[CharacterTimeline] = None


async def get_character_timeline(db_service=None) -> CharacterTimeline:
    """Get or create character timeline singleton."""
    global _character_timeline
    
    if _character_timeline is None or db_service is not None:
        if db_service is None:
            from app.services.db_query_service import get_db_service
            db_service = await get_db_service()
        _character_timeline = CharacterTimeline(db_service)
    
    return _character_timeline
