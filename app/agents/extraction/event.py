"""Event Extraction Agent - with Structured Output.

Role: "Scene Director" - Manages WHO, WHERE, WHAT HAPPENED.
Key: Focus on REFERENCES (to characters and settings) and VISUAL COMPOSITION.

Uses with_structured_output() for:
- Guaranteed valid JSON
- Pydantic schema validation
- No manual parsing required
"""
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_structured_llm
from app.schemas.events import EventExtractionResult


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
   - participants: Exact character names → Creates (Event)-[:INVOLVES]->(Character) edges
   - location_ref: Setting name → Creates (Event)-[:HAPPENS_AT]->(Location) edge
   - prev_event_id: Previous event ID → Creates timeline

2. **Image Generation Prompt**:
   - visual_scene: Describe ONLY the composition and action
     * INCLUDE: poses, positions, expressions, gestures, camera angle
     * EXCLUDE: background, environment, weather (that comes from Setting Agent)

3. **Narrative Context**:
   - narrative_summary: One-sentence summary
   - description: Detailed description (REQUIRED)
   - importance: 1-10 (use for filtering which scenes to illustrate)

=== FIELD REQUIREMENTS ===
For each event, you MUST provide:
- event_id: Unique ID like "E001", "E002"
- event_type: action, dialogue, revelation, flashback, foreshadowing, confrontation, transition
- narrative_summary: Brief one-line summary
- description: Detailed event description (REQUIRED!)
- participants: List of exact character names
- location_ref: Short setting name
- prev_event_id: Previous event ID or null
- visual_scene: Character action/pose description (NO BACKGROUND!)
- camera_angle: medium shot, close-up, wide shot, low angle, bird's eye, etc.
- importance: 1-10
- is_foreshadowing: true/false

=== PENALTY WARNING ===
If visual_scene contains background descriptions like "dark forest", "trees", "fog", "moonlight",
it will be REJECTED because that's Setting Agent's job."""),
    ("human", """Text to analyze:
{story_text}

=== STRICT CONSTRAINT: USE ONLY THESE NAMES ===

Available Characters (from Character Agent) - MUST use EXACT names:
{available_characters}

Available Inventory (VISUAL CONTEXT):
{available_inventory}

Available Locations (from Setting Agent) - MUST use EXACT names:
{available_settings}

RULES:
1. participants: ONLY use names from "Available Characters" list above
2. location_ref: ONLY use names from "Available Locations" list above
3. visual_scene: Action and composition ONLY - NO background descriptions
   - TIP: Use "Available Inventory" to describe held items precisely (e.g., "Silver Sword" instead of "sword")
4. description: MUST provide detailed description for each event

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
6. Ensure ALL events have a description field
7. Maintain timeline integrity (prev_event_id chain)

=== PENALTY ===
If visual_scene contains "forest", "trees", "moon", "fog" - it will be REJECTED."""),
    ("human", """Original text:
{story_text}

Available Characters: {available_characters}
Available Inventory: {available_inventory}
Available Locations: {available_settings}

Previous extraction (contains errors):
{previous_extraction}

Re-extract with corrections.""")
])


async def event_extraction_node(state: dict) -> dict:
    """Event Extraction Agent node function - with Structured Output.
    
    Uses with_structured_output() for guaranteed schema compliance.
    No manual JSON parsing required.
    """
    # Get LLM with structured output bound to schema
    structured_llm = get_structured_llm(EventExtractionResult)
    
    conflicts = state.get("consistency_report", {}).get("conflicts", [])
    retry_count = state.get("retry_count", 0)
    previous_events = state.get("extracted_events", [])
    
    # Get available characters and settings for reference matching
    # Support both legacy (c["name"]) and FullCharacter (c["profile"]["name"]) formats
    characters = state.get("extracted_characters", [])
    settings = state.get("extracted_settings", [])
    
    available_characters = []
    available_inventory = [] # Format: "Name: [Item1, Item2]"
    
    for c in characters:
        # Extract Name
        name = c.get("name") or (c.get("profile", {}) or {}).get("name")
        if name:
            available_characters.append(name)
            
            # Extract Inventory if available
            # Check various paths: c['inventory'], c['char_inventory'], or flat fields
            inv = c.get("inventory", {}) or c.get("char_inventory", {})
            items = []
            if isinstance(inv, dict):
                # Try 'equipped_items' or 'bag_items'
                items.extend(inv.get("equipped_items", []))
                items.extend(inv.get("bag_items", []))
                # Or generic 'items' list
                if not items and "items" in inv:
                    items = inv["items"]
            
            if items:
                # Cleanup simple strings
                clean_items = [i if isinstance(i, str) else str(i) for i in items]
                available_inventory.append(f"{name}: [{', '.join(clean_items)}]")
    
    inv_str = "\n".join(available_inventory) if available_inventory else "None"
    
    available_settings = [s.get("location_name") or s.get("name", "") for s in settings if s.get("location_name") or s.get("name")]
    
    print(f"[EVENT] Available characters: {available_characters}")
    print(f"[EVENT] Available inventory: {inv_str}")
    print(f"[EVENT] Available settings: {available_settings}")
    
    is_re_extraction = retry_count > 0 and conflicts and previous_events
    
    try:
        if is_re_extraction:
            print(f"[EVENT] Re-extracting with {len(conflicts)} conflicts as feedback")
            chain = EVENT_RE_EXTRACTION_PROMPT | structured_llm
            result: EventExtractionResult = await chain.ainvoke({
                "story_text": state["content"],
                "available_characters": str(available_characters),
                "available_inventory": inv_str,
                "available_settings": str(available_settings),
                "conflicts": str(conflicts),
                "previous_extraction": str(previous_events)
            })
        else:
            chain = EVENT_EXTRACTION_PROMPT | structured_llm
            result: EventExtractionResult = await chain.ainvoke({
                "story_text": state["content"],
                "available_characters": str(available_characters),
                "available_inventory": inv_str,
                "available_settings": str(available_settings)
            })
        
        # Result is already an EventExtractionResult Pydantic object
        events = [e.model_dump() for e in result.events]
        
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
                 "content": f"{'Re-' if is_re_extraction else ''}Extracted {len(events)} events (Structured Output)"}
            ]
        }
    except Exception as e:
        print(f"[EVENT] Extraction failed: {e}")
        return {
            "extracted_events": previous_events or [],
            "errors": [f"Event extraction failed: {str(e)}"],
            "partial_failure": True
        }
