"""Character Extraction Agent - Level 1 (Production Level).

Extracts character information from story text with:
- Separated visual/personality traits (for image generation)
- Explicit relationships (for Neo4j graph)
- Scene-aware emotional state (for TTS/expression)
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_standard_llm


# Production-level extraction prompt with structured output
CHARACTER_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert story analyst. Extract ALL characters from the given text with PRODUCTION-LEVEL detail.

=== OUTPUT STRUCTURE ===
For each character, provide:

1. **Basic Info**
   - name: Character's name
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

Return ONLY valid JSON:
{{
  "characters": [
    {{
      "name": "...",
      "role": "protagonist",
      "status": "alive",
      "visual": {{
        "appearance": ["..."],
        "attire": ["..."],
        "age_group": "adult",
        "gender": "male"
      }},
      "personality": {{
        "core_traits": ["brave", "loyal"],
        "flaws": ["impulsive"],
        "values": ["justice"]
      }},
      "relationships": [
        {{"target": "OtherChar", "type": "ENEMY", "history": "former_friend", "strength": 8}}
      ],
      "current_mood": {{
        "emotion": "tense",
        "intensity": 7,
        "trigger": "confronting former friend"
      }}
    }}
  ]
}}"""),
    ("human", """Story text to analyze:
{story_text}

Extract all characters with full production-level detail:""")
])


# Re-extraction prompt with STRONG trait preservation
CHARACTER_RE_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert story analyst. Re-extract characters with STRICT TRAIT PRESERVATION.

PREVIOUS CONFLICTS DETECTED:
{conflicts}

=== ⚠️ CRITICAL: INFORMATION PRESERVATION RULES ===

**RULE 1: PRESERVE ALL VALID DATA**
- Copy ALL visual traits from previous extraction that are NOT in conflict
- Copy ALL personality traits from previous extraction that are NOT in conflict
- Copy ALL relationships from previous extraction that are NOT in conflict
- Only MODIFY the specific conflicting element, DO NOT remove unrelated data

**RULE 2: APPEND, DON'T REPLACE**
- When fixing conflicts, ADD corrected information alongside preserved data
- Example: If "cold" and "skilled" were valid, keep them when fixing "betrayed" → "betrayer"
- Result: ["cold", "skilled", "betrayer"] NOT just ["betrayer"]

**RULE 3: RELATIONSHIP STRUCTURE**
- Relationships belong in the "relationships" array, NOT in personality traits
- "former friend" is a relationship history, NOT a personality trait
- Structure: {{"target": "서진", "type": "ENEMY", "history": "former_friend", "strength": 8}}

**RULE 4: VISUAL vs PERSONALITY SEPARATION**
- Visual (for image AI): appearance, clothing, equipment, physical features
- Personality (for LLM persona): character traits, behaviors, motivations
- Keep them strictly separated

=== MERGE STRATEGY EXAMPLE ===
Previous:
  personality.core_traits: ["cold", "skilled", "betrayed"]  // "betrayed" is wrong
  
Conflict: "betrayed" should be "betrayer" (he betrayed, not was betrayed)

Correct Result:
  personality.core_traits: ["cold", "skilled", "betrayer"]  // Keep cold, skilled, fix betrayed
  relationships: [{{"target": "마을", "type": "BETRAYER", "strength": 9}}]  // Add as relationship too

WRONG Result:
  personality.core_traits: ["former friend"]  // ❌ Lost "cold" and "skilled"!

=== OUTPUT STRUCTURE ===
{{
  "characters": [
    {{
      "name": "...",
      "role": "...",
      "status": "alive",
      "visual": {{
        "appearance": ["PRESERVE previous + add new"],
        "attire": ["PRESERVE previous + add new"],
        "age_group": "...",
        "gender": "..."
      }},
      "personality": {{
        "core_traits": ["PRESERVE previous valid traits + fix conflicts"],
        "flaws": ["PRESERVE previous"],
        "values": ["PRESERVE previous"]
      }},
      "relationships": [
        {{"target": "...", "type": "ENEMY/FRIEND/etc", "history": "former_friend if applicable", "strength": 1-10}}
      ],
      "current_mood": {{
        "emotion": "...",
        "intensity": 1-10,
        "trigger": "..."
      }},
      "trait_changes": "Specific note: Changed X to Y, preserved A, B, C"
    }}
  ]
}}"""),
    ("human", """Original story text:
{story_text}

=== PREVIOUS EXTRACTION (PRESERVE ALL VALID DATA FROM THIS) ===
{previous_extraction}

=== INSTRUCTIONS ===
1. Copy all valid data from previous extraction
2. Only modify the SPECIFIC conflicting elements
3. Do NOT remove any valid traits that weren't flagged as conflicts
4. Document exactly what you preserved and what you changed in trait_changes

Re-extract with MINIMAL CHANGES, preserving all valid previous data:""")
])


def convert_legacy_to_production(characters: list) -> list:
    """Convert legacy flat traits format to production format."""
    converted = []
    for char in characters:
        if isinstance(char.get("visual"), dict) and isinstance(char.get("personality"), dict):
            # Already in production format
            converted.append(char)
            continue
            
        # Convert legacy format
        traits = char.get("traits", [])
        
        # Simple heuristic classification
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
    """Character Extraction Agent node function - Production Level.
    
    Extracts characters with:
    - Separated visual/personality traits
    - Explicit relationships for Neo4j
    - Scene-aware emotional state
    """
    llm = get_standard_llm()
    
    # Check if this is a re-extraction (conflicts exist)
    conflicts = state.get("consistency_report", {}).get("conflicts", [])
    retry_count = state.get("retry_count", 0)
    previous_chars = state.get("extracted_characters", [])
    
    is_re_extraction = retry_count > 0 and conflicts and previous_chars
    
    try:
        if is_re_extraction:
            # Re-extraction with feedback
            print(f"[CHARACTER] Re-extracting with {len(conflicts)} conflicts as feedback")
            
            # Convert previous chars to production format if needed
            previous_production = convert_legacy_to_production(previous_chars)
            
            chain = CHARACTER_RE_EXTRACTION_PROMPT | llm
            response = await chain.ainvoke({
                "story_text": state["content"],
                "conflicts": json.dumps(conflicts, ensure_ascii=False, indent=2),
                "previous_extraction": json.dumps(previous_production, ensure_ascii=False, indent=2)
            })
        else:
            # Standard extraction
            chain = CHARACTER_EXTRACTION_PROMPT | llm
            response = await chain.ainvoke({
                "story_text": state["content"]
            })
        
        # Parse JSON from response
        content = response.content.strip()
        
        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        characters = result.get("characters", [])
        
        # Ensure production format
        characters = convert_legacy_to_production(characters)
        
        return {
            "extracted_characters": characters,
            "messages": [
                {"role": "character_agent", 
                 "content": f"{'Re-' if is_re_extraction else ''}Extracted {len(characters)} characters (Production Level)"}
            ]
        }
    except json.JSONDecodeError as e:
        return {
            "extracted_characters": previous_chars or [],
            "errors": [f"Character JSON parse error: {str(e)}"],
            "messages": [
                {"role": "character_agent", "content": f"Failed to parse response"}
            ]
        }
    except Exception as e:
        return {
            "extracted_characters": previous_chars or [],
            "errors": [f"Character extraction failed: {str(e)}"],
            "partial_failure": True
        }
