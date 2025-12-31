"""LangGraph State definition for story analysis pipeline.

Updated to align with hybrid message schema:
- Trace ID for distributed tracing
- Context data from Spring Boot + optional DB enrichment
- Centralized TypedDict for LangGraph compatibility
"""
from typing import Annotated, Any, Literal, Optional, TypedDict
import operator
from pydantic import BaseModel, Field
from langgraph.graph import add_messages


class AnalysisState(TypedDict, total=False):
    """Centralized TypedDict for LangGraph state management.
    
    This replaces the local definition in graph.py.
    """
    # Input (never changes)
    content: str
    project_id: str
    document_id: str
    job_id: str
    callback_url: str
    
    # Tracing
    trace_id: str
    
    # Existing data (from Spring Boot context or DB query)
    existing_characters: list
    existing_events: list
    existing_relationships: list
    existing_settings: list
    
    # Extraction results
    extracted_characters: list
    extracted_events: list
    extracted_settings: list
    analyzed_dialogues: dict
    tracked_emotions: dict
    
    # Analysis results
    relationship_graph: dict
    consistency_report: dict
    plot_integration: dict
    
    # Validation
    validation_result: dict
    
    # Control flags (supervisor uses these)
    extraction_done: bool
    analysis_done: bool
    validation_done: bool
    retry_count: int
    force_fail: bool
    force_fail_reason: str
    
    # Accumulating fields (use operator.add reducer)
    messages: Annotated[list, operator.add]
    errors: Annotated[list, operator.add]


class StoryAnalysisState(BaseModel):
    """Shared state for the multi-agent analysis pipeline.
    
    This state is passed through all agents in the LangGraph workflow.
    Each agent reads from and writes to specific fields.
    
    Data Flow:
    1. Initial state created from RabbitMQ message (AnalysisTaskMessage)
    2. Optional: Enriched with DB queries via DatabaseQueryService
    3. Passed through extraction → analysis → validation agents
    """
    
    # ===== Input Data =====
    content: str = Field(..., description="Original story text content")
    project_id: str = Field(..., description="Project UUID")
    document_id: str = Field(..., description="Document UUID")
    job_id: str = Field(..., description="Analysis job UUID")
    callback_url: str = Field(..., description="Spring callback endpoint")
    
    # ===== Tracing =====
    trace_id: str = Field(default="", description="Global trace ID for distributed tracing")
    
    # ===== Context from Message =====
    chapter_number: Optional[int] = Field(None, description="Current chapter number")
    total_chapters: Optional[int] = Field(None, description="Total chapters in project")
    world_rules_summary: Optional[str] = Field(None, description="Summary of world rules")
    
    # ===== Existing Data (From Spring Boot context or DB query) =====
    existing_characters: list[dict[str, Any]] = Field(
        default_factory=list, 
        description="Existing character refs/data from Spring Boot or DB"
    )
    existing_events: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Existing event refs/data from Spring Boot or DB"
    )
    existing_relationships: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Existing relationships from Neo4j"
    )
    existing_settings: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Existing settings/locations"
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
    extracted_settings: list[dict[str, Any]] = Field(
        default_factory=list,
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
