"""LangGraph State definition for story analysis pipeline."""
from typing import Annotated, Any, Literal, Optional
from pydantic import BaseModel, Field
from langgraph.graph import add_messages


class StoryAnalysisState(BaseModel):
    """Shared state for the multi-agent analysis pipeline.
    
    This state is passed through all agents in the LangGraph workflow.
    Each agent reads from and writes to specific fields.
    """
    
    # ===== Input Data =====
    content: str = Field(..., description="Original story text content")
    project_id: str = Field(..., description="Project UUID")
    document_id: str = Field(..., description="Document UUID")
    job_id: str = Field(..., description="Analysis job UUID")
    callback_url: str = Field(..., description="Spring callback endpoint")
    
    # ===== Existing Data (Context from DB) =====
    existing_characters: list[dict[str, Any]] = Field(
        default_factory=list, 
        description="Existing characters from PostgreSQL"
    )
    existing_events: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Existing events from PostgreSQL"
    )
    existing_relationships: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Existing relationships from Neo4j"
    )
    existing_settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Existing worldbuilding settings"
    )
    
    # ===== Level 1: Extraction Results =====
    extracted_characters: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Characters extracted by CharacterExtractionAgent"
    )
    extracted_events: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Events extracted by EventExtractionAgent"
    )
    extracted_settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Settings extracted by SettingExtractorAgent"
    )
    analyzed_dialogues: dict[str, Any] = Field(
        default_factory=dict,
        description="Dialogue analysis by DialogueAnalyzerAgent"
    )
    tracked_emotions: dict[str, Any] = Field(
        default_factory=dict,
        description="Emotion tracking by EmotionTrackerAgent"
    )
    
    # ===== Level 2: Analysis Results =====
    relationship_graph: dict[str, Any] = Field(
        default_factory=dict,
        description="Relationship graph by RelationshipAnalyzerAgent"
    )
    consistency_report: dict[str, Any] = Field(
        default_factory=dict,
        description="Consistency report by ConsistencyCheckerAgent"
    )
    plot_integration: dict[str, Any] = Field(
        default_factory=dict,
        description="Plot integration by PlotIntegratorAgent"
    )
    
    # ===== Level 3: Validation Results =====
    validation_result: dict[str, Any] = Field(
        default_factory=dict,
        description="Final validation by ValidatorAgent"
    )
    
    # ===== Control Flags =====
    extraction_done: bool = Field(default=False)
    analysis_done: bool = Field(default=False)
    validation_done: bool = Field(default=False)
    
    # ===== Agent Communication =====
    messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Agent-to-agent communication log"
    )
    
    # ===== Error Handling =====
    errors: list[str] = Field(default_factory=list)
    partial_failure: bool = Field(default=False)
    
    # ===== Metadata =====
    processing_start_time: Optional[float] = None
    tokens_used: int = Field(default=0)
    
    class Config:
        arbitrary_types_allowed = True


# Type alias for use in LangGraph
StoryAnalysisStateDict = dict[str, Any]
