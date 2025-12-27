"""Event extraction schemas - Production Level.

Enhanced for:
- Neo4j graph edges (participants, location_ref, prev_event_id)
- Image generation AI (visual_scene for action/composition prompts)
- Referential integrity (references Character and Setting by ID)
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event type classification."""
    ACTION = "action"
    DIALOGUE = "dialogue"
    REVELATION = "revelation"
    FLASHBACK = "flashback"
    FORESHADOWING = "foreshadowing"
    CONFRONTATION = "confrontation"
    TRANSITION = "transition"


class TimeStamp(BaseModel):
    """Temporal information for events."""
    relative: Optional[str] = Field(None, description="Relative time (e.g., '3일 후')")
    absolute: Optional[str] = Field(None, description="Absolute time (e.g., '1492년 10월')")
    chapter: Optional[int] = Field(None, description="Chapter number")
    sequence_order: int = Field(default=0, description="Event sequence order")


class EventExtraction(BaseModel):
    """Extracted event information - Production Level.
    
    Role: "Director" - Manages who, where, what happened.
    Key: Focus on references and visual scene description, NOT location details.
    """
    
    # === Event Identity ===
    event_id: str = Field(..., description="Event identifier (E001, E002...)")
    event_type: EventType = Field(..., description="Event type")
    
    # === Narrative Content ===
    narrative_summary: str = Field(..., description="Brief narrative summary of the event")
    description: str = Field(default="", description="Detailed event description")
    
    # === Graph Connections (for Neo4j) ===
    participants: list[str] = Field(
        default_factory=list, 
        description="Character names involved (creates INVOLVES edges)"
    )
    location_ref: Optional[str] = Field(
        None, 
        description="Setting name/ID reference (creates HAPPENS_AT edge)"
    )
    prev_event_id: Optional[str] = Field(
        None, 
        description="Previous event ID (creates NEXT edge for timeline)"
    )
    
    # === Visual Prompt (for Image Generation) ===
    visual_scene: str = Field(
        default="",
        description="Visual scene description for image AI (e.g., 'Two men facing each other with swords drawn, intense eye contact, low angle shot')"
    )
    camera_angle: Optional[str] = Field(
        None,
        description="Suggested camera angle (e.g., 'low angle', 'bird's eye', 'close-up')"
    )
    
    # === Metadata ===
    timestamp: Optional[TimeStamp] = Field(default=None)
    importance: int = Field(default=5, ge=1, le=10, description="Importance level (1-10)")
    is_foreshadowing: bool = Field(default=False, description="Whether this is foreshadowing")
    foreshadowing_tag: Optional[str] = Field(None, description="Foreshadowing tag if applicable")
    
    # === Re-extraction tracking ===
    changes_made: Optional[str] = Field(None, description="Changes made during re-extraction")


class EventExtractionResult(BaseModel):
    """Result of event extraction agent - Production Level."""
    events: list[EventExtraction] = Field(default_factory=list)
    timeline_summary: str = Field(default="", description="Timeline summary")
    total_events: int = Field(default=0)
    extraction_confidence: float = Field(default=0.0, ge=0, le=1)
