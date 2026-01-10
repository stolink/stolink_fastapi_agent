"""Character extraction schemas - Production Level.

Matches actual callback JSON structure.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


def none_to_list(v: Any) -> list:
    """Convert None to empty list."""
    return v if v is not None else []


def none_to_dict(v: Any) -> dict:
    """Convert None to empty dict."""
    return v if v is not None else {}


class CharacterRole(str, Enum):
    """Character role types."""
    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    MENTOR = "mentor"
    SIDEKICK = "sidekick"
    CAMEO = "cameo"
    OTHER = "other"


class RelationshipType(str, Enum):
    """Relationship types for Neo4j graph."""
    FRIEND = "FRIEND"
    ENEMY = "ENEMY"
    FAMILY = "FAMILY"
    ROMANTIC = "ROMANTIC"
    MENTOR = "MENTOR"
    RIVAL = "RIVAL"
    ALLY = "ALLY"
    BETRAYER = "BETRAYER"
    NEUTRAL = "NEUTRAL"


class CharacterRelationship(BaseModel):
    """Relationship to another character - for Neo4j edges."""
    target: str = Field(..., description="Target character name")
    type: RelationshipType = Field(..., description="Current relationship type")
    strength: int = Field(default=5, ge=1, le=10, description="Relationship intensity 1-10")
    description: Optional[str] = Field(None, description="Brief relationship description")
    public_stance: Optional[str] = Field(None, description="Outward stance")
    private_feeling: Optional[str] = Field(None, description="Inner feeling")


class PersonalityTraits(BaseModel):
    """Personality traits object."""
    core_traits: list[str] = Field(default_factory=list, description="Core personality traits")
    flaws: list[str] = Field(default_factory=list, description="Character flaws")
    values: list[str] = Field(default_factory=list, description="Core values")
    
    @field_validator('core_traits', 'flaws', 'values', mode='before')
    @classmethod
    def list_none_to_empty(cls, v):
        return none_to_list(v)


class CharacterProfile(BaseModel):
    """Character profile information."""
    name: Optional[str] = Field(None, description="Character name")
    age: Optional[int] = Field(None, ge=0, description="Character age")
    gender: Optional[str] = Field(None, description="Gender")
    race: Optional[str] = Field(None, description="Race/Species")
    mbti: Optional[str] = Field(None, description="MBTI type")
    personality: PersonalityTraits = Field(default_factory=PersonalityTraits, description="Personality traits")
    backstory: Optional[str] = Field(None, description="Background story")
    faction: dict = Field(default_factory=dict, description="Faction with social info")


class CharacterAppearance(BaseModel):
    """Visual appearance for image generation."""
    physique: Optional[str] = Field(None, description="Body type")
    skin_tone: Optional[str] = Field(None, description="Skin color/tone")
    eyes: Optional[str] = Field(None, description="Eye description")
    nose: Optional[str] = Field(None, description="Nose description")
    mouth: Optional[str] = Field(None, description="Mouth description")
    hair_style: Optional[str] = Field(None, description="Hairstyle")
    hair_color: Optional[str] = Field(None, description="Hair color")
    attire: list[str] = Field(default_factory=list, description="Clothing and accessories")
    expression: Optional[str] = Field(None, description="Facial expression")
    scars_tattoos: list[str] = Field(default_factory=list, description="Scars, tattoos, birthmarks")
    style_context: dict = Field(default_factory=dict, description="Art style context")
    
    @field_validator('attire', 'scars_tattoos', mode='before')
    @classmethod
    def list_none_to_empty(cls, v):
        return none_to_list(v)


class CharacterRelations(BaseModel):
    """Character relationships and world knowledge."""
    graph: list[CharacterRelationship] = Field(default_factory=list, description="Relationships")
    event_refs: list[str] = Field(default_factory=list, description="Event IDs")
    
    @field_validator('graph', 'event_refs', mode='before')
    @classmethod
    def list_none_to_empty(cls, v):
        return none_to_list(v)


# =============================================================================
# Full Character - Unified Model (matches callback structure)
# =============================================================================
class FullCharacter(BaseModel):
    """Complete character data model for callback.
    
    This matches the actual callback JSON structure exactly.
    """
    
    # Root Level
    id: Optional[str] = Field(None, description="Character ID", serialization_alias="_id")
    role: Optional[CharacterRole] = Field(None, description="Character role")
    
    # Profile
    profile: CharacterProfile = Field(default_factory=CharacterProfile)
    
    # Basic Identity
    aliases: list[str] = Field(default_factory=list, description="Nicknames or titles")
    status: Optional[str] = Field("alive", description="alive/deceased/unknown")
    
    # Visual
    appearance: CharacterAppearance = Field(default_factory=CharacterAppearance)
    
    # Relationships
    relations: CharacterRelations = Field(default_factory=CharacterRelations)
    
    # Embedding
    embedding: list[float] = Field(default_factory=list, description="Vector for Neo4j")
    
    model_config = {"populate_by_name": True}
    
    @field_validator('aliases', 'embedding', mode='before')
    @classmethod
    def list_none_to_empty(cls, v):
        return none_to_list(v)


class FullCharacterExtractionResult(BaseModel):
    """Result of character extraction."""
    characters: list[FullCharacter] = Field(default_factory=list)
    extraction_confidence: Optional[float] = Field(None, ge=0, le=1)
    
    @field_validator('characters', mode='before')
    @classmethod
    def characters_none_to_list(cls, v):
        return none_to_list(v)


# Backward compatibility aliases
CharacterExtraction = FullCharacter
CharacterExtractionResult = FullCharacterExtractionResult
