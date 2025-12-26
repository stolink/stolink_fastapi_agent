"""Emotion tracking schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class EmotionState(BaseModel):
    """Character emotional state at a specific scene."""
    character: str
    chapter: int
    scene: str
    primary_emotion: str
    secondary_emotions: list[str] = Field(default_factory=list)
    intensity: int = Field(default=5, ge=1, le=10)
    physical_manifestation: list[str] = Field(default_factory=list)
    internal_monologue: Optional[str] = None
    coping_mechanism: Optional[str] = None


class EmotionPhase(BaseModel):
    """Single phase in emotion arc."""
    chapter: int
    emotion: str
    intensity: int = Field(ge=1, le=10)


class TurningPoint(BaseModel):
    """Emotional turning point."""
    chapter: int
    event: str
    before: str
    after: str


class EmotionArc(BaseModel):
    """Character emotion arc across story."""
    character: str
    arc_type: str  # e.g., "tragedy", "redemption", "growth"
    phases: list[EmotionPhase] = Field(default_factory=list)
    turning_points: list[TurningPoint] = Field(default_factory=list)


class EmotionalTrigger(BaseModel):
    """Event that triggers emotional response."""
    character: str
    trigger_event: str
    triggered_emotion: str
    trigger_type: str  # "external" or "internal"
    vulnerability: Optional[str] = None
    predicted_behavior: list[str] = Field(default_factory=list)
    chapter: int


class PsychologicalNote(BaseModel):
    """Psychological analysis note."""
    character: str
    note_type: str  # "motivation_analysis", "trauma", etc.
    content: str
    evidence: list[dict] = Field(default_factory=list)
    psychological_concept: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0, le=1)


class EmotionTrackingResult(BaseModel):
    """Result of emotion tracker agent."""
    emotion_states: list[EmotionState] = Field(default_factory=list)
    emotion_arcs: list[EmotionArc] = Field(default_factory=list)
    emotional_triggers: list[EmotionalTrigger] = Field(default_factory=list)
    psychological_notes: list[PsychologicalNote] = Field(default_factory=list)
