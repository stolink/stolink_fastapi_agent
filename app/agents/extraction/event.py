"""Event Extraction Agent - Level 1 (Production Level).

Role: "Scene Director" - Manages WHO, WHERE, WHAT HAPPENED.
Key: Focus on REFERENCES (to characters and settings) and VISUAL COMPOSITION.

Output is optimized for:
- Neo4j graph edges (participants → INVOLVES, location_ref → HAPPENS_AT, prev_event_id → NEXT)
- Image generation AI (visual_scene for action/composition prompts - NO BACKGROUND)
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_standard_llm


EVENT_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a "Scene Director" / "Storyboard Artist".
Your job is to break down the story into SCENES and describe the COMPOSITION for each.

=== CRITICAL: BAD vs GOOD EXAMPLES ===

[Example 1: visual_scene should NOT include background]
Input: "서진이 어두운 숲에서 검을 쥐고 있었다."

❌ BAD (FAIL - Contains background description):
  "visual_scene": "A man holding a sword in a dark forest with tall trees and fog."
  
✅ GOOD (PASS - Only action and composition):
  "visual_scene": "A tall man with dark hair gripping a sword, tense posture, alert expression, medium shot"

[Example 2: Use participant names as EXACT references]
❌ BAD:
  "participants": ["the protagonist", "the antagonist"]
  
✅ GOOD:
  "participants": ["서진", "이민호"]  // Exact names for Neo4j matching

[Example 3: location_ref should match Setting Agent's name]
❌ BAD:
  "location_ref": "A dark forest where trees are twisted"
  
✅ GOOD:
  "location_ref": "Dark Forest"  // Short name, matches Setting Agent

=== YOUR TASK ===
Extract events with THREE purposes:

1. **Neo4j Graph Edges**:
   - participants: ["서진", "이민호"] → Creates (Event)-[:INVOLVES]->(Character) edges
   - location_ref: "Dark Forest" → Creates (Event)-[:HAPPENS_AT]->(Location) edge
   - prev_event_id: "E001" → Creates (E001)-[:NEXT]->(E002) edge

2. **Image Generation Prompt**:
   - visual_scene: Describe ONLY the composition and action
     * INCLUDE: poses, positions, expressions, gestures, camera angle
     * EXCLUDE: background, environment, weather (that comes from Setting Agent)
     * Think: "What do the CHARACTERS look like in this moment?"

3. **Narrative Context**:
   - narrative_summary: One-sentence Korean summary
   - importance: 1-10 (use for filtering which scenes to illustrate)

=== OUTPUT STRUCTURE ===
{{
  "events": [
    {{
      "event_id": "E001",
      "event_type": "action",
      "narrative_summary": "서진이 검을 쥐고 숲에서 대기 중",
      
      // Neo4j Edges
      "participants": ["서진"],
      "location_ref": "Dark Forest",
      "prev_event_id": null,
      
      // Image Generation (NO BACKGROUND!)
      "visual_scene": "A tall man with dark hair gripping a sword, tense posture, standing alert, medium shot",
      "camera_angle": "medium shot",
      
      "importance": 5,
      "is_foreshadowing": false
    }},
    {{
      "event_id": "E002",
      "event_type": "dialogue",
      "narrative_summary": "하나가 불안하게 질문함",
      "participants": ["하나", "서진"],
      "location_ref": "Dark Forest",
      "prev_event_id": "E001",
      "visual_scene": "A woman in white healer robes looking worried, speaking to a swordsman, eye-level shot",
      "camera_angle": "eye-level",
      "importance": 4,
      "is_foreshadowing": false
    }},
    {{
      "event_id": "E003",
      "event_type": "appearance",
      "narrative_summary": "이민호가 그림자 속에서 등장",
      "participants": ["이민호"],
      "location_ref": "Dark Forest",
      "prev_event_id": "E002",
      "visual_scene": "A man in black armor emerging from shadows, cold eyes, ominous presence, low angle dramatic shot",
      "camera_angle": "low angle",
      "importance": 8,
      "is_foreshadowing": false
    }},
    {{
      "event_id": "E004",
      "event_type": "confrontation",
      "narrative_summary": "서진이 이민호에게 배신 이유를 추궁",
      "participants": ["서진", "이민호"],
      "location_ref": "Dark Forest",
      "prev_event_id": "E003",
      "visual_scene": "Two men facing each other with swords drawn, intense eye contact, confrontational stance, low angle cinematic shot",
      "camera_angle": "low angle",
      "importance": 9,
      "is_foreshadowing": false
    }}
  ]
}}

=== PENALTY WARNING ===
If visual_scene contains background descriptions like "dark forest", "trees", "fog", "moonlight",
it will be REJECTED because that's Setting Agent's job."""),
    ("human", """Text to analyze:
{story_text}

=== STRICT CONSTRAINT: USE ONLY THESE NAMES ===

Available Characters (from Character Agent) - MUST use EXACT names:
{available_characters}

Available Locations (from Setting Agent) - MUST use EXACT names:
{available_settings}

RULES:
1. participants: ONLY use names from "Available Characters" list above
2. location_ref: ONLY use names from "Available Locations" list above
3. visual_scene: Action and composition ONLY - NO background descriptions

If a character or location is not in the list, use the closest match or exclude it.""")
])


EVENT_RE_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a Scene Director. Re-extract events with corrections based on feedback.

PREVIOUS CONFLICTS:
{conflicts}

=== CORRECTION RULES ===
1. Keep all valid events from previous extraction
2. Fix specific issues mentioned in conflicts
3. REMOVE any background descriptions from visual_scene
4. Ensure participants match exact character names
5. Ensure location_ref matches exact setting names
6. Maintain timeline integrity (prev_event_id chain)

=== PENALTY ===
If visual_scene contains "forest", "trees", "moon", "fog" - it will be REJECTED."""),
    ("human", """Original text:
{story_text}

Available Characters: {available_characters}
Available Locations: {available_settings}

Previous extraction (contains errors):
{previous_extraction}

Re-extract with corrections:""")
])


async def event_extraction_node(state: dict) -> dict:
    """Event Extraction Agent node function - Production Level.
    
    Role: "Scene Director" - extracts events with graph connections
    for Neo4j edges and image generation scene prompts.
    
    Key principle: 
    - visual_scene = action/composition ONLY
    - Background comes from Setting Agent
    - Use EXACT character/location names for graph matching
    """
    llm = get_standard_llm()
    
    conflicts = state.get("consistency_report", {}).get("conflicts", [])
    retry_count = state.get("retry_count", 0)
    previous_events = state.get("extracted_events", [])
    
    # Get available characters and settings for reference matching
    characters = state.get("extracted_characters", [])
    settings = state.get("extracted_settings", [])
    
    available_characters = [c.get("name", "") for c in characters if c.get("name")]
    available_settings = [s.get("name", "") for s in settings if s.get("name")]
    
    print(f"[EVENT] Available characters: {available_characters}")
    print(f"[EVENT] Available settings: {available_settings}")
    
    is_re_extraction = retry_count > 0 and conflicts and previous_events
    
    try:
        if is_re_extraction:
            print(f"[EVENT] Re-extracting with {len(conflicts)} conflicts as feedback")
            chain = EVENT_RE_EXTRACTION_PROMPT | llm
            response = await chain.ainvoke({
                "story_text": state["content"],
                "available_characters": json.dumps(available_characters, ensure_ascii=False),
                "available_settings": json.dumps(available_settings, ensure_ascii=False),
                "conflicts": json.dumps(conflicts, ensure_ascii=False, indent=2),
                "previous_extraction": json.dumps(previous_events, ensure_ascii=False, indent=2)
            })
        else:
            chain = EVENT_EXTRACTION_PROMPT | llm
            response = await chain.ainvoke({
                "story_text": state["content"],
                "available_characters": json.dumps(available_characters, ensure_ascii=False),
                "available_settings": json.dumps(available_settings, ensure_ascii=False)
            })
        
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        events = result.get("events", [])
        
        # Validate and log
        for event in events:
            participants = event.get("participants", [])
            location = event.get("location_ref", "")
            # Log any mismatches for debugging
            for p in participants:
                if p not in available_characters and available_characters:
                    print(f"[EVENT] Warning: participant '{p}' not in available_characters")
            if location and location not in available_settings and available_settings:
                print(f"[EVENT] Warning: location_ref '{location}' not in available_settings")
        
        return {
            "extracted_events": events,
            "messages": [
                {"role": "event_agent", 
                 "content": f"{'Re-' if is_re_extraction else ''}Extracted {len(events)} events (Production Level)"}
            ]
        }
    except json.JSONDecodeError as e:
        return {
            "extracted_events": previous_events or [],
            "errors": [f"Event JSON parse error: {str(e)}"],
            "messages": [
                {"role": "event_agent", "content": "Failed to parse response"}
            ]
        }
    except Exception as e:
        return {
            "extracted_events": previous_events or [],
            "errors": [f"Event extraction failed: {str(e)}"],
            "partial_failure": True
        }
