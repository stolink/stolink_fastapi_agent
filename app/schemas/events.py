"""Event extraction schemas - Production Level.

Enhanced for:
- Neo4j graph edges (participants, location_ref, prev_event_id)
- Image generation AI (visual_scene for action/composition prompts)
- Referential integrity (references Character and Setting by ID)
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


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
    
    
    # === Metadata ===
    timestamp: Optional[TimeStamp] = Field(default=None)
    importance: int = Field(default=5, ge=1, le=10, description="Importance level (1-10)")
    
    # === Re-extraction tracking ===
    changes_made: Optional[str] = Field(None, description="Changes made during re-extraction")


class EventExtractionResult(BaseModel):
    """Result of event extraction agent - Production Level."""
    events: list[EventExtraction] = Field(default_factory=list)
    timeline_summary: str = Field(default="", description="Timeline summary")
    total_events: int = Field(default=0)
    extraction_confidence: float = Field(default=0.0, ge=0, le=1)
    
    # Validator to handle string input (LLM sometimes returns JSON string)
    @field_validator('events', mode='before')
    @classmethod
    def parse_events_string(cls, v):
        """Parse events from string if LLM returns JSON string instead of list."""
        if isinstance(v, str):
            import json
            import re
            
            # Clean JSON: remove trailing commas (common LLM error)
            cleaned = re.sub(r',\s*}', '}', v)
            cleaned = re.sub(r',\s*]', ']', cleaned)
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
            
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
            
            # Try to extract individual event objects
            results = []
            object_pattern = r'\{\s*"event_id"\s*:\s*"[^"]+"\s*,.*?\}(?=\s*[,\]]|\s*$)'
            matches = re.findall(object_pattern, cleaned, re.DOTALL)
            
            for match in matches:
                try:
                    fixed = match
                    open_braces = fixed.count('{')
                    close_braces = fixed.count('}')
                    if open_braces > close_braces:
                        fixed += '}' * (open_braces - close_braces)
                    
                    obj = json.loads(fixed)
                    if isinstance(obj, dict) and 'event_id' in obj:
                        results.append(obj)
                except json.JSONDecodeError:
                    continue
            
            if results:
                print(f"[EVENT] Recovered {len(results)} events from partial JSON")
                return results
            
            # Last resort: fix truncated JSON
            try:
                open_brackets = cleaned.count('[') - cleaned.count(']')
                open_braces = cleaned.count('{') - cleaned.count('}')
                fixed = cleaned + '}' * open_braces + ']' * open_brackets
                return json.loads(fixed)
            except json.JSONDecodeError as e:
                print(f"[EVENT] JSON parse error: {e}")
                return []
        return v if v is not None else []

