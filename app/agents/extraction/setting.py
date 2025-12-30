"""Setting Extractor Agent - with Structured Output.

Role: "Environment Concept Artist" - Creates empty stage sets before actors arrive.
Key: Focus ONLY on static physical environment - ZERO character actions.

Uses with_structured_output() for:
- Guaranteed valid JSON
- Pydantic schema validation
- No manual parsing required
"""
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_structured_llm
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
- location_name: Same as name (for display)
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

=== PENALTY WARNING -> GUIDELINE ===
Focus purely on the visual environment. If character names or actions are mentioned, rephrase to focus on the effect they have on the environment (e.g., "footsteps on snow" -> "snowy path with footprints").

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
    # Get LLM with structured output bound to schema
    structured_llm = get_structured_llm(SettingExtractionResult, tier="standard")
    
    conflicts = state.get("consistency_report", {}).get("conflicts", [])
    retry_count = state.get("retry_count", 0)
    previous_settings = state.get("extracted_settings", [])
    
    is_re_extraction = retry_count > 0 and conflicts and previous_settings
    
    try:
        if is_re_extraction:
            print(f"[SETTING] Re-extracting with {len(conflicts)} conflicts as feedback")
            chain = SETTING_RE_EXTRACTION_PROMPT | structured_llm
            result: SettingExtractionResult = await chain.ainvoke({
                "story_text": state["content"],
                "conflicts": str(conflicts),
                "previous_extraction": str(previous_settings)
            })
        else:
            chain = SETTING_EXTRACTION_PROMPT | structured_llm
            result: SettingExtractionResult = await chain.ainvoke({
                "story_text": state["content"]
            })
        
        # Result is already a SettingExtractionResult Pydantic object
        # Convert to dict for state storage
        settings = [s.model_dump() for s in result.settings]
        
        # Ensure location_name is set (fallback to name if missing)
        for setting in settings:
            if not setting.get("location_name") and setting.get("name"):
                setting["location_name"] = setting["name"]
        
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
        print(f"[SETTING] Extraction failed: {e}")
        return {
            "extracted_settings": previous_settings or [],
            "errors": [f"Setting extraction failed: {str(e)}"],
            "partial_failure": True
        }
