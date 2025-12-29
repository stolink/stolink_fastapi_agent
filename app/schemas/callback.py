"""Spring callback schemas for analysis results - Updated for Spring Boot compatibility.

Includes all data categories that Spring Boot expects:
- Characters, Events, Settings, Relationships
- Dialogues, Emotions
- Plot Integration, Consistency Report, Validation
"""
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

from app.schemas.plot import PlotIntegrationResult
from app.schemas.consistency import ConsistencyReport
from app.schemas.validation import ValidationResult


class AnalysisMetadata(BaseModel):
    """Metadata about the analysis execution."""
    processing_time_ms: int = Field(default=0, description="Total processing time in milliseconds")
    tokens_used: int = Field(default=0, description="Total tokens consumed")
    trace_id: Optional[str] = Field(None, description="Distributed tracing ID")
    agents_executed: list[str] = Field(
        default_factory=list, 
        description="List of executed agent names"
    )


class FullAnalysisResult(BaseModel):
    """Complete analysis result structure - Spring Boot compatible.
    
    All fields match the expected schema in Spring Boot's AICallbackService.
    """
    # Level 1 Extraction Results
    characters: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    settings: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    
    # Level 1 Analysis Results
    dialogues: dict[str, Any] = Field(default_factory=dict)
    emotions: dict[str, Any] = Field(default_factory=dict)
    
    # Level 2 Analysis Results
    plot_integration: dict[str, Any] = Field(default_factory=dict)
    consistency_report: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    metadata: Optional[AnalysisMetadata] = None


class AnalysisCallbackPayload(BaseModel):
    """Callback payload sent to Spring Boot after analysis completion.
    
    This schema matches the expected format in Spring's AICallbackService.
    """
    job_id: str = Field(..., alias="jobId", description="Job identifier")
    status: Literal["COMPLETED", "WARNING", "FAILED"] = Field(..., description="Analysis status")
    result: Optional[FullAnalysisResult] = Field(default=None, description="Analysis results")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "jobId": "job-12345",
                "status": "COMPLETED",
                "result": {
                    "characters": [{"name": "Arin", "role": "protagonist"}],
                    "events": [{"event_id": "E001", "description": "Arin enters the forest"}],
                    "settings": [{"setting_id": "loc_forest_01", "location_name": "Dark Forest"}],
                    "relationships": [{"source": "Arin", "target": "Kael", "relation_type": "ALLY"}],
                    "dialogues": {"key_dialogues": []},
                    "emotions": {"emotion_states": []},
                    "plot_integration": {
                        "plot_summary": {"narrative": "..."},
                        "foreshadowing": [{"foreshadow_id": "F001", "hint_text": "..."}]
                    },
                    "consistency_report": {
                        "overall_score": 95,
                        "conflicts": [],
                        "resolution_summary": {"total_conflicts": 0}
                    },
                    "validation": {
                        "is_valid": True,
                        "quality_score": 98,
                        "action": "approve"
                    },
                    "metadata": {
                        "processing_time_ms": 5000,
                        "trace_id": "trace-123",
                        "agents_executed": ["character", "event", "setting"]
                    }
                },
                "error": None
            }
        }
