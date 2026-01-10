"""Setting Extractor Agent - with Structured Output.

Role: "Environment Concept Artist" - Creates empty stage sets before actors arrive.
Key: Focus ONLY on static physical environment - ZERO character actions.

Uses with_structured_output() for:
- Guaranteed valid JSON
- Pydantic schema validation
- No manual parsing required
"""
import re  # Added for regex operations
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_structured_llm, safe_ainvoke
from app.schemas.settings import SettingExtractionResult


SETTING_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an "Environment Concept Artist" / "3D Environment Artist".
Your job is to build the EMPTY STAGE SET before actors arrive.
You describe ONLY: lighting, weather, terrain, architecture, and textures.

=== CRITICAL: BAD vs GOOD EXAMPLES ===

[Example 1]
Input: "서진이 칼을 들고 어두운 숲 속에 서 있었다."

❌ BAD (FAIL - Contains character action):
  "visual_background": "Seojin standing in a dark forest holding a sword."
  
✅ GOOD (PASS - Only environment):
  "visual_background": "Dark ancient forest, dense twisted trees, thick fog on ground, dim moonlight filtering through canopy."

[Example 2]  
Input: "이민호가 나무 뒤에서 비웃으며 나타났다."

❌ BAD:
  "visual_background": "Behind a tree where Minho appears with a smirk."
  
✅ GOOD:
  "visual_background": "Large old trees with rough bark texture, deep shadows cast by thick tree trunks."

=== STEP-BY-STEP EXTRACTION PROCESS ===

1. **IDENTIFY** the physical location (forest, room, street)
2. **DESCRIBE** the scene as if it were an empty stage set
3. **FOCUS** on what remains: trees, fog, moon, ground, buildings, weather
4. **DESCRIBE** using ONLY physical nouns and adjectives:
   - Textures (rough bark, smooth stone, wet leaves, mossy rocks)
   - Materials (wood, stone, metal, fabric, leather)
   - Lighting (moonlight, shadows, god rays, rim light)
   - Colors (dark green, pale blue, warm orange, deep black)
   - Weather (foggy, rainy, clear, stormy)

5. **CREATIVELY INFER** (IMPORTANT): 
   If the text description is simple (e.g., just "forest"), ADD plausible visual details.

=== FIELD REQUIREMENTS ===
For each setting, you MUST provide:
- setting_id: Unique ID like "loc_forest_01"
- name: Short location name

- location_type: One of: indoor, outdoor, castle, city, village, forest, mountain, sea, dungeon, road, other
- visual_background: Detailed environment description (NO characters!)
- atmosphere: Mood keywords
- time_of_day: dawn, morning, noon, afternoon, evening, dusk, night, unknown
- lighting: Lighting description
- weather: Weather condition
- description: Brief narrative description  
- notable_features: List of key features
- significance: Story importance
- is_primary: true if action happens here

=== LANGUAGE INSTRUCTION ===
**CRITICAL**: Respond in the SAME language as the input text.
- If the input is in Korean (한글), ALL text fields (visual_background, descriptions, atmosphere, etc.) MUST be in Korean.
- If the input is in English, ALL text fields MUST be in English.
- Keep technical field names (like "setting_id", "location_type") in English, but content values should match the input language.

=== PENALTY WARNING -> GUIDELINE ===
Focus purely on the visual environment. If character names or actions are mentioned, rephrase to focus on the effect they have on the environment (e.g., "footsteps on snow" -> "snowy path with footprints").

=== LANGUAGE CONSISTENCY RULE ===
**CRITICAL**: Output ALL text content in the SAME LANGUAGE as the input.
- If the input text is in Korean (한국어), ALL descriptions MUST be in Korean.
- If the input text is in English, all descriptions must be in English.
- Never mix languages.

Your goal is valid JSON output of the environment description."""),
    ("human", """Text to analyze:
{story_text}

Extract all settings with full detail. Focus on the physical world.""")
])


SETTING_RE_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an Environment Concept Artist. Re-extract settings with corrections.

PREVIOUS CONFLICTS:
{conflicts}

=== CORRECTION PROCESS ===
1. Review the conflicts
2. REMOVE any character names or actions from descriptions
3. ADD more physical details: textures, materials, colors
4. Ensure time_of_day matches text clues (moonlight = night)

94. NOTE: Character names in visual_background should be avoided where possible, but context is improved if you focus on the static environment."""),
    ("human", """Original text:
{story_text}

Previous extraction (contains errors):
{previous_extraction}

Re-extract with corrections. Focus on environment detail.""")
])


async def setting_extraction_node(state: dict) -> dict:
    """Setting Extractor Agent node function - with Structured Output.
    
    Uses with_structured_output() for guaranteed schema compliance.
    No manual JSON parsing required.
    """
    print("[SETTING] Starting setting extraction...")
    
    # Get LLM with structured output bound to schema
    structured_llm = get_structured_llm(SettingExtractionResult, tier="advanced")
    
    conflicts = state.get("consistency_report", {}).get("conflicts", [])
    retry_count = state.get("retry_count", 0)
    previous_settings = state.get("extracted_settings", [])
    
    is_re_extraction = retry_count > 0 and conflicts and previous_settings
    
    try:
        if is_re_extraction:
            print(f"[SETTING] Re-extracting with {len(conflicts)} conflicts as feedback")
            chain = SETTING_RE_EXTRACTION_PROMPT | structured_llm
            result: SettingExtractionResult = await safe_ainvoke(chain, {
                "story_text": state["content"],
                "conflicts": str(conflicts),
                "previous_extraction": str(previous_settings)
            })
        else:
            print(f"[SETTING] First extraction, content length: {len(state.get('content', ''))}")
            chain = SETTING_EXTRACTION_PROMPT | structured_llm
            result: SettingExtractionResult = await safe_ainvoke(chain, {
                "story_text": state["content"]
            })
        
        # Result is already a SettingExtractionResult Pydantic object
        # Convert to dict for state storage
        settings = [s.model_dump() for s in result.settings]
        
        # No need to set location_name (removed attribute)
        
        print(f"[SETTING] Successfully extracted {len(settings)} settings")
        
        # If LLM returned empty, try fallback
        if not settings:
            print(f"[SETTING] LLM returned empty, trying fallback...")
            fallback_settings = create_fallback_settings(state.get("content", ""))
            if fallback_settings:
                print(f"[SETTING] Fallback created {len(fallback_settings)} settings")
                return {
                    "extracted_settings": fallback_settings,
                    "world_context": {
                        "world_name": result.world_name or "Unknown",
                        "era": result.era,
                        "technology_level": result.technology_level,
                    },
                    "messages": [
                        {"role": "setting_agent", 
                         "content": f"Fallback: Created {len(fallback_settings)} settings from keywords"}
                    ]
                }
        
        return {
            "extracted_settings": settings,
            "world_context": {
                "world_name": result.world_name,
                "era": result.era,
                "technology_level": result.technology_level,
            },
            "messages": [
                {"role": "setting_agent", 
                 "content": f"{'Re-' if is_re_extraction else ''}Extracted {len(settings)} settings (Structured Output)"}
            ]
        }
    except Exception as e:
        print(f"[SETTING] Extraction failed with error: {type(e).__name__}: {e}")
        
        # Create fallback settings based on common patterns in story
        fallback_settings = create_fallback_settings(state.get("content", ""))
        
        if fallback_settings:
            print(f"[SETTING] Created {len(fallback_settings)} fallback settings")
            return {
                "extracted_settings": fallback_settings,
                "messages": [
                    {"role": "setting_agent", 
                     "content": f"Fallback: Created {len(fallback_settings)} settings from keywords"}
                ]
            }
        
        return {
            "extracted_settings": previous_settings or [],
            "errors": [f"Setting extraction failed: {str(e)}"],
            "partial_failure": True
        }


def create_fallback_settings(content: str) -> list[dict]:
    """Create generic fallback settings if extraction fails."""
    settings = []
    
    # Generic location matching (Genre Agnostic)
    location_patterns = [
        # City/Urban
        (r"(도시|시내|거리|city|street|town)", "도심", "city", "Bustling city streets with diverse architecture and ambient lighting"),
        (r"(빈민가|슬럼|slum|alley)", "뒷골목", "city", "Narrow, shadowed alleyways with worn textures and dim lighting"),
        
        # Nature/Forest
        (r"(숲|산|나무|forest|mountain|woods)", "숲", "forest", "Dense forest with organic textures, natural lighting filtering through canopy"),
        (r"(바다|해변|물가|sea|beach|coast)", "해변", "sea", "Open water with rhythmic waves, horizon line, and natural atmospheric lighting"),
        
        # Indoor
        (r"(방|집|실내|room|house|indoor)", "실내", "indoor", "Enclosed interior space with functional furniture and controlled lighting"),
        (r"(가게|상점|store|shop)", "상점", "indoor", "Commercial space with display counters and warm interior lighting"),
        
        # Abstract/Other
        (r"(어둠|공간|void|darkness)", "알 수 없는 공간", "other", "Abstract space with minimal visual features and mysterious atmosphere")
    ]
    
    found_locations = set()
    
    for pattern, name, loc_type, visual in location_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            if name in found_locations:
                continue
                
            found_locations.add(name)
            
            # Create neutral setting
            settings.append({
                "setting_id": f"loc_fallback_{len(settings)+1}",
                "name": name,

                "location_type": loc_type,
                "visual_background": visual,
                "atmosphere": "mysterious" if "어둠" in content else "neutral",
                "time_of_day": "unknown",
                "lighting": "dim" if "어둠" in content else "natural",
                "weather": "rainy" if "비" in content else None,
                "description": f"Auto-generated generic setting for {name}",
                "notable_features": [],
                "significance": "Background location",
                "is_primary": False
            })
            
    # Default if nothing found
    if not settings:
        settings.append({
            "setting_id": "loc_default_01",
            "name": "Unknown Location",

            "location_type": "other",
            "visual_background": "Generic environment with neutral lighting and standard textures",
            "atmosphere": "neutral",
            "time_of_day": "unknown",
            "lighting": "neutral",
            "weather": None,
            "description": "Default fallback location",
            "notable_features": [],
            "significance": "Default setting",
            "is_primary": True
        })
        
    return settings
