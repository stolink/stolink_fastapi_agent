"""RabbitMQ message schemas for analysis requests.

Updated for hybrid approach:
- Spring Boot sends basic context (counts, identifiers)
- FastAPI can query DB directly for detailed data when needed
"""
from typing import Any, Optional
from pydantic import BaseModel, Field


class ExistingCharacterRef(BaseModel):
    """Reference to existing character (lightweight)."""
    id: str = Field(..., description="Character UUID from PostgreSQL")
    name: str = Field(..., description="Character name for matching")
    role: Optional[str] = Field(None, description="Character role (protagonist, antagonist, etc)")


class ExistingEventRef(BaseModel):
    """Reference to existing event (lightweight)."""
    id: str = Field(..., description="Event UUID from PostgreSQL")
    event_type: str = Field(..., description="Event type")
    summary: str = Field(..., description="Brief summary for context")
    chapter: Optional[int] = Field(None, description="Chapter number")


class ExistingRelationshipRef(BaseModel):
    """Reference to existing relationship from Neo4j (lightweight)."""
    source_name: str = Field(..., description="Source character name")
    target_name: str = Field(..., description="Target character name")
    relation_type: str = Field(..., description="Relationship type")
    strength: int = Field(default=5, ge=1, le=10)


class ExistingSettingRef(BaseModel):
    """Reference to existing setting/location (lightweight)."""
    id: str = Field(..., description="Setting UUID")
    name: str = Field(..., description="Location name")
    location_type: Optional[str] = Field(None, description="Location type")


class AnalysisContext(BaseModel):
    """Context information for analysis.
    
    This contains lightweight references to existing data.
    FastAPI can use these references to query full details from DB when needed.
    """
    # Previous chapter texts (for continuity analysis)
    previous_chapters: list[str] = Field(
        default_factory=list, 
        description="Previous chapter contents for context"
    )
    
    # Current document position
    chapter_number: Optional[int] = Field(None, description="Current chapter number")
    total_chapters: Optional[int] = Field(None, description="Total chapters in project")
    
    # Lightweight references (for matching and quick lookups)
    existing_characters: list[ExistingCharacterRef] = Field(
        default_factory=list,
        description="Existing character references from DB"
    )
    existing_events: list[ExistingEventRef] = Field(
        default_factory=list,
        description="Recent event references from DB"
    )
    existing_relationships: list[ExistingRelationshipRef] = Field(
        default_factory=list,
        description="Existing relationship references from Neo4j"
    )
    existing_settings: list[ExistingSettingRef] = Field(
        default_factory=list,
        description="Existing setting/location references"
    )
    
    # World rules summary (for consistency checking)
    world_rules_summary: Optional[str] = Field(
        None, 
        description="Summary of established world rules"
    )
    
    # Statistics for quick reference
    @property
    def character_count(self) -> int:
        return len(self.existing_characters)
    
    @property
    def event_count(self) -> int:
        return len(self.existing_events)


class AnalysisTaskMessage(BaseModel):
    """RabbitMQ message schema for analysis tasks.
    
    This message is published by Spring Boot when a writer requests
    story analysis from the AI system.
    
    Design: Hybrid approach
    - Spring Boot sends text + lightweight context
    - FastAPI can query DB directly for full details when needed
    """
    # Job identification
    job_id: str = Field(..., description="Unique job identifier")
    project_id: str = Field(..., description="Project UUID")
    document_id: str = Field(..., description="Document UUID being analyzed")
    
    # Story content
    content: str = Field(..., description="Story text content to analyze")
    
    # Context (optional, for enhanced analysis)
    context: Optional[AnalysisContext] = Field(
        default=None, 
        description="Analysis context with existing data references"
    )
    
    # Callback configuration
    callback_url: str = Field(..., description="Spring callback URL for results")
    
    # Tracing
    trace_id: Optional[str] = Field(
        None, 
        description="Global trace ID for distributed tracing"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job-12345",
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_id": "doc-uuid-123",
                "content": "아린은 검을 받아들었다. 카엘이 그녀를 바라보았다.",
                "context": {
                    "previous_chapters": [],
                    "chapter_number": 3,
                    "total_chapters": 10,
                    "existing_characters": [
                        {"id": "char-001", "name": "아린", "role": "protagonist"},
                        {"id": "char-002", "name": "카엘", "role": "supporting"}
                    ],
                    "existing_events": [],
                    "existing_relationships": [
                        {"source_name": "아린", "target_name": "카엘", "relation_type": "ALLY", "strength": 7}
                    ],
                    "existing_settings": [],
                    "world_rules_summary": "마법은 왕국에서 금지됨"
                },
                "callback_url": "http://spring:8080/api/internal/ai/analysis/callback",
                "trace_id": "trace-abc-123"
            }
        }
