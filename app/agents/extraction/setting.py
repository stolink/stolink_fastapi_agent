"""Setting Extractor Agent - Level 1 (Production Level).

Role: "Environment Concept Artist" - Creates empty stage sets before actors arrive.
Key: Focus ONLY on static physical environment - ZERO character actions.

Output is optimized for:
- Neo4j graph nodes (setting_id as node key)
- Image generation AI (static_visual_prompt for background-only prompts)
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_standard_llm


SETTING_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an "Environment Concept Artist" / "3D Environment Artist".
Your job is to build the EMPTY STAGE SET before actors arrive.
You describe ONLY: lighting, weather, terrain, architecture, and textures.

=== CRITICAL: BAD vs GOOD EXAMPLES ===

[Example 1]
Input: "서진이 칼을 들고 어두운 숲 속에 서 있었다."

❌ BAD (FAIL - Contains character action):
  "static_visual_prompt": "Seojin standing in a dark forest holding a sword."
  
✅ GOOD (PASS - Only environment):
  "static_visual_prompt": "Dark ancient forest, dense twisted trees, thick fog on ground, dim moonlight filtering through canopy."

[Example 2]  
Input: "이민호가 나무 뒤에서 비웃으며 나타났다."

❌ BAD:
  "static_visual_prompt": "Behind a tree where Minho appears with a smirk."
  
✅ GOOD:
  "static_visual_prompt": "Large old trees with rough bark texture, deep shadows cast by thick tree trunks."

[Example 3]
Input: "하나가 마을에서 가장 현명한 치료사였다."

❌ BAD:
  "static_visual_prompt": "The village where Hana lives as a healer."
  
✅ GOOD:
  "static_visual_prompt": "Rustic fantasy village, small wooden houses with thatched roofs, cobblestone paths, warm lantern glow."

=== STEP-BY-STEP EXTRACTION PROCESS ===

1. **IDENTIFY** all character names and action verbs in the text
   (e.g., "서진", "이민호", "holding sword", "standing", "appeared")
   
2. **REMOVE** them completely from your mind

3. **FOCUS** on what remains: trees, fog, moon, ground, buildings, weather

4. **DESCRIBE** using ONLY physical nouns and adjectives:
   - Textures (rough bark, smooth stone, wet leaves, mossy rocks)
   - Materials (wood, stone, metal, fabric, leather)
   - Lighting (moonlight, shadows, god rays, rim light)
   - Colors (dark green, pale blue, warm orange, deep black)
   - Weather (foggy, rainy, clear, stormy)

5. **CREATIVELY INFER** (IMPORTANT): 
   If the text description is simple (e.g., just "forest"), ADD plausible visual details:
   - Textures: gnarled roots, rough bark, mossy rocks
   - Lighting effects: god rays, volumetric fog, rim lighting
   - Environmental particles: fireflies, falling leaves, dust motes
   - Atmosphere enhancers: mist, puddles, cobwebs

=== PENALTY WARNING ===
If ANY character name (서진, 이민호, 하나, 박서연) or action verb (holding, standing, fighting, appearing) 
is included in 'static_visual_prompt', the output is INVALID and will be REJECTED.

=== OUTPUT STRUCTURE ===
{{
  "settings": [
    {{
      "setting_id": "loc_forest_01",
      "name": "Dark Forest",
      "location_type": "forest",
      
      // [CRITICAL] Image generation prompt - NO PEOPLE, NO ACTIONS
      "static_visual_prompt": "Dense ancient forest, tall twisted trees with rough dark bark, thick white fog covering the forest floor, pale moonlight filtering weakly through dense leaf canopy, deep shadows between trunks, moss-covered rocks scattered on dead leaves",
      
      // Lighting & Atmosphere Control
      "time_of_day": "night",
      "lighting_description": "dim pale moonlight filtering through dense canopy, low-key lighting",
      "atmosphere_keywords": "ominous, tense, mysterious, foreboding",
      "weather_condition": "foggy",
      
      // Physical Features (static objects only)
      "static_objects": ["ancient twisted trees", "thick ground fog", "moss-covered rocks", "dead leaves on ground"],
      
      // Metadata
      "is_primary_location": true,
      "story_significance": "Site of the confrontation"
    }},
    {{
      "setting_id": "loc_village_01", 
      "name": "The Village",
      "location_type": "village",
      "static_visual_prompt": "Rustic medieval fantasy village, small wooden houses with thatched straw roofs, narrow cobblestone paths, warm orange lantern light glowing from windows",
      "time_of_day": "unknown",
      "lighting_description": "warm ambient lantern light",
      "atmosphere_keywords": "peaceful, homely, rustic",
      "weather_condition": "clear",
      "static_objects": ["wooden houses", "thatched roofs", "cobblestone paths", "lanterns"],
      "is_primary_location": false,
      "story_significance": "Home of the characters, mentioned in backstory"
    }}
  ],
  "world_context": {{
    "era": "medieval fantasy",
    "technology_level": "pre-industrial"
  }}
}}"""),
    ("human", """Text to analyze:
{story_text}

=== YOUR TASK ===
1. Read the text and identify ALL locations (primary AND mentioned)
2. For each location, REMOVE all character references
3. Describe ONLY the static physical environment
4. Output valid JSON with 'static_visual_prompt' containing ZERO character actions

Remember: You are painting an EMPTY background. No people. Only environment.""")
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

PENALTY: If character names or actions remain in 'static_visual_prompt', output is INVALID."""),
    ("human", """Original text:
{story_text}

Previous extraction (contains errors):
{previous_extraction}

Re-extract with corrections. REMOVE all character references:""")
])


async def setting_extraction_node(state: dict) -> dict:
    """Setting Extractor Agent node function - Production Level.
    
    Role: "Environment Concept Artist" - creates empty stage sets
    for Neo4j nodes and image generation prompts.
    
    Key principle: ZERO character actions. ONLY static environment.
    """
    llm = get_standard_llm()
    
    conflicts = state.get("consistency_report", {}).get("conflicts", [])
    retry_count = state.get("retry_count", 0)
    previous_settings = state.get("extracted_settings", [])
    
    is_re_extraction = retry_count > 0 and conflicts and previous_settings
    
    try:
        if is_re_extraction:
            print(f"[SETTING] Re-extracting with {len(conflicts)} conflicts as feedback")
            chain = SETTING_RE_EXTRACTION_PROMPT | llm
            response = await chain.ainvoke({
                "story_text": state["content"],
                "conflicts": json.dumps(conflicts, ensure_ascii=False, indent=2),
                "previous_extraction": json.dumps(previous_settings, ensure_ascii=False, indent=2)
            })
        else:
            chain = SETTING_EXTRACTION_PROMPT | llm
            response = await chain.ainvoke({
                "story_text": state["content"]
            })
        
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        settings = result.get("settings", [])
        world_context = result.get("world_context", {})
        
        # Post-process: Map new field names to schema-compatible names
        for setting in settings:
            # Map static_visual_prompt to visual_background for schema compatibility
            if "static_visual_prompt" in setting and "visual_background" not in setting:
                setting["visual_background"] = setting["static_visual_prompt"]
            if "lighting_description" in setting and "lighting" not in setting:
                setting["lighting"] = setting["lighting_description"]
            if "atmosphere_keywords" in setting and "atmosphere" not in setting:
                setting["atmosphere"] = setting["atmosphere_keywords"]
            if "weather_condition" in setting and "weather" not in setting:
                setting["weather"] = setting["weather_condition"]
            if "static_objects" in setting and "notable_features" not in setting:
                setting["notable_features"] = setting["static_objects"]
            if "is_primary_location" in setting and "is_primary" not in setting:
                setting["is_primary"] = setting["is_primary_location"]
            if "story_significance" in setting and "significance" not in setting:
                setting["significance"] = setting["story_significance"]
        
        return {
            "extracted_settings": settings,
            "world_context": world_context,
            "messages": [
                {"role": "setting_agent", 
                 "content": f"{'Re-' if is_re_extraction else ''}Extracted {len(settings)} settings (Production Level)"}
            ]
        }
    except json.JSONDecodeError as e:
        return {
            "extracted_settings": previous_settings or [],
            "errors": [f"Setting JSON parse error: {str(e)}"],
            "messages": [
                {"role": "setting_agent", "content": "Failed to parse response"}
            ]
        }
    except Exception as e:
        return {
            "extracted_settings": previous_settings or [],
            "errors": [f"Setting extraction failed: {str(e)}"],
            "partial_failure": True
        }
