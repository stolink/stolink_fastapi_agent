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
    
    # ===== Vector Search (RAG) =====
    
    async def get_embedding(self, text: str) -> list[float]:
        """Generate embedding using AWS Bedrock Titan Embeddings.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (1536 dimensions)
        """
        import boto3
        import json
        
        bedrock = boto3.client(
            'bedrock-runtime',
            region_name='us-east-1'
        )
        
        try:
            response = bedrock.invoke_model(
                modelId='amazon.titan-embed-text-v1',
                body=json.dumps({"inputText": text})
            )
            result = json.loads(response['body'].read())
            return result['embedding']
        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e))
            return []
    
    async def search_similar_characters(
        self,
        project_id: str,
        query_embedding: list[float],
        top_k: int = 10
    ) -> list[dict[str, Any]]:
        """Search for similar characters using Neo4j vector index.
        
        Args:
            project_id: Project UUID
            query_embedding: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of similar character dicts with similarity scores
        """
        if not self._neo4j_driver or not query_embedding:
            return []
        
        query = """
            MATCH (c:Character {project_id: $project_id})
            WHERE c.embedding IS NOT NULL
            WITH c, vector.similarity.cosine(c.embedding, $embedding) AS score
            WHERE score > 0.6
            RETURN c.name AS name, c.status AS status, c.role AS role,
                   c.traits AS traits, score
            ORDER BY score DESC
            LIMIT $top_k
        """
        
        try:
            async with self._neo4j_driver.session() as session:
                result = await session.run(
                    query,
                    project_id=project_id,
                    embedding=query_embedding,
                    top_k=top_k
                )
                records = await result.data()
                return records
        except Exception as e:
            logger.error("Failed vector search", error=str(e))
            return []
    
    async def search_similar_events(
        self,
        project_id: str,
        query_embedding: list[float],
        top_k: int = 10
    ) -> list[dict[str, Any]]:
        """Search for similar events using Neo4j vector index.
        
        Args:
            project_id: Project UUID
            query_embedding: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of similar event dicts with similarity scores
        """
        if not self._neo4j_driver or not query_embedding:
            return []
        
        query = """
            MATCH (e:Event {project_id: $project_id})
            WHERE e.embedding IS NOT NULL
            WITH e, vector.similarity.cosine(e.embedding, $embedding) AS score
            WHERE score > 0.6
            RETURN e.event_id AS event_id, e.description AS description,
                   e.participants AS participants, e.chapter AS chapter, score
            ORDER BY score DESC
            LIMIT $top_k
        """
        
        try:
            async with self._neo4j_driver.session() as session:
                result = await session.run(
                    query,
                    project_id=project_id,
                    embedding=query_embedding,
                    top_k=top_k
                )
                records = await result.data()
                return records
        except Exception as e:
            logger.error("Failed event vector search", error=str(e))
            return []
    
    async def retrieve_relevant_history(
        self,
        project_id: str,
        current_characters: list[dict],
        current_events: list[dict],
        top_k: int = 10
    ) -> dict[str, Any]:
        """Retrieve relevant historical data using RAG.
        
        Searches for similar characters and events from previous chapters
        to provide context for consistency checking.
        
        Args:
            project_id: Project UUID
            current_characters: Currently extracted characters
            current_events: Currently extracted events
            top_k: Number of results per category
            
        Returns:
            Dict with 'characters' and 'events' lists
        """
        result = {
            "characters": [],
            "events": [],
            "search_performed": False
        }
        
        if not self._neo4j_driver:
            return result
        
        try:
            # Build query text from current characters
            char_names = []
            for c in current_characters:
                name = c.get("name") or (c.get("profile", {}) or {}).get("name")
                if name:
                    char_names.append(name)
            
            if char_names:
                # Create query text and get embedding
                query_text = f"Characters: {', '.join(char_names)}"
                embedding = await self.get_embedding(query_text)
                
                if embedding:
                    # Search similar characters
                    similar_chars = await self.search_similar_characters(
                        project_id, embedding, top_k
                    )
                    result["characters"] = similar_chars
                    result["search_performed"] = True
            
            # Build query text from current events
            event_descriptions = []
            for e in current_events:
                desc = e.get("narrative_summary") or e.get("description")
                if desc:
                    event_descriptions.append(desc[:100])  # Truncate
            
            if event_descriptions:
                query_text = " ".join(event_descriptions[:5])
                embedding = await self.get_embedding(query_text)
                
                if embedding:
                    similar_events = await self.search_similar_events(
                        project_id, embedding, top_k
                    )
                    result["events"] = similar_events
                    result["search_performed"] = True
            
            logger.info(
                "RAG search completed",
                chars_found=len(result["characters"]),
                events_found=len(result["events"])
            )
            
        except Exception as e:
            logger.error("Failed to retrieve history", error=str(e))
        
        return result
    
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
    
    # ============================================================
    # 대용량 문서 분석 아키텍처 (Document Analysis Architecture)
    # ============================================================
    
    async def get_document_content(
        self,
        document_id: str
    ) -> Optional[dict[str, Any]]:
        """Get document content by ID (Claim Check Pattern).
        
        Spring에서 document_id만 전송하고, Python이 content를 직접 조회합니다.
        
        Args:
            document_id: Document UUID
            
        Returns:
            Document dict with content, or None if not found
        """
        if not self._pg_pool:
            logger.warning("PostgreSQL pool not initialized")
            return None
        
        query = """
            SELECT 
                d.id, d.title, d.content, d.type, d.order,
                d.parent_id, d.project_id, d.word_count
            FROM documents d
            WHERE d.id = $1 AND d.type = 'TEXT'
        """
        
        try:
            async with self._pg_pool.acquire() as conn:
                row = await conn.fetchrow(query, document_id)
                if row:
                    return dict(row)
                logger.warning("Document not found", document_id=document_id)
                return None
        except Exception as e:
            logger.error("Failed to query document content", error=str(e), document_id=document_id)
            return None
    
    async def get_document_with_parent_info(
        self,
        document_id: str
    ) -> Optional[dict[str, Any]]:
        """Get document with parent folder information.
        
        Args:
            document_id: Document UUID
            
        Returns:
            Document dict with parent info
        """
        if not self._pg_pool:
            return None
        
        query = """
            SELECT 
                d.id, d.title, d.content, d.type, d.order,
                d.parent_id, d.project_id,
                parent.title AS parent_title,
                parent.order AS parent_order
            FROM documents d
            LEFT JOIN documents parent ON d.parent_id = parent.id
            WHERE d.id = $1
        """
        
        try:
            async with self._pg_pool.acquire() as conn:
                row = await conn.fetchrow(query, document_id)
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error("Failed to query document with parent", error=str(e))
            return None
    
    async def get_all_project_characters_for_merge(
        self,
        project_id: str
    ) -> list[dict[str, Any]]:
        """Get all characters for a project for Entity Resolution.
        
        2차 Pass(GlobalMerger)에서 사용합니다.
        
        Args:
            project_id: Project UUID
            
        Returns:
            List of character dicts with aliases
        """
        if not self._pg_pool:
            return []
        
        query = """
            SELECT 
                c.id, c.name, c.role, c.aliases_json,
                c.description, c.created_at
            FROM characters c
            WHERE c.project_id = $1
            ORDER BY c.created_at
        """
        
        try:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch(query, project_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Failed to query project characters for merge", error=str(e))
            return []
    
    async def get_project_analysis_status(
        self,
        project_id: str
    ) -> dict[str, Any]:
        """Get analysis status summary for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Dict with counts by status
        """
        if not self._pg_pool:
            return {"total": 0, "completed": 0, "failed": 0, "pending": 0}
        
        query = """
            SELECT 
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE analysis_status = 'COMPLETED') AS completed,
                COUNT(*) FILTER (WHERE analysis_status = 'FAILED') AS failed,
                COUNT(*) FILTER (WHERE analysis_status IN ('PENDING', 'QUEUED', 'PROCESSING')) AS pending
            FROM documents
            WHERE project_id = $1 AND type = 'TEXT'
        """
        
        try:
            async with self._pg_pool.acquire() as conn:
                row = await conn.fetchrow(query, project_id)
                if row:
                    return dict(row)
                return {"total": 0, "completed": 0, "failed": 0, "pending": 0}
        except Exception as e:
            logger.error("Failed to query analysis status", error=str(e))
            return {"total": 0, "completed": 0, "failed": 0, "pending": 0}
    
    # ===== Vector Similarity Search =====
    
    async def search_similar_sections(
        self,
        embedding: list[float],
        project_id: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.7
    ) -> list[dict[str, Any]]:
        """Search for similar sections using pgvector cosine similarity.
        
        Args:
            embedding: Query embedding vector (1024 dimensions)
            project_id: Optional project filter
            limit: Maximum number of results
            threshold: Minimum similarity threshold (0-1)
            
        Returns:
            List of similar sections with similarity scores
        """
        if not self._pg_pool:
            logger.warning("PostgreSQL pool not initialized")
            return []
        
        # Convert embedding list to pgvector format
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
        
        # Query with optional project filter
        if project_id:
            query = """
                SELECT 
                    s.id, s.nav_title, s.content, s.sequence_order,
                    s.document_id, d.title as document_title,
                    1 - (s.embedding <=> $1::vector) as similarity
                FROM sections s
                JOIN documents d ON s.document_id = d.id
                WHERE d.project_id = $2
                    AND s.embedding IS NOT NULL
                    AND 1 - (s.embedding <=> $1::vector) >= $3
                ORDER BY s.embedding <=> $1::vector
                LIMIT $4
            """
            params = [embedding_str, project_id, threshold, limit]
        else:
            query = """
                SELECT 
                    s.id, s.nav_title, s.content, s.sequence_order,
                    s.document_id,
                    1 - (s.embedding <=> $1::vector) as similarity
                FROM sections s
                WHERE s.embedding IS NOT NULL
                    AND 1 - (s.embedding <=> $1::vector) >= $2
                ORDER BY s.embedding <=> $1::vector
                LIMIT $3
            """
            params = [embedding_str, threshold, limit]
        
        try:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Failed to search similar sections", error=str(e))
            return []
    
    async def get_context_sections_for_document(
        self,
        document_id: str,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get related context sections for consistency checking.
        
        Returns sections from the same project that might be relevant for
        checking narrative consistency.
        
        Args:
            document_id: Current document being analyzed
            limit: Maximum sections to return
            
        Returns:
            List of context sections with embeddings
        """
        if not self._pg_pool:
            return []
        
        query = """
            SELECT 
                s.id, s.nav_title, s.content, s.sequence_order,
                s.document_id, d.title as document_title,
                s.related_characters_json, s.related_events_json
            FROM sections s
            JOIN documents d ON s.document_id = d.id
            WHERE d.project_id = (
                SELECT project_id FROM documents WHERE id = $1
            )
            AND s.document_id != $1
            ORDER BY s.created_at DESC
            LIMIT $2
        """
        
        try:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch(query, document_id, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Failed to get context sections", error=str(e))
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
