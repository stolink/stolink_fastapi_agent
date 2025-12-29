"""Character Extraction Agent - with Structured Output.

Extracts character information from story text with:
- Separated visual/personality traits (for image generation)
- Explicit relationships (for Neo4j graph)
- Scene-aware emotional state (for TTS/expression)

Uses with_structured_output() for:
- Guaranteed valid JSON
- Pydantic schema validation
- No manual parsing required
"""
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_structured_llm
from app.schemas.characters import CharacterExtractionResult


CHARACTER_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert story analyst. Extract ALL characters from the given text with PRODUCTION-LEVEL detail.

=== OUTPUT STRUCTURE ===
For each character, provide:

1. **Basic Info**
   - name: Character's name (REQUIRED)
   - role: "protagonist", "antagonist", "supporting", "mentor", "sidekick", "other"
   - status: "alive", "deceased", "unknown"

2. **Visual Traits** (for image generation AI)
   - appearance: Physical features ["tall", "scar on cheek", "dark hair"]
   - attire: Clothing/equipment ["holding sword", "wearing cloak"]
   - age_group: "child", "teen", "young_adult", "adult", "elderly"
   - gender: "male", "female", "unknown"

3. **Personality Traits** (for character understanding)
   - core_traits: Main personality ["brave", "cunning"]
   - flaws: Weaknesses ["impulsive", "distrustful"]
   - values: What they care about ["loyalty", "justice"]

4. **Relationships** (for Neo4j graph database)
   - target: Other character name
   - type: "FRIEND", "ENEMY", "FAMILY", "ROMANTIC", "MENTOR", "RIVAL", "ALLY", "BETRAYER"
   - history: Previous relationship if changed (e.g., "former_friend")
   - strength: 1-10 intensity

5. **Current Mood** (for this scene)
   - emotion: Primary feeling ("tense", "angry", "hopeful")
   - intensity: 1-10
   - trigger: What caused it

=== IMPORTANT RULES ===
1. Extract ALL characters mentioned, even minor ones
2. Use EXACT names as they appear in the text
3. Separate visual traits (physical) from personality traits (behavior)
4. Relationships go in the relationships array, NOT in personality traits"""),
    ("human", """Story text to analyze:
{story_text}

Extract all characters with full production-level detail.""")
])


CHARACTER_RE_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert story analyst. Re-extract characters with STRICT TRAIT PRESERVATION.

PREVIOUS CONFLICTS DETECTED:
{conflicts}

=== ⚠️ CRITICAL: INFORMATION PRESERVATION RULES ===

**RULE 1: PRESERVE ALL VALID DATA**
- Copy ALL visual traits from previous extraction that are NOT in conflict
- Copy ALL personality traits from previous extraction that are NOT in conflict
- Only MODIFY the specific conflicting element, DO NOT remove unrelated data

**RULE 2: APPEND, DON'T REPLACE**
- When fixing conflicts, ADD corrected information alongside preserved data

**RULE 3: RELATIONSHIP STRUCTURE**
- Relationships belong in the "relationships" array, NOT in personality traits
- "former friend" is a relationship history, NOT a personality trait

**RULE 4: VISUAL vs PERSONALITY SEPARATION**
- Visual (for image AI): appearance, clothing, equipment, physical features
- Personality (for LLM persona): character traits, behaviors, motivations"""),
    ("human", """Original story text:
{story_text}

=== PREVIOUS EXTRACTION (PRESERVE ALL VALID DATA FROM THIS) ===
{previous_extraction}

=== INSTRUCTIONS ===
1. Copy all valid data from previous extraction
2. Only modify the SPECIFIC conflicting elements
3. Do NOT remove any valid traits that weren't flagged as conflicts

Re-extract with MINIMAL CHANGES, preserving all valid previous data.""")
])


def convert_legacy_to_production(characters: list) -> list:
    """Convert legacy flat traits format to production format."""
    converted = []
    for char in characters:
        if isinstance(char.get("visual"), dict) and isinstance(char.get("personality"), dict):
            converted.append(char)
            continue
            
        traits = char.get("traits", [])
        visual_keywords = ["tall", "short", "young", "old", "scar", "hair", "eyes", "wearing", "holding", "muscular", "thin"]
        
        visual_traits = []
        personality_traits = []
        
        for trait in traits:
            trait_lower = trait.lower()
            if any(kw in trait_lower for kw in visual_keywords):
                visual_traits.append(trait)
            else:
                personality_traits.append(trait)
        
        converted.append({
            **char,
            "visual": {
                "appearance": visual_traits[:3],
                "attire": [],
                "age_group": None,
                "gender": None
            },
            "personality": {
                "core_traits": personality_traits[:5],
                "flaws": [],
                "values": []
            },
            "relationships": char.get("relationships", []),
            "current_mood": char.get("current_mood")
        })
    
    return converted


async def character_extraction_node(state: dict) -> dict:
    """Character Extraction Agent node function - with Structured Output.
    
    Uses with_structured_output() for guaranteed schema compliance.
    No manual JSON parsing required.
    """
    # Get LLM with structured output bound to schema
    structured_llm = get_structured_llm(CharacterExtractionResult)
    
    conflicts = state.get("consistency_report", {}).get("conflicts", [])
    retry_count = state.get("retry_count", 0)
    previous_chars = state.get("extracted_characters", [])
    
    is_re_extraction = retry_count > 0 and conflicts and previous_chars
    
    try:
        if is_re_extraction:
            print(f"[CHARACTER] Re-extracting with {len(conflicts)} conflicts as feedback")
            previous_production = convert_legacy_to_production(previous_chars)
            
            chain = CHARACTER_RE_EXTRACTION_PROMPT | structured_llm
            result: CharacterExtractionResult = await chain.ainvoke({
                "story_text": state["content"],
                "conflicts": str(conflicts),
                "previous_extraction": str(previous_production)
            })
        else:
            chain = CHARACTER_EXTRACTION_PROMPT | structured_llm
            result: CharacterExtractionResult = await chain.ainvoke({
                "story_text": state["content"]
            })
        
        # Result is already a CharacterExtractionResult Pydantic object
        characters = [c.model_dump() for c in result.characters]
        
        # Ensure production format
        characters = convert_legacy_to_production(characters)
        
        return {
            "extracted_characters": characters,
            "messages": [
                {"role": "character_agent", 
                 "content": f"{'Re-' if is_re_extraction else ''}Extracted {len(characters)} characters (Structured Output)"}
            ]
        }
    except Exception as e:
        print(f"[CHARACTER] Extraction failed: {e}")
        return {
            "extracted_characters": previous_chars or [],
            "errors": [f"Character extraction failed: {str(e)}"],
            "partial_failure": True
        }
