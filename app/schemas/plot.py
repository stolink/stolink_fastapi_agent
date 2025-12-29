"""Plot integration schemas - Updated for Spring Boot compatibility.

Provides structured output for:
- Narrative beats with visual prompts
- Tension curve analysis
- Three-act structure mapping
- Foreshadowing tracking
"""
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class BeatType(str, Enum):
    """Narrative beat type classification."""
    SETUP = "SETUP"
    INCITING_INCIDENT = "INCITING_INCIDENT"
    RISING_ACTION = "RISING_ACTION"
    MIDPOINT = "MIDPOINT"
    COMPLICATION = "COMPLICATION"
    CRISIS = "CRISIS"
    CLIMAX = "CLIMAX"
    FALLING_ACTION = "FALLING_ACTION"
    RESOLUTION = "RESOLUTION"


class NarrativeBeat(BaseModel):
    """Individual narrative beat for multimedia generation."""
    beat_id: int = Field(..., description="Beat sequence number")
    text: str = Field(..., description="Beat description text")
    beat_type: BeatType = Field(default=BeatType.SETUP)
    event_ref: Optional[str] = Field(None, description="Reference to Event ID")
    visual_prompt: str = Field(default="", description="Visual prompt for image generation")


class ThreeActSection(BaseModel):
    """Section of three-act structure."""
    act: str = Field(..., description="Act name: setup, confrontation, resolution")
    event_ids: list[str] = Field(default_factory=list, description="Event IDs in this act")
    purpose: str = Field(default="", description="Purpose of this act section")


class Foreshadowing(BaseModel):
    """Foreshadowing element for narrative tracking."""
    foreshadow_id: str = Field(..., description="Unique foreshadowing ID (F001, F002...)")
    source_event: Optional[str] = Field(None, description="Source event ID")
    hint_text: str = Field(..., description="The foreshadowing hint text")
    predicted_outcome: Optional[str] = Field(None, description="Predicted narrative outcome")
    confidence: int = Field(default=5, ge=1, le=10, description="Confidence level 1-10")
    target_event: Optional[str] = Field(None, description="Target payoff event ID if resolved")


class PlotSummary(BaseModel):
    """Summary of plot narrative."""
    narrative: str = Field(default="", description="Overall narrative description")
    central_conflict: str = Field(default="", description="Central conflict type")


class MultimediaSummary(BaseModel):
    """Summary of multimedia-related content."""
    beat_count: int = Field(default=0)
    tension_curve_length: int = Field(default=0)
    has_visual_prompts: bool = Field(default=False)


class PlotIntegrationResult(BaseModel):
    """Result of plot integrator agent - Spring Boot compatible.
    
    Maps to Spring Boot's PlotIntegration entity.
    """
    # Summary
    plot_summary: PlotSummary = Field(default_factory=PlotSummary)
    overall_tension: float = Field(default=5.0, ge=0, le=10, description="Overall tension level")
    
    # Narrative structure
    narrative_beats: list[NarrativeBeat] = Field(default_factory=list)
    tension_curve: list[float] = Field(default_factory=list, description="Tension values per scene")
    three_act_structure: list[ThreeActSection] = Field(default_factory=list)
    
    # Foreshadowing
    foreshadowing: list[Foreshadowing] = Field(default_factory=list)
    
    # Metadata
    multimedia_summary: MultimediaSummary = Field(default_factory=MultimediaSummary)
