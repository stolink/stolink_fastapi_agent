"""Dialogue analysis schemas."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class FormalityLevel(str, Enum):
    """Speech formality level."""
    FORMAL = "formal"
    INFORMAL = "informal"
    MIXED = "mixed"


class PowerDynamic(str, Enum):
    """Power dynamic between speakers."""
    SUPERIOR = "superior"
    EQUAL = "equal"
    SUBORDINATE = "subordinate"


class DialogueEvidence(BaseModel):
    """Evidence for dialogue-based relationship."""
    chapter: int
    quote: str


class SpeechPattern(BaseModel):
    """Character speech pattern analysis."""
    character_name: str = Field(..., description="Character name")
    formality_level: FormalityLevel = Field(default=FormalityLevel.MIXED)
    speech_characteristics: list[str] = Field(default_factory=list)
    vocabulary_level: Optional[str] = None
    emotional_expression: Optional[str] = None
    unique_phrases: list[str] = Field(default_factory=list)
    dialect: Optional[str] = None


class DialogueRelationship(BaseModel):
    """Relationship inferred from dialogue."""
    speaker: str
    listener: str
    formality_to_listener: FormalityLevel = Field(default=FormalityLevel.MIXED)
    power_dynamic: PowerDynamic = Field(default=PowerDynamic.EQUAL)
    intimacy_level: int = Field(default=5, ge=1, le=10)
    communication_style: Optional[str] = None
    evidence: list[DialogueEvidence] = Field(default_factory=list)


class KeyDialogue(BaseModel):
    """Significant dialogue excerpt."""
    dialogue_id: str
    participants: list[str]
    chapter: int
    content: str
    significance: str
    subtext: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class SubtextAnalysis(BaseModel):
    """Hidden meaning analysis."""
    character: str
    dialogue_context: str
    surface_meaning: str
    hidden_meaning: str
    indicators: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)


class DialogueAnalysisResult(BaseModel):
    """Result of dialogue analyzer agent."""
    speech_patterns: list[SpeechPattern] = Field(default_factory=list)
    dialogue_relationships: list[DialogueRelationship] = Field(default_factory=list)
    key_dialogues: list[KeyDialogue] = Field(default_factory=list)
    subtext_analysis: list[SubtextAnalysis] = Field(default_factory=list)
