"""Character extraction schemas - Production Level.

Enhanced for:
- Neo4j graph database integration (explicit relationships)
- Image generation AI (visual vs personality traits separation)
- Scene-aware emotion tracking (current mood/sentiment)

All list fields handle None by converting to empty lists.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Literal
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
    FORMER_ALLY = "FORMER_ALLY"
    FORMER_ENEMY = "FORMER_ENEMY"
    NEUTRAL = "NEUTRAL"
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
    
    @field_validator('appearance', 'attire', mode='before')
    @classmethod
    def list_none_to_empty(cls, v):
        return none_to_list(v)


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
    
    @field_validator('core_traits', 'flaws', 'values', mode='before')
    @classmethod
    def list_none_to_empty(cls, v):
        return none_to_list(v)


class CurrentMood(BaseModel):
    """Scene-specific emotional state for TTS/expression generation."""
    emotion: Optional[str] = Field(None, description="Primary emotion (e.g., 'tense', 'angry', 'hopeful')")
    intensity: Optional[int] = Field(5, ge=1, le=10, description="Emotion intensity 1-10")
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
    
    @field_validator('aliases', 'traits', 'relationships', mode='before')
    @classmethod
    def list_none_to_empty(cls, v):
        return none_to_list(v)


class CharacterExtractionResult(BaseModel):
    """Result of character extraction agent."""
    characters: list[CharacterExtraction] = Field(default_factory=list)
    extraction_confidence: float = Field(default=0.0, ge=0, le=1, description="Extraction confidence score")
    scene_context: Optional[str] = Field(None, description="Scene context for mood extraction")
    
    @field_validator('characters', mode='before')
    @classmethod
    def characters_none_to_list(cls, v):
        return none_to_list(v)


# =============================================================================
# A. Basic Profile (기본 정보)
# =============================================================================
class CharacterProfile(BaseModel):
    """Basic character profile information."""
    character_id: Optional[str] = Field(None, description="Primary Key / UUID")
    name: Optional[str] = Field(None, description="Character name")
    age: Optional[int] = Field(None, ge=0, description="Character age")
    gender: Optional[str] = Field(None, description="Gender (male/female/other)")
    race: Optional[str] = Field(None, description="Race/Species (e.g., human, elf, orc)")
    faction: Optional[str] = Field(None, description="Faction/Organization affiliation")
    mbti: Optional[str] = Field(None, description="MBTI personality type")
    personality: list[str] = Field(default_factory=list, description="Personality traits")
    chapter_appearance: Optional[int] = Field(None, ge=1, description="Chapter of first appearance")
    backstory: Optional[str] = Field(None, description="Character background story")
    
    @field_validator('personality', mode='before')
    @classmethod
    def personality_none_to_list(cls, v):
        return none_to_list(v)


# =============================================================================
# B. Appearance (외형 정보)
# =============================================================================
class CharacterAppearance(BaseModel):
    """Visual/physical appearance for image generation."""
    physique: Optional[str] = Field(None, description="Body type (e.g., muscular, slender)")
    skin_tone: Optional[str] = Field(None, description="Skin color/tone")
    eyes: Optional[str] = Field(None, description="Eye description (color, shape)")
    nose: Optional[str] = Field(None, description="Nose description")
    mouth: Optional[str] = Field(None, description="Mouth/lips description")
    hair_style: Optional[str] = Field(None, description="Hairstyle")
    hair_color: Optional[str] = Field(None, description="Hair color")
    attire: list[str] = Field(default_factory=list, description="Clothing and accessories")
    expression: Optional[str] = Field(None, description="Default facial expression")
    scars_tattoos: list[str] = Field(default_factory=list, description="Scars, tattoos, birthmarks")
    cyberware: list[str] = Field(default_factory=list, description="Cybernetic enhancements")
    
    @field_validator('attire', 'scars_tattoos', 'cyberware', mode='before')
    @classmethod
    def list_none_to_empty(cls, v):
        return none_to_list(v)


# =============================================================================
# C. Stats (능력치)
# =============================================================================
class CharacterStats(BaseModel):
    """Character statistics and abilities."""
    # Core stats
    str_: Optional[int] = Field(None, ge=0, alias="str", description="Strength")
    dex: Optional[int] = Field(None, ge=0, description="Dexterity")
    int_: Optional[int] = Field(None, ge=0, alias="int", description="Intelligence")
    con: Optional[int] = Field(None, ge=0, description="Constitution")
    
    # Combat stats
    attack: Optional[int] = Field(None, ge=0, description="Attack power")
    defense: Optional[int] = Field(None, ge=0, description="Defense power")
    crit_rate: Optional[float] = Field(None, ge=0, le=1, description="Critical hit rate (0-1)")
    evasion: Optional[float] = Field(None, ge=0, le=1, description="Evasion rate (0-1)")
    
    # Speed stats
    move_speed: Optional[float] = Field(None, ge=0, description="Movement speed")
    attack_speed: Optional[float] = Field(None, ge=0, description="Attack speed")
    cast_speed: Optional[float] = Field(None, ge=0, description="Spell casting speed")
    
    # Progression
    level: Optional[int] = Field(None, ge=1, description="Character level")
    exp: Optional[int] = Field(None, ge=0, description="Experience points")
    skills: list[str] = Field(default_factory=list, description="List of skills/abilities")

    class Config:
        populate_by_name = True
    
    @field_validator('skills', mode='before')
    @classmethod
    def skills_none_to_list(cls, v):
        return none_to_list(v)


# =============================================================================
# D. State & Resources (상태 및 자원)
# =============================================================================
class CharacterState(BaseModel):
    """Current character state and resources."""
    # Health
    hp: Optional[int] = Field(None, ge=0, description="Current HP")
    hp_max: Optional[int] = Field(None, ge=1, description="Maximum HP")
    
    # Mana
    mp: Optional[int] = Field(None, ge=0, description="Current MP/Mana")
    mp_max: Optional[int] = Field(None, ge=0, description="Maximum MP/Mana")
    
    # Stamina
    sp: Optional[int] = Field(None, ge=0, description="Current Stamina")
    sp_max: Optional[int] = Field(None, ge=0, description="Maximum Stamina")
    
    # Status
    health: Optional[str] = Field(None, description="Health condition (healthy/injured/critical)")
    status_effects: list[str] = Field(default_factory=list, description="Active status effects")
    location_id: Optional[str] = Field(None, description="Current location ID")
    
    @field_validator('status_effects', mode='before')
    @classmethod
    def status_effects_none_to_list(cls, v):
        return none_to_list(v)


# =============================================================================
# F. Relations & World Context (세계관/관계)
# =============================================================================
class CharacterRelations(BaseModel):
    """Character relationships and world knowledge.
    
    Naming convention:
    - graph: Relationship list (not "relations" to avoid relations.relations duplication)
    - event_refs: Event ID references (optimized for payload size)
    """
    graph: list[CharacterRelationship] = Field(
        default_factory=list, 
        description="List of relationships with other characters"
    )
    event_refs: list[str] = Field(
        default_factory=list, 
        description="Event IDs the character knows about (e.g., ['E001', 'E045'])"
    )
    location_context: Optional[str] = Field(
        None, 
        description="Current location context/description"
    )
    
    @field_validator('graph', 'event_refs', mode='before')
    @classmethod
    def list_none_to_empty(cls, v):
        return none_to_list(v)


# =============================================================================
# 1. AI/LLM Dialogue Configuration (AI/LLM 연동)
# =============================================================================
class DialogueConfig(BaseModel):
    """Configuration for AI dialogue generation."""
    tone: Optional[str] = Field(None, description="Speaking tone (formal/casual/aggressive)")
    catchphrases: list[str] = Field(default_factory=list, description="Signature phrases or habits")
    forbidden_topics: list[str] = Field(default_factory=list, description="Topics character avoids/refuses")
    known_events: list[str] = Field(default_factory=list, description="Known event IDs for dialogue context")
    secret_keys: list[str] = Field(default_factory=list, description="Secret information the character holds")
    embedding_id: Optional[str] = Field(None, description="Vector DB embedding ID for RAG")
    
    @field_validator('catchphrases', 'forbidden_topics', 'known_events', 'secret_keys', mode='before')
    @classmethod
    def list_none_to_empty(cls, v):
        return none_to_list(v)


# =============================================================================
# 2. Combat Configuration (전투/물리)
# =============================================================================
class CombatConfig(BaseModel):
    """Combat and physics configuration."""
    elemental_resist: dict[str, int] = Field(
        default_factory=dict, 
        description="Elemental resistance (e.g., {'fire': 50, 'ice': -20})"
    )
    cc_resist: dict[str, int] = Field(
        default_factory=dict, 
        description="Crowd control resistance (e.g., {'stun': 30})"
    )
    hitbox_radius: Optional[float] = Field(None, ge=0, description="Hitbox collision radius")
    mass: Optional[float] = Field(None, ge=0, description="Character mass for physics")
    aggro_radius: Optional[float] = Field(None, ge=0, description="Aggro detection range")
    cooldown_reduction: Optional[float] = Field(None, ge=0, le=1, description="Skill cooldown reduction (0-1)")
    attack_range: Optional[float] = Field(None, ge=0, description="Base attack range")
    
    @field_validator('elemental_resist', 'cc_resist', mode='before')
    @classmethod
    def dict_none_to_empty(cls, v):
        return none_to_dict(v)


# =============================================================================
# 3. Social Configuration (사회성/평판)
# =============================================================================
class SocialConfig(BaseModel):
    """Social standing and reputation."""
    faction_reputation: dict[str, int] = Field(
        default_factory=dict, 
        description="Reputation with factions (e.g., {'Empire': 100, 'Rebels': -50})"
    )
    global_karma: Optional[int] = Field(None, description="Good/Evil alignment score")
    rank: Optional[str] = Field(None, description="Social/military rank or title")
    influence: Optional[int] = Field(None, ge=0, description="Political/social influence points")
    
    @field_validator('faction_reputation', mode='before')
    @classmethod
    def dict_none_to_empty(cls, v):
        return none_to_dict(v)


# =============================================================================
# 4. Economy Configuration (경제)
# =============================================================================
class EconomyConfig(BaseModel):
    """Economic status and trading."""
    gold: Optional[int] = Field(None, ge=0, description="Currency amount")
    trade_status: Optional[str] = Field(None, description="Trade capability (merchant/blocked/normal)")


# =============================================================================
# 5. System Metadata (시스템 메타)
# =============================================================================
class SystemMeta(BaseModel):
    """System-level metadata for the character."""
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    is_active: Optional[bool] = Field(True, description="Whether character is active in story")
    data_version: Optional[str] = Field(None, description="Schema version for migrations")
    lock_version: Optional[int] = Field(None, ge=0, description="Optimistic locking version")
    plot_armor: Optional[bool] = Field(None, description="Character cannot die if True")
    is_player: Optional[bool] = Field(None, description="True if player-controlled character")


# =============================================================================
# Full Character - Unified Model
# =============================================================================
class FullCharacter(BaseModel):
    """Complete character data model integrating all aspects.
    
    This model unifies:
    - Basic profile and identity
    - Visual appearance for image generation
    - Personality and character depth
    - Game stats and progression
    - Current state and resources
    - Relationships and world knowledge
    - AI dialogue configuration
    - Combat mechanics
    - Social standing
    - Economic status
    - System metadata
    
    All fields are Optional to accommodate partial data extraction from text.
    """
    
    # === Basic Identity ===
    profile: CharacterProfile = Field(default_factory=CharacterProfile)
    role: Optional[CharacterRole] = Field(None, description="Character role type")
    aliases: list[str] = Field(default_factory=list, description="Nicknames or titles")
    status: Optional[str] = Field("alive", description="Current status: alive/deceased/unknown")
    
    # === Visual & Personality ===
    appearance: CharacterAppearance = Field(default_factory=CharacterAppearance)
    personality: PersonalityTraits = Field(default_factory=PersonalityTraits)
    visual: VisualTraits = Field(default_factory=VisualTraits)  # Legacy compatibility
    
    # === Game Mechanics ===
    stats: CharacterStats = Field(default_factory=CharacterStats)
    state: CharacterState = Field(default_factory=CharacterState)

    
    # === Relationships & World ===
    relations: CharacterRelations = Field(default_factory=CharacterRelations)
    current_mood: Optional[CurrentMood] = Field(None, description="Current emotional state")
    
    # === AI Integration ===
    dialogue: DialogueConfig = Field(default_factory=DialogueConfig)
    
    # === Combat System ===
    combat: CombatConfig = Field(default_factory=CombatConfig)
    
    # === Social & Economy ===
    social: SocialConfig = Field(default_factory=SocialConfig)
    economy: EconomyConfig = Field(default_factory=EconomyConfig)
    
    # === System ===
    meta: SystemMeta = Field(default_factory=SystemMeta)
    
    # === Extraction Metadata ===
    extraction_notes: Optional[str] = Field(None, description="Notes about the extraction process")
    
    @field_validator('aliases', mode='before')
    @classmethod
    def list_none_to_empty(cls, v):
        return none_to_list(v)


class FullCharacterExtractionResult(BaseModel):
    """Result of full character extraction."""
    characters: list[FullCharacter] = Field(default_factory=list)
    extraction_confidence: Optional[float] = Field(None, ge=0, le=1, description="Overall extraction confidence")
    source_context: Optional[str] = Field(None, description="Source text context")
    missing_fields_summary: Optional[str] = Field(None, description="Summary of fields that couldn't be extracted")
    
    @field_validator('characters', mode='before')
    @classmethod
    def characters_none_to_list(cls, v):
        return none_to_list(v)
