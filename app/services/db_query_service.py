"""Database query service for FastAPI.

Provides read-only access to PostgreSQL and Neo4j for agent pipeline.
Used when agents need detailed data beyond what Spring Boot provided.

Design Principle:
- READ ONLY: FastAPI only reads, writes go through Spring Boot callback
- On-demand: Only query when agents actually need the data
- Cached: Use connection pooling for efficiency
- Auto-recovery: Reconnect on connection failures
"""
import asyncio
from typing import Any, Optional
import structlog
import asyncpg
import uuid
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired

from app.config import settings

logger = structlog.get_logger()


class DatabaseQueryService:
    """Read-only database query service for agent pipeline."""

    def __init__(self):
        self._pg_pool: Optional[asyncpg.Pool] = None
        self._neo4j_driver = None
        self._connection_lock = asyncio.Lock()

    # ===== Connection Management =====

    async def connect(self) -> None:
        """Initialize database connections."""
        await self._connect_postgres()
        await self._connect_neo4j()

    async def _connect_postgres(self) -> None:
        """Initialize PostgreSQL connection pool and ensure schema exists."""
        try:
            self._pg_pool = await asyncpg.create_pool(
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )

            logger.info("PostgreSQL connection pool created")

            # Ensure schema and extensions exist
            async with self._pg_pool.acquire() as conn:
                # 1. Enable pgvector
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

                # 2. Create tables
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS sections (
                        id UUID PRIMARY KEY,
                        document_id UUID,
                        content TEXT,
                        embedding vector(3072),
                        sequence_order INTEGER,
                        nav_title TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                    CREATE TABLE IF NOT EXISTS settings (
                        id UUID PRIMARY KEY,
                        project_id UUID,
                        name TEXT,
                        location_type TEXT,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                    CREATE TABLE IF NOT EXISTS events (
                        id UUID PRIMARY KEY,
                        project_id UUID,
                        document_id UUID,
                        event_type TEXT,
                        description TEXT,
                        chapter INTEGER,
                        sequence_order INTEGER,
                        participants JSONB,
                        location TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                    CREATE TABLE IF NOT EXISTS characters (
                        id UUID PRIMARY KEY,
                        project_id UUID,
                        name TEXT,
                        role TEXT,
                        description TEXT,
                        aliases_json JSONB,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                """)

                # 3. Create indices for performance
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS sections_document_id_idx ON sections(document_id);
                    CREATE INDEX IF NOT EXISTS settings_project_id_idx ON settings(project_id);
                    CREATE INDEX IF NOT EXISTS events_project_id_idx ON events(project_id);
                    CREATE INDEX IF NOT EXISTS characters_project_id_idx ON characters(project_id);
                    
                    /* Create UNIQUE indexes for upsert support */
                    CREATE UNIQUE INDEX IF NOT EXISTS characters_project_id_name_idx ON characters(project_id, name);
                    CREATE UNIQUE INDEX IF NOT EXISTS settings_project_id_name_idx ON settings(project_id, name);
                """)

                logger.info("PostgreSQL schema initialized (sections, settings, events, characters tables)")

        except Exception as e:
            logger.error("Failed to initialize PostgreSQL", error=str(e))
            self._pg_pool = None

    async def _connect_neo4j(self) -> None:
        """Initialize Neo4j driver."""
        try:
            self._neo4j_driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                max_connection_lifetime=300,
                connection_timeout=30,
            )
            
            # Initialize Schema (Constraints & Indexes)
            async with self._neo4j_driver.session() as session:
                # 1. Character
                await session.run("CREATE CONSTRAINT character_id_unique IF NOT EXISTS FOR (c:Character) REQUIRE c.id IS UNIQUE")
                await session.run("CREATE INDEX character_project_id_idx IF NOT EXISTS FOR (c:Character) ON (c.project_id)")
                await session.run("CREATE INDEX character_name_idx IF NOT EXISTS FOR (c:Character) ON (c.name)")
                
                # 2. Event
                await session.run("CREATE CONSTRAINT event_id_unique IF NOT EXISTS FOR (e:Event) REQUIRE e.eventId IS UNIQUE")
                await session.run("CREATE INDEX event_project_id_idx IF NOT EXISTS FOR (e:Event) ON (e.project_id)")
                
                # 3. Setting
                await session.run("CREATE CONSTRAINT setting_id_unique IF NOT EXISTS FOR (s:Setting) REQUIRE s.settingId IS UNIQUE")
                await session.run("CREATE INDEX setting_project_id_idx IF NOT EXISTS FOR (s:Setting) ON (s.project_id)")
                await session.run("CREATE INDEX setting_name_idx IF NOT EXISTS FOR (s:Setting) ON (s.name)")
            
            logger.info("Neo4j driver initialized and schema constraints applied")
        except Exception as e:
            logger.error("Failed to initialize Neo4j driver", error=str(e))
            self._neo4j_driver = None

    async def ensure_postgres_connected(self) -> bool:
        """Ensure PostgreSQL pool is connected, reconnect if needed."""
        if self._pg_pool is None:
            async with self._connection_lock:
                if self._pg_pool is None:
                    logger.warning("PostgreSQL pool not initialized, attempting reconnect")
                    await self._connect_postgres()
        return self._pg_pool is not None

    async def ensure_neo4j_connected(self) -> bool:
        """Ensure Neo4j driver is connected, reconnect if needed."""
        if self._neo4j_driver is None:
            async with self._connection_lock:
                if self._neo4j_driver is None:
                    logger.warning("Neo4j driver not initialized, attempting reconnect")
                    await self._connect_neo4j()
        return self._neo4j_driver is not None

    async def reconnect_neo4j(self) -> None:
        """Force reconnect Neo4j driver (for connection recovery)."""
        async with self._connection_lock:
            if self._neo4j_driver:
                try:
                    await self._neo4j_driver.close()
                except Exception:
                    pass
            await self._connect_neo4j()
            logger.info("Neo4j driver reconnected")

    async def disconnect(self) -> None:
        """Close database connections."""
        if self._pg_pool:
            await self._pg_pool.close()
            self._pg_pool = None
            logger.info("PostgreSQL connection pool closed")

        if self._neo4j_driver:
            await self._neo4j_driver.close()
            self._neo4j_driver = None
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
                c.id, c.name, c.role, c.description, c.aliases_json
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
                e.location_ref, e.chapter, e.sequence_order
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
            logger.warning("Failed to query settings (table might not exist)", error=str(e))
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
            MATCH (source:Character {projectId: $project_id})-[r]->(target:Character)
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
        """Generate embedding using Gemini Text Embeddings.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (768 dimensions)
        """
        from app.services.embedding_service import generate_embedding_async

        try:
            return await generate_embedding_async(text)
        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e))
            return []

    # ===== Adaptive RAG (Phase 1) =====

    async def get_project_stats(self, project_id: str) -> dict[str, int]:
        """프로젝트의 엔티티 통계 조회.
        
        적응형 top_k 계산에 사용됩니다.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Dict with character_count, event_count, setting_count
        """
        stats = {
            "character_count": 0,
            "event_count": 0,
            "setting_count": 0
        }
        
        if not self._neo4j_driver:
            return stats
        
        try:
            async with self._neo4j_driver.session() as session:
                # 캐릭터 수
                result = await session.run(
                    "MATCH (c:Character {projectId: $pid}) RETURN count(c) as cnt",
                    pid=project_id
                )
                record = await result.single()
                stats["character_count"] = record["cnt"] if record else 0
                
                # 이벤트 수
                result = await session.run(
                    "MATCH (e:Event {projectId: $pid}) RETURN count(e) as cnt",
                    pid=project_id
                )
                record = await result.single()
                stats["event_count"] = record["cnt"] if record else 0
                
                # 장소 수
                result = await session.run(
                    "MATCH (s:Setting {projectId: $pid}) RETURN count(s) as cnt",
                    pid=project_id
                )
                record = await result.single()
                stats["setting_count"] = record["cnt"] if record else 0
                
        except Exception as e:
            logger.error("Failed to get project stats", error=str(e))
        
        return stats

    async def get_adaptive_top_k(self, project_id: str) -> int:
        """프로젝트 분량에 따른 적응형 top_k 계산.
        
        분량이 많은 프로젝트일수록 더 많은 컨텍스트를 검색합니다.
        
        Args:
            project_id: Project UUID
            
        Returns:
            적응형 top_k 값 (10-40 범위)
        """
        stats = await self.get_project_stats(project_id)
        
        base_k = 10
        char_count = stats.get("character_count", 0)
        event_count = stats.get("event_count", 0)
        
        # 캐릭터 50명 이상 → top_k 증가
        if char_count > 50:
            base_k = min(25, base_k + char_count // 10)
        elif char_count > 20:
            base_k = min(15, base_k + char_count // 20)
        
        # 이벤트 100개 이상 → top_k 추가 증가
        if event_count > 100:
            base_k = min(40, base_k + event_count // 20)
        elif event_count > 50:
            base_k = min(25, base_k + event_count // 25)
        
        logger.info(
            "Adaptive top_k calculated",
            project_id=project_id,
            char_count=char_count,
            event_count=event_count,
            top_k=base_k
        )
        
        return base_k

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
                   c.profileJson AS profile, score
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
            MATCH (e:Event {projectId: $project_id})
            WHERE e.embedding IS NOT NULL
            WITH e, vector.similarity.cosine(e.embedding, $embedding) AS score
            WHERE score > 0.6
            RETURN e.eventId AS event_id, e.description AS description,
                   e.participantsJson AS participants, e.chapter AS chapter, score
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
        top_k: int = None  # None이면 적응형 top_k 사용
    ) -> dict[str, Any]:
        """Retrieve relevant historical data using RAG.

        Searches for similar characters and events from previous chapters
        to provide context for consistency checking.

        Args:
            project_id: Project UUID
            current_characters: Currently extracted characters
            current_events: Currently extracted events
            top_k: Number of results per category (None = adaptive)

        Returns:
            Dict with 'characters' and 'events' lists
        """
        result = {
            "characters": [],
            "events": [],
            "search_performed": False,
            "top_k_used": 0
        }

        if not self._neo4j_driver:
            return result

        try:
            # 적응형 top_k 사용 (None이면 자동 계산)
            if top_k is None:
                top_k = await self.get_adaptive_top_k(project_id)
            result["top_k_used"] = top_k

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
                events_found=len(result["events"]),
                top_k=top_k
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

    async def save_sections(self, document_id: str, sections: list[dict]) -> int:
        """Save semantic sections and their embeddings to PostgreSQL.

        Args:
            document_id: The source document UUID
            sections: List of section dicts (content, embedding, title)

        Returns:
            Number of sections saved
        """
        if not self._pg_pool:
            logger.warning("PostgreSQL pool not initialized, skipping section save")
            return 0

        if not sections:
            return 0

        # First, delete existing sections for this document to avoid duplication
        delete_query = "DELETE FROM sections WHERE document_id = $1"

        # Insert query
        insert_query = """
            INSERT INTO sections
            (id, document_id, content, embedding, sequence_order, nav_title, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
        """

        import uuid

        saved_count = 0
        try:
            async with self._pg_pool.acquire() as conn:
                async with conn.transaction():
                    # 1. Clean up old sections
                    await conn.execute(delete_query, document_id)

                    # 2. Batch insert new sections
                    # Prepare list of params for executemany
                    params = []
                    for i, sec in enumerate(sections):
                        sec_id = str(uuid.uuid4())
                        embedding_vector = str(sec["embedding"]) if sec.get("embedding") else None

                        params.append((
                            sec_id,
                            document_id,
                            sec["content"],
                            embedding_vector, # pgvector expects string representation like "[0.1, 0.2, ...]"
                            i,
                            sec.get("title", f"Section {i+1}")
                        ))

                    if params:
                        await conn.executemany(insert_query, params)
                        saved_count = len(params)
                        logger.info(f"Saved {saved_count} semantic sections for doc {document_id}")

        except Exception as e:
            logger.error("Failed to save sections", error=str(e), document_id=document_id)
            return 0

        return saved_count

        return saved_count

    async def search_similar_sections(
        self,
        embedding: list[float],
        project_id: Optional[str] = None,
        limit: int = 5,
        threshold: float = 0.7
    ) -> list[dict[str, Any]]:
        """Search for similar sections using vector similarity.

        Args:
            embedding: Query embedding vector
            project_id: Optional project filter
            limit: Max results
            threshold: Minimum similarity threshold (0-1)

        Returns:
            List of section dicts with similarity score
        """
        if not self._pg_pool:
            return []

        # pgvector cosine distance: <=> operator returns distance (0=same, 2=opposite)
        # Similarity = 1 - (distance / 2) roughly, or just 1 - distance for normalized vectors
        # For cosine distance on normalized vectors: distance = 1 - cosine_similarity
        # So cosine_similarity = 1 - distance

        # We start with a base query
        where_clause = "1=1"
        params = [str(embedding)] # $1 = embedding vector string

        if project_id:
            where_clause += f" AND d.project_id = ${len(params) + 1}"
            params.append(project_id)

        # Add limit
        params.append(limit)
        limit_param_idx = len(params)

        query = f"""
            SELECT
                s.id, s.nav_title, s.content, s.sequence_order, s.document_id,
                d.title as document_title,
                1 - (s.embedding <=> $1) as similarity
            FROM sections s
            JOIN documents d ON s.document_id = d.id
            WHERE {where_clause}
            AND (1 - (s.embedding <=> $1)) > {threshold}
            ORDER BY similarity DESC
            LIMIT ${limit_param_idx}
        """

        try:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("Failed to search similar sections", error=str(e))
            return []

    async def get_document_content(self, document_id: str) -> Optional[str]:
        """Fetch raw content of a document."""
        if not self._pg_pool:
            return None

        query = "SELECT content FROM documents WHERE id = $1"

        try:
            async with self._pg_pool.acquire() as conn:
                return await conn.fetchval(query, document_id)
        except Exception as e:
            logger.error("Failed to fetch document content", error=str(e))
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

    async def save_extraction_result(
        self,
        project_id: str,
        document_id: str,  # 🆕 Added for source tracking
        characters: list[dict],
        events: list[dict],
        settings_list: list[dict],
        relationships: list[dict] = None  # 🆕 Added relationships
    ) -> None:
        """Save extracted entities to Neo4j for graph queries.
        
        🆕 Event Sourcing 아키텍처:
        - PostgreSQL 저장 제거 (Spring Boot가 Single Source of Truth)
        - Neo4j만 저장 (그래프 쿼리 최적화용)
        - 분석 결과는 Event로 발행되어 Spring Boot Consumer가 RDB에 저장
        """
        logger.info("Saving extraction result to Neo4j only", chars=len(characters), events=len(events))

        try:
            # PostgreSQL 저장 제거 (Event Sourcing - Spring Boot가 담당)
            # async with self._pg_pool.acquire() as conn:
            #     async with conn.transaction():
            #         for char in characters:
            #             await self._upsert_character(conn, project_id, char)
            #         for sitting in settings_list:
            #             await self._upsert_setting(conn, project_id, sitting)
            #         for evt in events:
            #             await self._insert_event(conn, project_id, evt)

            # Sync to Neo4j only (그래프 쿼리 최적화용)
            await self.ensure_neo4j_connected()
            
            if self._neo4j_driver:
                logger.info("[DEBUG] Starting Neo4j sync...")
                await self._sync_to_neo4j(project_id, document_id, characters, events, settings_list, relationships or [])
                logger.info("[DEBUG] Neo4j sync complete.")
            else:
                logger.warning("[DEBUG] Neo4j driver not available, skipping sync.")

        except Exception as e:
            logger.error("Failed to persist to Neo4j", error=str(e))
            raise e

    async def _upsert_character(self, conn, project_id, char):
        query = """
            INSERT INTO characters (id, project_id, name, role, description, aliases_json, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            ON CONFLICT (project_id, name) DO UPDATE SET
                role = EXCLUDED.role,
                description = EXCLUDED.description,
                aliases_json = EXCLUDED.aliases_json,
                updated_at = NOW()
        """
        import json
        import uuid

        # Extract name from top-level or nested profile
        char_name = char.get("name") or (char.get("profile", {}) or {}).get("name")

        # Skip characters without name (NOT NULL constraint)
        if not char_name:
            return

        # Validate or generate UUID
        raw_id = char.get("id") or char.get("_id")
        try:
            char_uuid = str(uuid.UUID(raw_id)) if raw_id else str(uuid.uuid4())
        except (ValueError, AttributeError):
            # Invalid UUID format, generate new one
            char_uuid = str(uuid.uuid4())

        aliases = json.dumps(char.get("aliases", []))
        await conn.execute(
            query,
            char_uuid,
            project_id,
            char_name,
            char.get("role", "Unknown"),
            char.get("description", ""),
            aliases
        )

    async def _upsert_setting(self, conn, project_id, setting):
        query = """
            INSERT INTO settings (id, project_id, name, location_type, description, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
            ON CONFLICT (project_id, name) DO UPDATE SET
                location_type = EXCLUDED.location_type,
                description = EXCLUDED.description,
                updated_at = NOW()
        """
        import uuid

        # Validate or generate UUID
        raw_id = setting.get("id")
        try:
            setting_uuid = str(uuid.UUID(raw_id)) if raw_id else str(uuid.uuid4())
        except (ValueError, AttributeError):
            setting_uuid = str(uuid.uuid4())

        await conn.execute(
            query,
            setting_uuid,
            project_id,
            setting.get("name"),
            setting.get("location_type", "Unknown"),
            setting.get("description", "")
        )

    async def _insert_event(self, conn, project_id, evt):
        query = """
            INSERT INTO events (id, project_id, document_id, event_type, description, chapter, sequence_order, participants, location, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
                description = EXCLUDED.description,
                participants = EXCLUDED.participants,
                location = EXCLUDED.location,
                chapter = EXCLUDED.chapter,
                sequence_order = EXCLUDED.sequence_order,
                updated_at = NOW()
        """
        import json
        import uuid

        # Validate or generate UUID
        raw_id = evt.get("event_id") or evt.get("id")
        try:
            evt_uuid = str(uuid.UUID(raw_id)) if raw_id else str(uuid.uuid4())
        except (ValueError, AttributeError):
            evt_uuid = str(uuid.uuid4())

        participants = json.dumps(evt.get("participants", []))
        await conn.execute(
            query,
            evt_uuid,
            project_id,
            evt.get("document_id"),
            evt.get("event_type", "Unknown"),
            evt.get("description", "") or evt.get("summary", ""),
            evt.get("chapter", 0),
            evt.get("sequence_order", 0),
            participants,
            evt.get("location_ref", "")
        )

    async def get_previous_section_hashes(self, document_id: str) -> list[dict]:
        """Get previously saved section hashes for incremental analysis.
        
        Returns:
            List of dicts with sequence_order and content_hash
        """
        if not self._pg_pool:
            return []
            
        try:
            async with self._pg_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT sequence_order, content_hash, nav_title
                    FROM sections
                    WHERE document_id = $1
                    ORDER BY sequence_order
                """, document_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"Failed to get section hashes: {e}")
            return []

    def detect_change_point(
        self, 
        previous_hashes: list[dict], 
        new_sections: list[dict]
    ) -> int:
        """Detect first section that changed.
        
        Args:
            previous_hashes: List of {sequence_order, content_hash} from DB
            new_sections: List of section dicts with content
            
        Returns:
            0-based index of first changed section, or -1 if no change
        """
        import hashlib
        
        # 🆕 If no previous hashes exist, this is first analysis - analyze everything
        if not previous_hashes:
            logger.info("[INCREMENTAL] No previous hashes found, full analysis required")
            return 0
        
        for i, section in enumerate(new_sections):
            content = section.get("content", "")
            new_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
            
            # If we've run out of previous sections, this is new content
            if i >= len(previous_hashes):
                logger.info(f"[INCREMENTAL] New section detected at index {i}")
                return i
            
            # If hash doesn't match, this section changed
            old_h = previous_hashes[i].get("content_hash")
            if old_h != new_hash:
                logger.info(f"[INCREMENTAL] Change detected at section {i+1}", old=old_h, new=new_hash)
                return i
            else:
                logger.debug(f"[INCREMENTAL] Section {i+1} match", hash=new_hash)
        
        # All sections match - check if there are fewer sections now
        if len(new_sections) < len(previous_hashes):
            logger.info("[INCREMENTAL] Sections were removed, full re-analysis needed")
            return 0
        
        # No changes
        return -1

    async def get_previous_summary(self, document_id: str) -> Optional[str]:
        """Get previous document summary for context in incremental analysis."""
        if not self._pg_pool:
            return None
            
        try:
            async with self._pg_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT summary FROM document_summaries
                    WHERE document_id = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                """, document_id)
                return row['summary'] if row else None
        except Exception as e:
            logger.warning(f"Failed to get previous summary: {e}")
            return None

    async def get_intra_chapter_summaries(
        self,
        project_id: str,
        parent_folder_id: str,
        current_document_id: str,
        limit: int = 5
    ) -> list[str]:
        """Get summaries of other documents in the same chapter (parent_folder).
        
        This provides context for the current document by fetching summaries
        of preceding documents in the same chapter/folder.
        
        Args:
            project_id: Project UUID
            parent_folder_id: Parent folder ID (represents chapter)
            current_document_id: Current document ID (to exclude)
            limit: Maximum number of summaries to retrieve
            
        Returns:
            List of summary strings from earlier documents in same chapter
        """
        if not self._pg_pool or not parent_folder_id:
            return []
            
        try:
            async with self._pg_pool.acquire() as conn:
                # Join documents and document_summaries to get summaries
                # of documents in the same parent folder, ordered by creation
                rows = await conn.fetch("""
                    SELECT ds.summary
                    FROM document_summaries ds
                    JOIN documents d ON ds.document_id = d.id
                    WHERE d.parent_id = $1
                      AND d.project_id = $2
                      AND d.id != $3
                      AND ds.level = 3
                    ORDER BY d.created_at ASC
                    LIMIT $4
                """, parent_folder_id, project_id, current_document_id, limit)
                
                summaries = [row['summary'] for row in rows if row.get('summary')]
                logger.info(f"[INTRA-CHAPTER] Retrieved {len(summaries)} summaries from same chapter")
                return summaries
                
        except Exception as e:
            # If documents table structure is different, log and return empty
            logger.warning(f"[INTRA-CHAPTER] Failed to get intra-chapter summaries: {e}")
            return []

    async def save_sections(self, document_id: str, sections: list[dict]) -> int:
        """Save semantic sections with embeddings to PostgreSQL.
        
        Args:
            document_id: Document UUID
            sections: List of section dicts from ChunkingService
            
        Returns:
            Number of saved sections
        """
        if not self._pg_pool:
            logger.warning("PostgreSQL pool not available, skipping section save")
            return 0
            
        if not sections:
            return 0

        logger.info("Saving vector sections", document_id=document_id, count=len(sections))
        
        saved_count = 0
        try:
            async with self._pg_pool.acquire() as conn:
                # Prepare statement for bulk insert
                # Note: We use execute_many for better performance
                
                # First delete existing sections for this document to avoid duplicates
                # (Optional: depends on business logic, here we replace)
                await conn.execute("DELETE FROM sections WHERE document_id = $1", document_id)
                
                # Insert new sections
                data_list = []
                for idx, section in enumerate(sections):
                    sec_id = str(uuid.uuid4())
                    content = section.get("content", "")
                    embedding = section.get("embedding") # List[float]
                    nav_title = section.get("title", f"Section {idx+1}")
                    
                    # 🆕 Generate content hash for incremental analysis
                    import hashlib
                    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
                    
                    # embedding must be passed as string format '[1.0, 2.0, ...]' for asyncpg if not using type codec
                    if embedding is not None:
                        if hasattr(embedding, "tolist"):
                            embedding = str(embedding.tolist())
                        elif isinstance(embedding, list):
                            embedding = str(embedding)
                        else:
                            embedding = str(embedding)
                    else:
                        embedding = None
                        
                    data_list.append((
                        sec_id, 
                        document_id, 
                        content, 
                        embedding_str,  # pgvector accepts JSON string
                        idx + 1, 
                        nav_title,
                        content_hash  # 🆕
                    ))
                
                if data_list:
                    # executemany works with list of tuples
                    await conn.executemany("""
                        INSERT INTO sections (id, document_id, content, embedding, sequence_order, nav_title, content_hash, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                    """, data_list)
                    saved_count = len(data_list)
                    
        except Exception as e:
            logger.error("Failed to save sections to PG", error=str(e), document_id=document_id)
            # Don't raise, just log error so analysis can continue
            return 0
            
        return saved_count

    async def _cleanup_document_data(self, session, document_id: str) -> None:
        """재분석 전 document의 기존 데이터 정리.
        
        Character와 Setting의 source_documents에서 document_id를 제거하고,
        더 이상 참조되지 않는 엔티티는 삭제합니다.
        """
        # Character cleanup
        await session.run("""
            MATCH (c:Character)
            WHERE $doc_id IN coalesce(c.source_documents, [])
            SET c.source_documents = [d IN c.source_documents WHERE d <> $doc_id]
            
            WITH c
            WHERE size(coalesce(c.source_documents, [])) = 0
            DETACH DELETE c
        """, doc_id=document_id)
        
        # Setting cleanup
        await session.run("""
            MATCH (s:Setting)
            WHERE $doc_id IN coalesce(s.source_documents, [])
            SET s.source_documents = [d IN s.source_documents WHERE d <> $doc_id]
            
            WITH s
            WHERE size(coalesce(s.source_documents, [])) = 0
            DETACH DELETE s
        """, doc_id=document_id)
        
        # Event cleanup (Events는 document-scoped로 ID에 doc_id 포함)
        await session.run("""
            MATCH (e:Event)
            WHERE e.eventId STARTS WITH $doc_id_prefix
            DETACH DELETE e
        """, doc_id_prefix=f"{document_id}_")
        
        print(f"[NEO4J] Cleaned up existing data for document: {document_id}")

    async def _find_similar_character(
        self, session, project_id: str, embedding: list[float], threshold: float = 0.92
    ) -> Optional[str]:
        """Find existing character with similar embedding using cosine similarity."""
        if not embedding:
            return None
            
        try:
            result = await session.run("""
                MATCH (c:Character {project_id: $pid})
                WHERE c.embedding IS NOT NULL
                WITH c, 
                     reduce(dot = 0.0, i IN range(0, size(c.embedding)-1) | 
                         dot + c.embedding[i] * $emb[i]) /
                     (sqrt(reduce(a = 0.0, i IN range(0, size(c.embedding)-1) | a + c.embedding[i]^2)) *
                      sqrt(reduce(b = 0.0, i IN range(0, size($emb)-1) | b + $emb[i]^2))) AS score
                WHERE score > $threshold
                RETURN c.name AS name, score
                ORDER BY score DESC
                LIMIT 1
            """, pid=project_id, emb=embedding, threshold=threshold)
            
            record = await result.single()
            if record:
                logger.info(f"[DEDUP] Found similar character: {record['name']} (score={record['score']:.3f})")
                return record['name']
            return None
        except Exception as e:
            logger.warning(f"[DEDUP] Character similarity search failed: {e}")
            return None

    async def _find_similar_event(
        self, session, project_id: str, embedding: list[float], threshold: float = 0.92
    ) -> Optional[str]:
        """Find existing event with similar embedding using cosine similarity."""
        if not embedding:
            return None
            
        try:
            result = await session.run("""
                MATCH (e:Event {project_id: $pid})
                WHERE e.embedding IS NOT NULL
                WITH e,
                     reduce(dot = 0.0, i IN range(0, size(e.embedding)-1) | 
                         dot + e.embedding[i] * $emb[i]) /
                     (sqrt(reduce(a = 0.0, i IN range(0, size(e.embedding)-1) | a + e.embedding[i]^2)) *
                      sqrt(reduce(b = 0.0, i IN range(0, size($emb)-1) | b + $emb[i]^2))) AS score
                WHERE score > $threshold
                RETURN e.narrativeSummary AS summary, score
                ORDER BY score DESC
                LIMIT 1
            """, pid=project_id, emb=embedding, threshold=threshold)
            
            record = await result.single()
            if record:
                logger.info(f"[DEDUP] Found similar event (score={record['score']:.3f})")
                return record['summary']
            return None
        except Exception as e:
            logger.warning(f"[DEDUP] Event similarity search failed: {e}")
            return None

    async def _find_similar_setting(
        self, session, project_id: str, embedding: list[float], threshold: float = 0.92
    ) -> Optional[str]:
        """Find existing setting with similar embedding using cosine similarity."""
        if not embedding:
            return None
            
        try:
            result = await session.run("""
                MATCH (s:Setting {project_id: $pid})
                WHERE s.embedding IS NOT NULL
                WITH s,
                     reduce(dot = 0.0, i IN range(0, size(s.embedding)-1) | 
                         dot + s.embedding[i] * $emb[i]) /
                     (sqrt(reduce(a = 0.0, i IN range(0, size(s.embedding)-1) | a + s.embedding[i]^2)) *
                      sqrt(reduce(b = 0.0, i IN range(0, size($emb)-1) | b + $emb[i]^2))) AS score
                WHERE score > $threshold
                RETURN s.name AS name, score
                ORDER BY score DESC
                LIMIT 1
            """, pid=project_id, emb=embedding, threshold=threshold)
            
            record = await result.single()
            if record:
                logger.info(f"[DEDUP] Found similar setting: {record['name']} (score={record['score']:.3f})")
                return record['name']
            return None
        except Exception as e:
            logger.warning(f"[DEDUP] Setting similarity search failed: {e}")
            return None

    async def _sync_to_neo4j(self, project_id, document_id, characters, events, settings_list, relationships):
        """Neo4j에 분석 결과 동기화.
        
        Spring에서 삭제된 로직을 포함하여 전체 데이터를 저장합니다.
        """
        import json
        import re
        import uuid as uuid_mod

        async with self._neo4j_driver.session() as session:
            # 🆕 Cleanup 제거: Merge-with-History가 자동으로 처리
            # Cleanup하면 기존 데이터 삭제 후 재생성 → 불필요한 DB 부하
            # 작가가 글을 추가할 때마다 기존 정보가 사라지는 문제 방지
            # await self._cleanup_document_data(session, document_id)
            
            # ===== 1. Characters =====
            # Spring의 saveCharacters() + updateCharacterJsonFields() 로직 통합
            for char in characters:
                # Extract name from top-level or nested profile
                char_name = char.get("name") or (char.get("profile", {}) or {}).get("name")
                
                if not char_name:
                    continue
                
                char_name = char_name.strip()
                
                # Extract profile data
                profile = char.get("profile", {}) or {}
                
                # Build profile JSON for storage
                profile_json = json.dumps(profile, ensure_ascii=False) if profile else None
                
                # Extract current mood
                current_mood = char.get("current_mood", {}) or {}
                current_mood_json = json.dumps(current_mood, ensure_ascii=False) if current_mood else None
                
                # Extract appearance
                appearance = char.get("appearance", {}) or {}
                appearance_json = json.dumps(appearance, ensure_ascii=False) if appearance else None
                
                # Extract relations
                relations = char.get("relations", {}) or {}
                # Extract relations
                relations = char.get("relations", {}) or {}
                relations_json = json.dumps(relations, ensure_ascii=False) if relations else None

                # Extract embedding
                embedding = char.get("embedding") # List[float]
                
                # 🆕 Embedding-based deduplication: Find similar existing character
                existing_name = await self._find_similar_character(session, project_id, embedding)
                if existing_name and existing_name.lower() != char_name.lower():
                    logger.info(f"[DEDUP] Merging '{char_name}' with existing '{existing_name}'")
                    # Add current name as alias to existing character
                    await session.run("""
                        MATCH (c:Character {project_id: $pid, name: $existing_name})
                        SET c.aliases = CASE
                            WHEN c.aliases IS NULL THEN [$new_alias]
                            WHEN NOT $new_alias IN c.aliases THEN c.aliases + $new_alias
                            ELSE c.aliases
                        END
                    """, pid=project_id, existing_name=existing_name, new_alias=char_name)
                    char_name = existing_name  # Use existing name for MERGE
                
                await session.run(
                    """
                    MERGE (c:Character {project_id: $pid, name: $name})
                    SET 
                        // Merge-with-History: Keep first non-null value
                        c.role = CASE 
                            WHEN c.role IS NULL OR c.role = 'Unknown' THEN $role
                            WHEN $role IS NULL OR $role = 'Unknown' THEN c.role
                            WHEN size($role) > size(coalesce(c.role, '')) THEN $role
                            ELSE c.role
                        END,
                        c.status = coalesce(c.status, $status),
                        c.age = coalesce(c.age, $age),
                        c.gender = coalesce(c.gender, $gender),
                        
                        // Keep longer/more detailed version
                        c.profileJson = CASE
                            WHEN $profile_json IS NULL THEN c.profileJson
                            WHEN c.profileJson IS NULL THEN $profile_json
                            WHEN size($profile_json) > size(c.profileJson) THEN $profile_json
                            ELSE c.profileJson
                        END,
                        c.backstory = CASE
                            WHEN $backstory IS NULL THEN c.backstory
                            WHEN c.backstory IS NULL THEN $backstory
                            WHEN size($backstory) > size(c.backstory) THEN $backstory
                            ELSE c.backstory
                        END,
                        
                        c.currentMoodJson = $mood_json,  // Always update mood (temporal)
                        c.appearanceJson = coalesce(c.appearanceJson, $appearance_json),
                        c.relationsJson = coalesce(c.relationsJson, $relations_json),
                        
                        // Merge aliases (always set property, even if empty)
                        c.aliases = CASE
                            WHEN $aliases IS NULL OR size($aliases) = 0 THEN coalesce(c.aliases, [])
                            WHEN c.aliases IS NULL THEN $aliases
                            ELSE c.aliases + [a IN $aliases WHERE NOT a IN c.aliases]
                        END,
                        
                        // Source documents tracking
                        c.source_documents = CASE 
                            WHEN c.source_documents IS NULL THEN [$doc_id]
                            WHEN NOT $doc_id IN c.source_documents THEN c.source_documents + $doc_id
                            ELSE c.source_documents
                        END,

                        // Save Embedding (Vector)
                        c.embedding = $embedding
                    """,
                    pid=project_id,
                    name=char_name,
                    doc_id=document_id,
                    role=char.get("role", "Unknown"),
                    status=char.get("status", "Unknown"),
                    age=profile.get("age"),
                    gender=profile.get("gender"),
                    profile_json=profile_json,
                    backstory=profile.get("backstory", ""),
                    mood_json=current_mood_json,
                    appearance_json=appearance_json,
                    relations_json=relations_json,
                    aliases=char.get("aliases") or [],
                    embedding=embedding
                )
            
            # ===== 2. Settings (Locations) =====
            # Spring의 saveSettings() 로직 통합
            for setting in settings_list:
                setting_name = setting.get("name")
                
                if not setting_name:
                    continue
                
                # 🆕 Generate DETERMINISTIC setting_id from project_id + name
                # This ensures same setting always gets same ID, avoiding UNIQUE constraint violations
                setting_id = str(uuid_mod.uuid5(uuid_mod.UUID(project_id), f"setting_{setting_name}"))
                
                # 🆕 Generate embedding for setting if not present
                setting_embedding = setting.get("embedding")
                if not setting_embedding:
                    # Generate embedding from name + description
                    setting_text = f"{setting_name}: {setting.get('description', '')}"
                    try:
                        setting_embedding = await self.get_embedding(setting_text)
                    except Exception:
                        setting_embedding = None
                
                # 🆕 Embedding-based deduplication: Find similar existing setting
                existing_name = await self._find_similar_setting(session, project_id, setting_embedding)
                if existing_name and existing_name.lower() != setting_name.lower():
                    logger.info(f"[DEDUP] Merging setting '{setting_name}' with existing '{existing_name}'")
                    # Add current name as alias
                    await session.run("""
                        MATCH (s:Setting {project_id: $pid, name: $existing_name})
                        SET s.aliases = CASE
                            WHEN s.aliases IS NULL THEN [$new_alias]
                            WHEN NOT $new_alias IN s.aliases THEN s.aliases + $new_alias
                            ELSE s.aliases
                        END
                    """, pid=project_id, existing_name=existing_name, new_alias=setting_name)
                    setting_name = existing_name  # Use existing name for MERGE

                await session.run(
                    """
                    MERGE (s:Setting {project_id: $pid, name: $name})
                    SET 
                        s.settingId = coalesce(s.settingId, $setting_id),
                        
                        // Merge-with-History: Keep first non-null value
                        s.locationType = coalesce(s.locationType, $loc_type),
                        
                        // Keep longer description
                        s.description = CASE
                            WHEN $desc IS NULL THEN s.description
                            WHEN s.description IS NULL THEN $desc
                            WHEN size($desc) > size(s.description) THEN $desc
                            ELSE s.description
                        END,
                        s.visualBackground = CASE
                            WHEN $visual_bg IS NULL THEN s.visualBackground
                            WHEN s.visualBackground IS NULL THEN $visual_bg
                            WHEN size($visual_bg) > size(s.visualBackground) THEN $visual_bg
                            ELSE s.visualBackground
                        END,
                        
                        s.atmosphere = coalesce(s.atmosphere, $atmosphere),
                        s.timeOfDay = coalesce(s.timeOfDay, $time_of_day),
                        s.lighting = coalesce(s.lighting, $lighting),
                        s.weather = coalesce(s.weather, $weather),
                        
                        // Merge notable features (accumulate)
                        s.notableFeatures = CASE
                            WHEN s.notableFeatures IS NULL THEN $notable_features
                            WHEN $notable_features IS NULL THEN s.notableFeatures
                            ELSE [f IN (s.notableFeatures + $notable_features) WHERE f IS NOT NULL]
                        END,
                        
                        s.significance = coalesce(s.significance, $significance),
                        s.isPrimary = coalesce(s.isPrimary, $is_primary),
                        s.parentLocation = $parent_location,
                        s.artStyle = $art_style,
                        
                        // Source documents tracking
                        s.source_documents = CASE 
                            WHEN s.source_documents IS NULL THEN [$doc_id]
                            WHEN NOT $doc_id IN s.source_documents THEN s.source_documents + $doc_id
                            ELSE s.source_documents
                        END,
                        
                        // Save Embedding (Vector)
                        s.embedding = $embedding
                    """,
                    pid=project_id,
                    name=setting_name,
                    setting_id=setting_id,
                    doc_id=document_id,
                    loc_type=setting.get("location_type", "Unknown"),
                    desc=setting.get("description", ""),
                    visual_bg=setting.get("visual_background", ""),
                    atmosphere=setting.get("atmosphere", ""),
                    time_of_day=setting.get("time_of_day"),
                    lighting=setting.get("lighting"),
                    weather=setting.get("weather"),
                    notable_features=setting.get("notable_features", []),
                    significance=setting.get("significance", ""),
                    is_primary=setting.get("is_primary", False),
                    parent_location=setting.get("parent_location"),
                    art_style=setting.get("art_style"),
                    embedding=setting_embedding
                )
            
            # ===== 3. Events =====
            # Spring의 saveEvents() 로직 통합
            # 🆕 Event ID는 document-scoped: {document_id}_{event_id}
            for evt in events:
                raw_evt_id = evt.get("event_id") or evt.get("id")
                # Document-scoped event ID
                evt_id_with_doc = f"{document_id}_{raw_evt_id}" if raw_evt_id else f"{document_id}_{uuid_mod.uuid4()}"
                
                try:
                    evt_uuid = str(uuid_mod.UUID(raw_evt_id)) if raw_evt_id else str(uuid_mod.uuid4())
                except (ValueError, AttributeError):
                    evt_uuid = evt_id_with_doc

                # 🆕 Embedding-based deduplication: Find similar existing event
                evt_embedding = evt.get("embedding")
                narrative_summary = evt.get("narrative_summary", "")
                
                existing_summary = await self._find_similar_event(session, project_id, evt_embedding)
                if existing_summary and existing_summary != narrative_summary:
                    logger.info(f"[DEDUP] Found similar event, using existing summary")
                    narrative_summary = existing_summary  # Use existing for MERGE

                await session.run(
                    """
                    MERGE (e:Event {project_id: $pid, narrativeSummary: $narrative_summary})
                    SET e.eventId = coalesce(e.eventId, $id_with_doc),
                        e.eventType = $event_type,
                        e.description = $desc,
                        e.chapter = $chapter,
                        e.sequenceOrder = $seq_order,
                        e.importance = $importance,
                        e.timestamp = $timestamp,
                        e.locationRef = $location_ref,
                        e.prevEventId = $prev_event_id,
                        e.documentId = CASE 
                            WHEN e.documentId IS NULL THEN $doc_id
                            WHEN NOT $doc_id IN coalesce(e.source_documents, []) THEN e.documentId
                            ELSE e.documentId
                        END,
                        e.source_documents = CASE 
                            WHEN e.source_documents IS NULL THEN [$doc_id]
                            WHEN NOT $doc_id IN e.source_documents THEN e.source_documents + $doc_id
                            ELSE e.source_documents
                        END,
                        
                        // Save Embedding (Vector)
                        e.embedding = $embedding
                    """,
                    id_with_doc=evt_id_with_doc,
                    id=evt_uuid,
                    pid=project_id,
                    doc_id=document_id,
                    event_type=evt.get("event_type", "Unknown"),
                    narrative_summary=narrative_summary,  # Use dedup-checked variable
                    desc=evt.get("description", "") or evt.get("summary", ""),
                    chapter=evt.get("chapter", 0),
                    seq_order=evt.get("sequence_order", 0),
                    importance=evt.get("importance", 5),
                    timestamp=evt.get("timestamp"),
                    location_ref=evt.get("location_ref", ""),
                    prev_event_id=evt.get("prev_event_id"),
                    embedding=evt.get("embedding")
                )

                # Create PARTICIPATES_IN relationships (Character -> Event)
                participants = evt.get("participants", [])
                for participant_name in participants:
                    if not participant_name:
                        continue
                    
                    participant_name = participant_name.strip()
                    
                    await session.run(
                        """
                        MATCH (c:Character {project_id: $pid, name: $char_name})
                        MATCH (e:Event {project_id: $pid, narrativeSummary: $narrative_summary})
                        MERGE (c)-[r:PARTICIPATES_IN]->(e)
                        """,
                        pid=project_id,
                        char_name=participant_name,
                        narrative_summary=evt.get("narrative_summary", "")
                    )

                # Create HAPPENED_AT relationship (Event -> Setting)
                # Spring의 eventNeo4jRepository.createHappenedAtEdge() 로직
                location_ref = evt.get("location_ref") or evt.get("location")
                if location_ref:
                    await session.run(
                        """
                        MATCH (e:Event {project_id: $pid, narrativeSummary: $narrative_summary})
                        MATCH (s:Setting {project_id: $pid, name: $loc_name})
                        MERGE (e)-[r:HAPPENED_AT]->(s)
                        """,
                        pid=project_id,
                        narrative_summary=evt.get("narrative_summary", ""),
                        loc_name=location_ref
                    )

            # ===== 4. Relationships (Character <-> Character) =====
            # Spring의 saveRelationships() + createRelationship() 로직
            for rel in relationships:
                source_name = rel.get("source")
                target_name = rel.get("target")
                rel_type = (rel.get("type") or rel.get("relation_type") or "RELATED_TO").upper().replace(" ", "_")

                if not source_name or not target_name:
                    continue

                # Sanitize relationship type (Neo4j naming requirement)
                safe_rel_type = re.sub(r'[^A-Z0-9_]', '_', rel_type)
                if not safe_rel_type:
                    safe_rel_type = "RELATED_TO"

                # Create relationship with properties
                query = f"""
                    MATCH (a:Character {{projectId: $pid, name: $source}})
                    MATCH (b:Character {{projectId: $pid, name: $target}})
                    MERGE (a)-[r:{safe_rel_type}]->(b)
                    SET r.description = $desc, 
                        r.strength = $strength,
                        r.bidirectional = $bidirectional,
                        r.emotionalBond = $emotional_bond,
                        r.functionalTrust = $functional_trust,
                        r.valueAlignment = $value_alignment,
                        r.interdependence = $interdependence,
                        r.latentTension = $latent_tension
                """

                await session.run(
                    query,
                    pid=project_id,
                    source=source_name.strip(),
                    target=target_name.strip(),
                    desc=rel.get("description", ""),
                    strength=rel.get("strength", 5),
                    bidirectional=rel.get("bidirectional", False),
                    emotional_bond=rel.get("emotional_bond", 5),
                    functional_trust=rel.get("functional_trust", 5),
                    value_alignment=rel.get("value_alignment", 5),
                    interdependence=rel.get("interdependence", 5),
                    latent_tension=rel.get("latent_tension", 1)
                )

                # If bidirectional, create reverse relationship
                if rel.get("bidirectional", False):
                    reverse_query = f"""
                        MATCH (a:Character {{projectId: $pid, name: $source}})
                        MATCH (b:Character {{projectId: $pid, name: $target}})
                        MERGE (b)-[r:{safe_rel_type}]->(a)
                        SET r.description = $desc, 
                            r.strength = $strength,
                            r.bidirectional = $bidirectional,
                            r.emotionalBond = $emotional_bond,
                            r.functionalTrust = $functional_trust,
                            r.valueAlignment = $value_alignment,
                            r.interdependence = $interdependence,
                            r.latentTension = $latent_tension
                    """
                    await session.run(
                        reverse_query,
                        pid=project_id,
                        source=source_name.strip(),
                        target=target_name.strip(),
                        desc=rel.get("description", ""),
                        strength=rel.get("strength", 5),
                        bidirectional=True,
                        emotional_bond=rel.get("emotional_bond", 5),
                        functional_trust=rel.get("functional_trust", 5),
                        value_alignment=rel.get("value_alignment", 5),
                        interdependence=rel.get("interdependence", 5),
                        latent_tension=rel.get("latent_tension", 1)
                    )

        logger.info(
            "Neo4j sync completed",
            project_id=project_id,
            characters=len(characters),
            events=len(events),
            settings=len(settings_list),
            relationships=len(relationships)
        )




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


