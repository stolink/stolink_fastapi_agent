"""Event Extraction Agent - Level 1 (Production Level).

Role: "Director" - Manages who, where, what happened.
Key: Focus on REFERENCES (to characters and settings) and VISUAL SCENE description.

Output is optimized for:
- Neo4j graph edges (participants → INVOLVES, location_ref → HAPPENS_AT, prev_event_id → NEXT)
- Image generation AI (visual_scene for action/composition prompts)
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_standard_llm


EVENT_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a "Director" - an expert at analyzing story events and their connections.

Your role: Extract EVENTS that will be used for:
1. Neo4j graph database (as Event nodes with edges to Characters and Locations)
2. Image generation AI (as scene composition prompts)

=== KEY PRINCIPLES ===
- **Reference, don't duplicate**: Use character NAMES and location NAMES as references
- **Focus on action**: Describe WHAT HAPPENS, not background details
- **Visual scene**: Describe the COMPOSITION for image generation

=== OUTPUT STRUCTURE ===
For each event, provide:

1. **Event Identity**
   - event_id: Unique ID (E001, E002...)
   - event_type: "action", "dialogue", "revelation", "confrontation", "flashback"
   - narrative_summary: Brief summary of what happens

2. **Graph Connections (for Neo4j Edges)**
   - participants: List of CHARACTER NAMES involved (creates INVOLVES edges)
   - location_ref: LOCATION NAME where event happens (creates HAPPENS_AT edge)
   - prev_event_id: Previous event ID for timeline (creates NEXT edge)

3. **Visual Scene (for Image Generation)**
   - visual_scene: Describe the COMPOSITION and ACTION
     * Focus on: poses, positions, expressions, camera angle
     * Example: "Two men facing each other with swords drawn, intense eye contact, low angle shot"
     * DO NOT describe background (that comes from Setting)
   - camera_angle: Suggested angle ("low angle", "bird's eye", "close-up", "wide shot")

4. **Metadata**
   - importance: 1-10 scale
   - is_foreshadowing: true/false

Return ONLY valid JSON:
{{
  "events": [
    {{
      "event_id": "E001",
      "event_type": "action",
      "narrative_summary": "서진이 숲에서 검을 들고 대기 중",
      "participants": ["서진"],
      "location_ref": "Dark Forest",
      "prev_event_id": null,
      "visual_scene": "A tall man with dark hair holding a sword, standing alert, tense posture",
      "camera_angle": "medium shot",
      "importance": 5,
      "is_foreshadowing": false
    }},
    {{
      "event_id": "E002",
      "event_type": "confrontation",
      "narrative_summary": "이민호가 배신의 이유를 묻는 대치",
      "participants": ["서진", "이민호"],
      "location_ref": "Dark Forest",
      "prev_event_id": "E001",
      "visual_scene": "Two men facing each other with swords drawn, intense eye contact, low angle dramatic shot",
      "camera_angle": "low angle",
      "importance": 9,
      "is_foreshadowing": false
    }}
  ]
}}"""),
    ("human", """Text to analyze:
{story_text}

Extract all events with graph connections and visual scenes:""")
])


EVENT_RE_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an event analysis expert. Re-extract events with corrections based on feedback.

PREVIOUS CONFLICTS:
{conflicts}

=== PRESERVATION RULES ===
1. Keep all valid events from previous extraction
2. Only modify the specific conflicting elements
3. Ensure proper event_type classification
4. Maintain timeline integrity (prev_event_id chain)

=== IMPORTANT ===
- Preserve participant lists
- Preserve location_ref references
- Fix only what is flagged as conflict

Return the same JSON structure as initial extraction."""),
    ("human", """Original text:
{story_text}

Previous extraction:
{previous_extraction}

Re-extract with corrections, maintaining valid data:""")
])


async def event_extraction_node(state: dict) -> dict:
    """Event Extraction Agent node function - Production Level.
    
    Role: "Director" - extracts events with graph connections
    for Neo4j edges and image generation scene prompts.
    """
    llm = get_standard_llm()
    
    conflicts = state.get("consistency_report", {}).get("conflicts", [])
    retry_count = state.get("retry_count", 0)
    previous_events = state.get("extracted_events", [])
    
    is_re_extraction = retry_count > 0 and conflicts and previous_events
    
    try:
        if is_re_extraction:
            print(f"[EVENT] Re-extracting with {len(conflicts)} conflicts as feedback")
            chain = EVENT_RE_EXTRACTION_PROMPT | llm
            response = await chain.ainvoke({
                "story_text": state["content"],
                "conflicts": json.dumps(conflicts, ensure_ascii=False, indent=2),
                "previous_extraction": json.dumps(previous_events, ensure_ascii=False, indent=2)
            })
        else:
            chain = EVENT_EXTRACTION_PROMPT | llm
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
        events = result.get("events", [])
        
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
