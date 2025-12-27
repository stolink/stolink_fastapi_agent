"""Setting/Location extraction schemas - Production Level.

Enhanced for:
- Neo4j graph database integration (location_id as node key)
- Image generation AI (visual_background for background prompts)
- Unique location identity for referential integrity
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class LocationType(str, Enum):
    """Location type classification."""
    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    CASTLE = "castle"
    CITY = "city"
    VILLAGE = "village"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    SEA = "sea"
    DUNGEON = "dungeon"
    ROAD = "road"
    OTHER = "other"


class TimeOfDay(str, Enum):
    """Time of day for visual rendering."""
    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    DUSK = "dusk"
    NIGHT = "night"
    UNKNOWN = "unknown"


class SettingExtraction(BaseModel):
    """Extracted setting/location information - Production Level.
    
    Role: "Stage Director" - Manages backgrounds, lighting, and atmosphere.
    Key: Defines location identity to prevent Event Agent from creating duplicates.
    """
    
    # === Neo4j Node Key ===
    setting_id: str = Field(..., description="Unique location ID (loc_forest_01, loc_castle_main...)")
    name: str = Field(..., description="Location name (Neo4j node key)")
    
    # === Classification ===
    location_type: LocationType = Field(default=LocationType.OTHER)
    parent_location: Optional[str] = Field(None, description="Parent location ID for hierarchical structure")
    
    # === Visual Prompt (for Image Generation) ===
    visual_background: str = Field(
        ..., 
        description="Detailed background prompt for image AI (e.g., 'Dense ancient forest with tall twisted trees, thick fog covering the ground, moonlight filtering through leaves')"
    )
    atmosphere: str = Field(
        default="neutral",
        description="Mood/atmosphere keywords (e.g., 'ominous, tense', 'peaceful, serene')"
    )
    time_of_day: TimeOfDay = Field(default=TimeOfDay.UNKNOWN)
    lighting: Optional[str] = Field(None, description="Lighting description for visual rendering")
    weather: Optional[str] = Field(None, description="Weather conditions")
    art_style: Optional[str] = Field(
        default="Dark Fantasy, Realistic, Cinematic Lighting",
        description="Art style for image generation (e.g., 'Dark Fantasy, Anime, Watercolor')"
    )
    
    # === Narrative Context ===
    description: str = Field(default="", description="Narrative description")
    notable_features: list[str] = Field(default_factory=list, description="Key features of the location")
    significance: Optional[str] = Field(None, description="Story significance of this location")
    first_mentioned: Optional[str] = Field(None, description="First appearance in story")
    is_primary: bool = Field(default=True, description="True if action happens here, False if only mentioned")


class WorldRule(BaseModel):
    """Worldbuilding rule or law."""
    rule_id: str = Field(..., description="Rule ID")
    category: str = Field(..., description="Rule category (magic_system, physics, society...)")
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    exceptions: list[str] = Field(default_factory=list)
    importance: str = Field(default="MEDIUM", description="HIGH, MEDIUM, LOW")


class SettingExtractionResult(BaseModel):
    """Result of setting extraction agent - Production Level."""
    settings: list[SettingExtraction] = Field(default_factory=list, description="Extracted locations")
    world_name: Optional[str] = None
    era: Optional[str] = None
    technology_level: Optional[str] = None
    rules: list[WorldRule] = Field(default_factory=list)
    extraction_confidence: float = Field(default=0.0, ge=0, le=1)
