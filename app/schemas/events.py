"""Event extraction schemas."""
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


class TimeStamp(BaseModel):
    """Temporal information for events."""
    relative: Optional[str] = Field(None, description="Relative time (e.g., '3일 후')")
    absolute: Optional[str] = Field(None, description="Absolute time (e.g., '1492년 10월')")
    chapter: Optional[int] = Field(None, description="Chapter number")
    sequence_order: int = Field(..., description="Event sequence order")


class EventExtraction(BaseModel):
    """Extracted event information."""
    event_id: str = Field(..., description="Event identifier (E001, E002...)")
    description: str = Field(..., description="Event description")
    participants: list[str] = Field(default_factory=list, description="Participating characters")
    timestamp: TimeStamp
    location: Optional[str] = Field(None, description="Event location")
    event_type: EventType = Field(..., description="Event type")
    is_foreshadowing: bool = Field(default=False, description="Whether this is foreshadowing")
    foreshadowing_tag: Optional[str] = Field(None, description="Foreshadowing tag if applicable")
    importance: int = Field(default=5, ge=1, le=10, description="Importance level (1-10)")


class EventExtractionResult(BaseModel):
    """Result of event extraction agent."""
    events: list[EventExtraction] = Field(default_factory=list)
    timeline_summary: str = Field(default="", description="Timeline summary")
