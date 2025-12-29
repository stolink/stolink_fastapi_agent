"""Database query service for FastAPI.

Provides read-only access to PostgreSQL and Neo4j for agent pipeline.
Used when agents need detailed data beyond what Spring Boot provided.

Design Principle:
- READ ONLY: FastAPI only reads, writes go through Spring Boot callback
- On-demand: Only query when agents actually need the data
- Cached: Use connection pooling for efficiency
"""
import asyncio
from typing import Any, Optional
import structlog
import asyncpg
from neo4j import AsyncGraphDatabase

from app.config import settings

logger = structlog.get_logger()


class DatabaseQueryService:
    """Read-only database query service for agent pipeline."""
    
    def __init__(self):
        self._pg_pool: Optional[asyncpg.Pool] = None
        self._neo4j_driver = None
    
    # ===== Connection Management =====
    
    async def connect(self) -> None:
        """Initialize database connections."""
        # PostgreSQL connection pool
        self._pg_pool = await asyncpg.create_pool(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            min_size=2,
            max_size=10,
        )
        logger.info("PostgreSQL connection pool created")
        
        # Neo4j async driver
        self._neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        logger.info("Neo4j driver initialized")
    
    async def disconnect(self) -> None:
        """Close database connections."""
        if self._pg_pool:
            await self._pg_pool.close()
            logger.info("PostgreSQL connection pool closed")
        
        if self._neo4j_driver:
            await self._neo4j_driver.close()
            logger.info("Neo4j driver closed")
    
    # ===== Character Queries =====
    
    async def get_character_details(
        self, 
        project_id: str, 
        character_name: str
    ) -> Optional[dict[str, Any]]:
        """Get full character details by name.
        
        Args:
            project_id: Project UUID
            character_name: Character name to look up
            
        Returns:
            Character details dict or None if not found
        """
        if not self._pg_pool:
            logger.warning("PostgreSQL pool not initialized")
            return None
        
        query = """
            SELECT 
                c.id, c.name, c.role, c.description, c.traits,
                c.visual_traits, c.personality_traits, c.status,
                c.inventory, c.stats,
                c.first_appearance, c.created_at
            FROM characters c
            WHERE c.project_id = $1 AND c.name = $2
        """
        
        try:
            async with self._pg_pool.acquire() as conn:
                row = await conn.fetchrow(query, project_id, character_name)
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error("Failed to query character", error=str(e), name=character_name)
            return None
    
    async def get_all_characters(
        self, 
        project_id: str
    ) -> list[dict[str, Any]]:
        """Get all characters for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            List of character dicts
        """
        if not self._pg_pool:
            return []
        
        query = """
            SELECT 
                c.id, c.name, c.role, c.description, c.traits,
                c.visual_traits, c.personality_traits, c.status,
                c.inventory, c.stats
            FROM characters c
            WHERE c.project_id = $1
            ORDER BY c.created_at
        """
        
        try:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch(query, project_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Failed to query characters", error=str(e))
            return []
    
    # ===== Event Queries =====
    
    async def get_recent_events(
        self, 
        project_id: str, 
        limit: int = 20
    ) -> list[dict[str, Any]]:
        """Get recent events for a project.
        
        Args:
            project_id: Project UUID
            limit: Maximum number of events to return
            
        Returns:
            List of event dicts
        """
        if not self._pg_pool:
            return []
        
        query = """
            SELECT 
                e.id, e.event_type, e.description, e.participants,
                e.location_ref, e.chapter, e.sequence_order, e.importance
            FROM events e
            WHERE e.project_id = $1
            ORDER BY e.chapter DESC, e.sequence_order DESC
            LIMIT $2
        """
        
        try:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch(query, project_id, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Failed to query events", error=str(e))
            return []
    
    # ===== Setting/Location Queries =====
    
    async def get_all_settings(
        self, 
        project_id: str
    ) -> list[dict[str, Any]]:
        """Get all settings/locations for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            List of setting dicts
        """
        if not self._pg_pool:
            return []
        
        query = """
            SELECT 
                s.id, s.name, s.location_type, s.description,
                s.visual_background, s.atmosphere, s.parent_location
            FROM settings s
            WHERE s.project_id = $1
        """
        
        try:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch(query, project_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Failed to query settings", error=str(e))
            return []
    
    # ===== Neo4j Relationship Queries =====
    
    async def get_character_relationships(
        self, 
        project_id: str, 
        character_name: str
    ) -> list[dict[str, Any]]:
        """Get all relationships for a character from Neo4j.
        
        Args:
            project_id: Project UUID
            character_name: Character name
            
        Returns:
            List of relationship dicts
        """
        if not self._neo4j_driver:
            logger.warning("Neo4j driver not initialized")
            return []
        
        query = """
            MATCH (c:Character {name: $name, project_id: $project_id})-[r]-(other:Character)
            RETURN 
                c.name AS source,
                type(r) AS relation_type,
                other.name AS target,
                r.strength AS strength,
                r.description AS description
        """
        
        try:
            async with self._neo4j_driver.session() as session:
                result = await session.run(
                    query, 
                    name=character_name, 
                    project_id=project_id
                )
                records = await result.data()
                return records
        except Exception as e:
            logger.error("Failed to query Neo4j relationships", error=str(e))
            return []
    
    async def get_all_relationships(
        self, 
        project_id: str
    ) -> list[dict[str, Any]]:
        """Get all character relationships for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            List of relationship dicts
        """
        if not self._neo4j_driver:
            return []
        
        query = """
            MATCH (source:Character {project_id: $project_id})-[r]->(target:Character)
            RETURN 
                source.name AS source_name,
                type(r) AS relation_type,
                target.name AS target_name,
                r.strength AS strength,
                r.description AS description
        """
        
        try:
            async with self._neo4j_driver.session() as session:
                result = await session.run(query, project_id=project_id)
                records = await result.data()
                return records
        except Exception as e:
            logger.error("Failed to query all relationships", error=str(e))
            return []
    
    # ===== World Rules Query =====
    
    async def get_world_rules(
        self, 
        project_id: str
    ) -> list[dict[str, Any]]:
        """Get established world rules for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            List of world rule dicts
        """
        if not self._pg_pool:
            return []
        
        query = """
            SELECT 
                w.id, w.category, w.name, w.description, 
                w.importance, w.exceptions
            FROM world_rules w
            WHERE w.project_id = $1
            ORDER BY w.importance DESC
        """
        
        try:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch(query, project_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Failed to query world rules", error=str(e))
            return []


# ===== Singleton Instance =====

_db_service: Optional[DatabaseQueryService] = None


async def get_db_service() -> DatabaseQueryService:
    """Get or create database query service singleton."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseQueryService()
        await _db_service.connect()
    return _db_service


async def close_db_service() -> None:
    """Close database service connections."""
    global _db_service
    if _db_service:
        await _db_service.disconnect()
        _db_service = None
