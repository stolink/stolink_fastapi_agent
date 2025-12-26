"""Plot integration schemas."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ConnectionStrength(str, Enum):
    """Foreshadowing connection strength."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class ForeshadowingStatus(str, Enum):
    """Foreshadowing resolution status."""
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    ABANDONED = "abandoned"


class ForeshadowLink(BaseModel):
    """Link between foreshadowing setup and payoff."""
    foreshadow_id: str
    setup_chapter: int
    setup_content: str
    payoff_chapter: Optional[int] = None
    payoff_content: Optional[str] = None
    connection_strength: ConnectionStrength = Field(default=ConnectionStrength.MODERATE)
    status: ForeshadowingStatus = Field(default=ForeshadowingStatus.UNRESOLVED)


class PlotSummary(BaseModel):
    """Summary of plot at various levels."""
    overall_summary: str = Field(default="")
    chapter_summaries: list[dict] = Field(default_factory=list)
    major_plot_points: list[str] = Field(default_factory=list)


class StoryArc(BaseModel):
    """Story arc definition."""
    arc_id: str
    arc_name: str
    arc_type: str  # "character", "theme", "plot"
    subject: str  # character name or theme
    status: str  # "rising", "climax", "falling", "resolved"
    key_events: list[str] = Field(default_factory=list)


class TensionPoint(BaseModel):
    """Tension curve data point."""
    chapter: int
    scene: Optional[str] = None
    tension_level: int = Field(ge=1, le=10)
    description: str = Field(default="")


class PlotIntegrationResult(BaseModel):
    """Result of plot integrator agent."""
    foreshadowing_links: list[ForeshadowLink] = Field(default_factory=list)
    plot_summary: PlotSummary = Field(default_factory=PlotSummary)
    story_arcs: list[StoryArc] = Field(default_factory=list)
    tension_curve: list[TensionPoint] = Field(default_factory=list)
