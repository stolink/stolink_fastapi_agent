"""Character extraction schemas."""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class CharacterRole(str, Enum):
    """Character role types."""
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    MENTOR = "mentor"
    SIDEKICK = "sidekick"
    CAMEO = "cameo"
    OTHER = "other"


class PhysicalDescription(BaseModel):
    """Physical appearance description."""
    hair: Optional[str] = None
    eyes: Optional[str] = None
    height: Optional[str] = None
    distinctive_features: list[str] = Field(default_factory=list)


class CharacterExtraction(BaseModel):
    """Extracted character information."""
    name: str = Field(..., description="Character name")
    aliases: list[str] = Field(default_factory=list, description="Nicknames or titles")
    role: CharacterRole = Field(..., description="Character role type")
    traits: list[str] = Field(default_factory=list, max_length=5, description="Personality traits (max 5)")
    motivation: Optional[str] = Field(None, description="Primary motivation")
    secret: Optional[str] = Field(None, description="Hidden secret or agenda")
    physical: Optional[PhysicalDescription] = None
    status: str = Field(default="생존", description="Current status (생존/부상/사망)")
    first_appearance: Optional[str] = Field(None, description="First appearance location")


class CharacterExtractionResult(BaseModel):
    """Result of character extraction agent."""
    characters: list[CharacterExtraction] = Field(default_factory=list)
    extraction_confidence: float = Field(default=0.0, ge=0, le=1, description="Extraction confidence score")
