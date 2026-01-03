"""Vector search API endpoints.

Provides semantic search functionality using pgvector.
"""
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
import structlog

from app.services.db_query_service import get_db_service
from app.services.embedding_service import EmbeddingService

logger = structlog.get_logger()
router = APIRouter(prefix="/api/search", tags=["search"])


class SimilarSectionRequest(BaseModel):
    """Request for similar section search."""
    query: str = Field(..., description="Text to search for similar sections")
    project_id: Optional[str] = Field(None, description="Optional project filter")
    limit: int = Field(5, ge=1, le=20, description="Maximum results to return")
    threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")


class SectionResult(BaseModel):
    """A section result with similarity score."""
    id: str
    nav_title: Optional[str]
    content: str
    sequence_order: int
    document_id: str
    document_title: Optional[str] = None
    similarity: float


class SimilarSectionResponse(BaseModel):
    """Response containing similar sections."""
    query: str
    results: list[SectionResult]
    total: int


class ConsistencyContext(BaseModel):
    """Context for consistency checking."""
    document_id: str
    project_id: Optional[str] = None
    limit: int = Field(10, ge=1, le=50)


class ContextSection(BaseModel):
    """A context section for consistency checking."""
    id: str
    nav_title: Optional[str]
    content: str
    document_title: Optional[str] = None
    related_characters: list[str] = []
    related_events: list[str] = []


class ConsistencyContextResponse(BaseModel):
    """Response with context sections for consistency."""
    document_id: str
    sections: list[ContextSection]
    total: int


@router.post("/similar", response_model=SimilarSectionResponse)
async def search_similar_sections(request: SimilarSectionRequest):
    """Search for sections similar to the given text.
    
    Uses pgvector cosine similarity to find semantically related sections.
    """
    try:
        # Generate embedding for the query
        embedding_service = EmbeddingService()
        query_embedding = await embedding_service.generate_embedding_async(request.query)
        
        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate embedding")
        
        # Search for similar sections
        db_service = await get_db_service()
        results = await db_service.search_similar_sections(
            embedding=query_embedding,
            project_id=request.project_id,
            limit=request.limit,
            threshold=request.threshold
        )
        
        # Convert to response model
        section_results = []
        for row in results:
            section_results.append(SectionResult(
                id=str(row["id"]),
                nav_title=row.get("nav_title"),
                content=row["content"][:500] if row.get("content") else "",  # Truncate content
                sequence_order=row.get("sequence_order", 0),
                document_id=str(row["document_id"]),
                document_title=row.get("document_title"),
                similarity=float(row.get("similarity", 0))
            ))
        
        logger.info(
            "Similar section search completed",
            query_length=len(request.query),
            results_count=len(section_results)
        )
        
        return SimilarSectionResponse(
            query=request.query,
            results=section_results,
            total=len(section_results)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to search similar sections", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context", response_model=ConsistencyContextResponse)
async def get_consistency_context(request: ConsistencyContext):
    """Get context sections for consistency checking.
    
    Returns related sections from the same project that can be used
    to verify narrative consistency.
    """
    try:
        db_service = await get_db_service()
        results = await db_service.get_context_sections_for_document(
            document_id=request.document_id,
            limit=request.limit
        )
        
        # Convert to response model
        sections = []
        for row in results:
            # Parse JSON fields
            characters = []
            events = []
            if row.get("related_characters_json"):
                try:
                    import json
                    characters = json.loads(row["related_characters_json"])
                except:
                    pass
            if row.get("related_events_json"):
                try:
                    import json
                    events = json.loads(row["related_events_json"])
                except:
                    pass
            
            sections.append(ContextSection(
                id=str(row["id"]),
                nav_title=row.get("nav_title"),
                content=row["content"][:500] if row.get("content") else "",
                document_title=row.get("document_title"),
                related_characters=characters,
                related_events=events
            ))
        
        logger.info(
            "Context sections retrieved",
            document_id=request.document_id,
            sections_count=len(sections)
        )
        
        return ConsistencyContextResponse(
            document_id=request.document_id,
            sections=sections,
            total=len(sections)
        )
        
    except Exception as e:
        logger.error("Failed to get context sections", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
