"""RabbitMQ message schemas for analysis requests."""
from typing import Optional
from pydantic import BaseModel, Field


class AnalysisContext(BaseModel):
    """Context information for analysis."""
    previous_chapters: list[str] = Field(default_factory=list, description="Previous chapter contents")
    existing_characters_count: int = Field(default=0, description="Number of existing characters in DB")
    existing_events_count: int = Field(default=0, description="Number of existing events in DB")


class AnalysisTaskMessage(BaseModel):
    """RabbitMQ message schema for analysis tasks.
    
    This message is published by Spring Boot when a writer requests
    story analysis from the AI system.
    """
    job_id: str = Field(..., description="Unique job identifier")
    project_id: str = Field(..., description="Project UUID")
    document_id: str = Field(..., description="Document UUID being analyzed")
    content: str = Field(..., description="Story text content to analyze")
    context: Optional[AnalysisContext] = Field(default=None, description="Analysis context")
    callback_url: str = Field(..., description="Spring callback URL for results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job-12345",
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_id": "doc-uuid-123",
                "content": "아린은 검을 받아들었다. 카엘이 그녀를 바라보았다.",
                "context": {
                    "previous_chapters": [],
                    "existing_characters_count": 2,
                    "existing_events_count": 5
                },
                "callback_url": "http://spring:8080/api/internal/ai/analysis/callback"
            }
        }
