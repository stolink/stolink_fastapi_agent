"""Setting/worldbuilding extraction schemas."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class LocationType(str, Enum):
    """Location type classification."""
    CASTLE = "castle"
    CITY = "city"
    VILLAGE = "village"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    SEA = "sea"
    DUNGEON = "dungeon"
    OTHER = "other"


class Location(BaseModel):
    """Location information."""
    location_id: str = Field(..., description="Location unique ID")
    name: str = Field(..., description="Location name")
    location_type: LocationType = Field(default=LocationType.OTHER)
    description: str = Field(default="", description="Location description")
    parent_location: Optional[str] = Field(None, description="Parent location")
    notable_features: list[str] = Field(default_factory=list)
    first_mentioned: Optional[str] = Field(None, description="First mention chapter")


class WorldRule(BaseModel):
    """Worldbuilding rule or law."""
    rule_id: str = Field(..., description="Rule ID")
    category: str = Field(..., description="Rule category (magic_system, physics, society...)")
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    exceptions: list[str] = Field(default_factory=list)
    importance: str = Field(default="MEDIUM", description="HIGH, MEDIUM, LOW")


class SettingExtractionResult(BaseModel):
    """Result of setting extraction agent."""
    world_name: Optional[str] = None
    era: Optional[str] = None
    technology_level: Optional[str] = None
    locations: list[Location] = Field(default_factory=list)
    rules: list[WorldRule] = Field(default_factory=list)
    restrictions: list[str] = Field(default_factory=list)
