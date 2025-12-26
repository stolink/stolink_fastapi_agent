"""Spring callback schemas for analysis results."""
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class AnalysisMetadata(BaseModel):
    """Metadata about the analysis execution."""
    processing_time_ms: int = Field(..., description="Total processing time in milliseconds")
    tokens_used: int = Field(default=0, description="Total tokens consumed")
    agents_executed: list[str] = Field(default_factory=list, description="List of executed agent names")


class AnalysisCallbackPayload(BaseModel):
    """Callback payload sent to Spring Boot after analysis completion.
    
    This schema matches the expected format in Spring's AICallbackService.
    """
    job_id: str = Field(..., alias="jobId", description="Job identifier")
    status: Literal["COMPLETED", "WARNING", "FAILED"] = Field(..., description="Analysis status")
    result: Optional[dict[str, Any]] = Field(default=None, description="Analysis results")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "jobId": "job-12345",
                "status": "COMPLETED",
                "result": {
                    "characters": [],
                    "events": [],
                    "relationships": [],
                    "settings": {},
                    "dialogues": {},
                    "emotions": {},
                    "consistency_report": {},
                    "plot_integration": {}
                },
                "error": None
            }
        }


class FullAnalysisResult(BaseModel):
    """Complete analysis result structure."""
    characters: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)
    dialogues: dict[str, Any] = Field(default_factory=dict)
    emotions: dict[str, Any] = Field(default_factory=dict)
    consistency_report: dict[str, Any] = Field(default_factory=dict)
    plot_integration: dict[str, Any] = Field(default_factory=dict)
    metadata: Optional[AnalysisMetadata] = None
