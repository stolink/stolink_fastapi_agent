"""Character extraction schemas - Production Level.

Enhanced for:
- Neo4j graph database integration (explicit relationships)
- Image generation AI (visual vs personality traits separation)
- Scene-aware emotion tracking (current mood/sentiment)
"""
from enum import Enum
from typing import Optional, Literal
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
    UNKNOWN = "UNKNOWN"


class CharacterRelationship(BaseModel):
    """Relationship to another character - for Neo4j edges."""
    target: str = Field(..., description="Target character name")
    type: RelationshipType = Field(..., description="Current relationship type")
    history: Optional[str] = Field(None, description="Previous relationship (e.g., 'former_friend')")
    strength: int = Field(default=5, ge=1, le=10, description="Relationship intensity 1-10")
    description: Optional[str] = Field(None, description="Brief relationship description")


class VisualTraits(BaseModel):
    """Visual/physical traits for image generation AI."""
    appearance: list[str] = Field(
        default_factory=list, 
        max_length=5,
        description="Physical appearance keywords (e.g., 'tall', 'scar on face', 'dark hair')"
    )
    attire: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Clothing/equipment (e.g., 'holding sword', 'wearing cloak')"
    )
    age_group: Optional[str] = Field(None, description="Age category: child/teen/young_adult/adult/elderly")
    gender: Optional[str] = Field(None, description="Gender: male/female/unknown")


class PersonalityTraits(BaseModel):
    """Internal personality traits for character understanding."""
    core_traits: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Core personality (e.g., 'brave', 'cunning', 'compassionate')"
    )
    flaws: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Character flaws (e.g., 'impulsive', 'distrustful')"
    )
    values: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Core values (e.g., 'loyalty', 'justice', 'family')"
    )


class CurrentMood(BaseModel):
    """Scene-specific emotional state for TTS/expression generation."""
    emotion: str = Field(..., description="Primary emotion (e.g., 'tense', 'angry', 'hopeful')")
    intensity: int = Field(default=5, ge=1, le=10, description="Emotion intensity 1-10")
    trigger: Optional[str] = Field(None, description="What caused this emotion")


class CharacterExtraction(BaseModel):
    """Extracted character information - Production Level."""
    
    # === Basic Identity ===
    name: str = Field(..., description="Character name")
    aliases: list[str] = Field(default_factory=list, description="Nicknames or titles")
    role: CharacterRole = Field(..., description="Character role type")
    status: str = Field(default="alive", description="Current status: alive/deceased/unknown")
    
    # === Separated Traits (for different AI systems) ===
    visual: VisualTraits = Field(
        default_factory=VisualTraits,
        description="Visual traits for image generation"
    )
    personality: PersonalityTraits = Field(
        default_factory=PersonalityTraits,
        description="Personality traits for character understanding"
    )
    
    # === Legacy traits field (for backward compatibility) ===
    traits: list[str] = Field(
        default_factory=list, 
        max_length=7,
        description="[DEPRECATED] Use visual/personality instead. Combined traits list."
    )
    
    # === Relationships (for Neo4j graph) ===
    relationships: list[CharacterRelationship] = Field(
        default_factory=list,
        description="Explicit relationships with other characters"
    )
    
    # === Scene-specific State ===
    current_mood: Optional[CurrentMood] = Field(
        None,
        description="Current emotional state in this scene"
    )
    
    # === Character Background ===
    motivation: Optional[str] = Field(None, description="Primary motivation")
    secret: Optional[str] = Field(None, description="Hidden secret or agenda")
    first_appearance: Optional[str] = Field(None, description="First appearance location")
    
    # === Extraction Metadata ===
    trait_changes: Optional[str] = Field(None, description="Changes made during re-extraction")


class CharacterExtractionResult(BaseModel):
    """Result of character extraction agent."""
    characters: list[CharacterExtraction] = Field(default_factory=list)
    extraction_confidence: float = Field(default=0.0, ge=0, le=1, description="Extraction confidence score")
    scene_context: Optional[str] = Field(None, description="Scene context for mood extraction")
