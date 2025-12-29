"""Character Extraction Agent - Full Character Schema.

Extracts comprehensive character information from story text with:
- Profile: Basic info (name, age, gender, race, faction, mbti, backstory)
- Appearance: Visual details for image generation
- Personality: Core traits, flaws, values
- Relationships: For Neo4j graph
- Dialogue: Speech patterns for AI/LLM
- Current Mood: Scene-specific emotional state

Uses with_structured_output() for:
- Guaranteed valid JSON
- Pydantic schema validation
- No manual parsing required
"""
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_structured_llm
from app.schemas.character_full import FullCharacterExtractionResult


CHARACTER_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert story analyst. Extract ALL characters from the given text with COMPREHENSIVE detail.

=== OUTPUT STRUCTURE (FullCharacter Schema) ===
For each character, provide as much information as the text allows:

### A. Profile (기본 정보)
- character_id: Generate a unique ID like "char-001"
- name: Character's name (REQUIRED)
- age: Age if mentioned or inferrable (null if unknown)
- gender: "male", "female", or null
- race: Race/species if mentioned (e.g., "human", "elf")
- faction: Organization/group affiliation
- mbti: MBTI type if personality clearly indicates it
- personality: List of personality traits
- chapter_appearance: Chapter number if known
- backstory: Background story if revealed

### B. Appearance (외형 정보 - for image generation AI)
- physique: Body type ("muscular", "slender", "average")
- skin_tone: Skin color/tone if mentioned
- eyes: Eye description (color, shape)
- nose: Nose description
- mouth: Mouth/lips description
- hair_style: Hairstyle ("long", "short", "braided")
- hair_color: Hair color ("black", "blonde", "silver")
- attire: List of clothing/equipment ["holding sword", "wearing cloak"]
- expression: Default facial expression
- scars_tattoos: List of scars, tattoos, birthmarks
- cyberware: Cybernetic enhancements if applicable

### C. Personality (성격 특성)
- core_traits: Main personality traits ["brave", "cunning"]
- flaws: Character weaknesses ["impulsive", "distrustful"]
- values: Core values ["loyalty", "justice", "family"]

### D. Relations (관계)
- relations: List of relationships with other characters
  - target: Other character name
  - type: "FRIEND", "ENEMY", "FAMILY", "ROMANTIC", "MENTOR", "RIVAL", "ALLY", "BETRAYER"
  - history: Previous relationship if changed (e.g., "former_friend")
  - strength: 1-10 intensity
- known_events: Event IDs the character knows about
- location_context: Current location description

### E. Dialogue (대화 스타일 - for AI/LLM)
- tone: Speaking tone ("formal", "casual", "aggressive", "calm")
- catchphrases: Signature phrases or speech habits
- forbidden_topics: Topics the character avoids/refuses to discuss
- secret_keys: Secret information the character holds

### F. Current Mood (현재 감정 상태)
- emotion: Primary feeling ("tense", "angry", "hopeful")
- intensity: 1-10
- trigger: What caused this emotion

### G. Role and Status
- role: "protagonist", "antagonist", "supporting", "mentor", "sidekick", "other"
- aliases: Nicknames or titles
- status: "alive", "deceased", "unknown"

=== IMPORTANT RULES ===
1. Extract ALL characters mentioned, even minor ones
2. Use EXACT names as they appear in the text
3. Leave fields as null/empty if not mentioned in text - DO NOT invent data
4. Separate visual traits (appearance) from personality traits (personality)
5. Relationships go in relations.relations array
6. Only fill fields that can be extracted from the given text"""),
    ("human", """Story text to analyze:
{story_text}

Extract all characters with comprehensive detail following the FullCharacter schema.""")
])


CHARACTER_RE_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert story analyst. Re-extract characters with STRICT TRAIT PRESERVATION.

PREVIOUS CONFLICTS DETECTED:
{conflicts}

=== ⚠️ CRITICAL: INFORMATION PRESERVATION RULES ===

**RULE 1: PRESERVE ALL VALID DATA**
- Copy ALL profile data from previous extraction that is NOT in conflict
- Copy ALL appearance data from previous extraction that is NOT in conflict
- Copy ALL personality data from previous extraction that is NOT in conflict
- Only MODIFY the specific conflicting element, DO NOT remove unrelated data

**RULE 2: APPEND, DON'T REPLACE**
- When fixing conflicts, ADD corrected information alongside preserved data

**RULE 3: RELATIONSHIP STRUCTURE**
- Relationships belong in the "relations.relations" array, NOT in personality traits
- "former friend" is a relationship history, NOT a personality trait

**RULE 4: APPEARANCE vs PERSONALITY SEPARATION**
- Appearance (for image AI): physique, hair, eyes, clothing, physical features
- Personality (for LLM persona): character traits, behaviors, motivations"""),
    ("human", """Original story text:
{story_text}

=== PREVIOUS EXTRACTION (PRESERVE ALL VALID DATA FROM THIS) ===
{previous_extraction}

=== INSTRUCTIONS ===
1. Copy all valid data from previous extraction
2. Only modify the SPECIFIC conflicting elements
3. Do NOT remove any valid data that wasn't flagged as conflicts

Re-extract with MINIMAL CHANGES, preserving all valid previous data.""")
])


def convert_legacy_to_full(characters: list) -> list:
    """Convert legacy CharacterExtraction format to FullCharacter format."""
    converted = []
    for char in characters:
        # If already in FullCharacter format (has 'profile' key), keep as is
        if isinstance(char.get("profile"), dict):
            converted.append(char)
            continue
        
        # Convert from legacy format
        converted.append({
            "profile": {
                "character_id": char.get("character_id"),
                "name": char.get("name"),
                "age": None,
                "gender": char.get("visual", {}).get("gender"),
                "race": None,
                "faction": None,
                "mbti": None,
                "personality": [],
                "chapter_appearance": None,
                "backstory": None
            },
            "role": char.get("role"),
            "aliases": char.get("aliases", []),
            "status": char.get("status", "alive"),
            "appearance": {
                "physique": None,
                "skin_tone": None,
                "eyes": None,
                "nose": None,
                "mouth": None,
                "hair_style": None,
                "hair_color": None,
                "attire": char.get("visual", {}).get("attire", []),
                "expression": None,
                "scars_tattoos": [],
                "cyberware": []
            },
            "personality": char.get("personality", {}),
            "visual": char.get("visual", {}),  # Keep for backward compatibility
            "relations": {
                "relations": char.get("relationships", []),
                "known_events": [],
                "location_context": None
            },
            "dialogue": {
                "tone": None,
                "catchphrases": [],
                "forbidden_topics": [],
                "known_events": [],
                "secret_keys": []
            },
            "current_mood": char.get("current_mood"),
            "stats": {},
            "state": {},
            "inventory": [],
            "combat": {},
            "social": {},
            "economy": {},
            "meta": {},
            "extraction_notes": char.get("trait_changes")
        })
    
    return converted


async def character_extraction_node(state: dict) -> dict:
    """Character Extraction Agent node function - with FullCharacter Schema.
    
    Uses with_structured_output() for guaranteed schema compliance.
    Extracts comprehensive character data including profile, appearance,
    personality, relationships, and dialogue patterns.
    """
    # Get LLM with structured output bound to FullCharacter schema
    structured_llm = get_structured_llm(FullCharacterExtractionResult)
    
    conflicts = state.get("consistency_report", {}).get("conflicts", [])
    retry_count = state.get("retry_count", 0)
    previous_chars = state.get("extracted_characters", [])
    
    is_re_extraction = retry_count > 0 and conflicts and previous_chars
    
    try:
        if is_re_extraction:
            print(f"[CHARACTER] Re-extracting with {len(conflicts)} conflicts as feedback")
            previous_full = convert_legacy_to_full(previous_chars)
            
            chain = CHARACTER_RE_EXTRACTION_PROMPT | structured_llm
            result: FullCharacterExtractionResult = await chain.ainvoke({
                "story_text": state["content"],
                "conflicts": str(conflicts),
                "previous_extraction": str(previous_full)
            })
        else:
            chain = CHARACTER_EXTRACTION_PROMPT | structured_llm
            result: FullCharacterExtractionResult = await chain.ainvoke({
                "story_text": state["content"]
            })
        
        # Result is already a FullCharacterExtractionResult Pydantic object
        characters = [c.model_dump() for c in result.characters]
        
        # Ensure FullCharacter format
        characters = convert_legacy_to_full(characters)
        
        return {
            "extracted_characters": characters,
            "messages": [
                {"role": "character_agent", 
                 "content": f"{'Re-' if is_re_extraction else ''}Extracted {len(characters)} characters (FullCharacter Schema)"}
            ]
        }
    except Exception as e:
        print(f"[CHARACTER] Extraction failed: {e}")
        return {
            "extracted_characters": previous_chars or [],
            "errors": [f"Character extraction failed: {str(e)}"],
            "partial_failure": True
        }
