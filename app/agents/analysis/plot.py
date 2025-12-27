"""Plot Integrator Agent - Level 2 (Production Level).

Role: "Story Structure Architect" / "Narrative Pattern Analyst"
- Analyzes events for story structure and pacing
- Detects foreshadowing and links to future events
- Provides 3-Act structure analysis
- Generates neo4j-ready connections for foreshadowing
- **Temporal Control**: Tension curve array for audio/direction timing
- **Beat Markers**: Narrative beats for cut editing and illustration prompts

Key: Connect events to narrative structure for story visualization.
Uses: extracted_events, extracted_characters, relationship_graph
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_standard_llm


PLOT_INTEGRATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a "Story Structure Architect" / "Narrative Pattern Analyst".
Your job is to analyze events for narrative structure, pacing, and foreshadowing.

=== CRITICAL: Use EXACT Event and Character Names ===

Use the EXACT event_ids and character names from the provided data.

❌ BAD: "the protagonist's meeting" 
✅ GOOD: "E001" (exact event_id)

=== YOUR TASK ===

1. **Plot Summary**
   - narrative: Brief narrative summary (2-3 sentences)
   - central_conflict: Main conflict identification

2. **Narrative Beats** (for cut editing / illustration prompts)
   - beat_id: Sequential index (1, 2, 3...)
   - text: Short description of this beat
   - beat_type: "SETUP", "INCITING_INCIDENT", "RISING_ACTION", "CLIMAX", "FALLING_ACTION", "RESOLUTION"
   - event_ref: Related event_id (EXACT)
   - visual_prompt: Short prompt for illustration generation

3. **3-Act Structure Analysis**
   - act: "setup", "confrontation", "resolution"
   - event_ids: Events belonging to this act
   - purpose: What this act accomplishes

4. **Tension Curve Array** (REQUIRED for audio/direction timing)
   - Array of tension levels (1-10) at each beat
   - Length MUST match number of narrative_beats
   - Example: [3, 5, 7, 8, 6] - shows build-up and drop patterns
   - CRITICAL: This field MUST NOT be empty!

5. **Foreshadowing Detection**
   - foreshadow_id: Unique ID (F001, F002...)
   - source_event: Event where hint appears (EXACT event_id)
   - hint_text: The foreshadowing text/dialogue
   - predicted_outcome: What this hints at
   - confidence: 1-10
   - target_event: If known, the event_id this foreshadows (null if future)

=== OUTPUT STRUCTURE ===
Return ONLY valid JSON:
{{
  "plot_summary": {{
    "narrative": "Brief story summary...",
    "central_conflict": "Main conflict description"
  }},
  "narrative_beats": [
    {{
      "beat_id": 1,
      "text": "서진과 하나가 어두운 숲에서 만남",
      "beat_type": "SETUP",
      "event_ref": "E001",
      "visual_prompt": "Two figures meeting in dark forest, mysterious atmosphere"
    }},
    {{
      "beat_id": 2,
      "text": "이민호의 갑작스러운 등장",
      "beat_type": "INCITING_INCIDENT",
      "event_ref": "E002",
      "visual_prompt": "Shadowy figure emerging from darkness, tense moment"
    }}
  ],
  "tension_curve": [3, 5, 7, 8, 6],
  "three_act_structure": [
    {{
      "act": "setup",
      "event_ids": ["E001", "E002"],
      "purpose": "Establish characters and setting"
    }}
  ],
  "foreshadowing": [
    {{
      "foreshadow_id": "F001",
      "source_event": "E004",
      "hint_text": "이민호가 과거 배신의 이유를 암시",
      "predicted_outcome": "배신의 진짜 이유가 밝혀질 것",
      "confidence": 8,
      "target_event": null
    }}
  ],
  "overall_tension": 7
}}

=== IMPORTANT FOR MULTIMEDIA AUTOMATION ===
1. tension_curve array length MUST match narrative_beats count
2. Each beat should have a concise visual_prompt for illustration AI
3. beat_type follows standard screenplay beat structure
4. tension_curve MUST NOT be empty - derive from event importance if needed"""),
    ("human", """=== DATA TO ANALYZE ===

**Available Events** (use EXACT event_ids):
{events}

**Characters** (for context):
{characters}

**Relationships** (for conflict understanding):
{relationships}

Analyze the plot structure with tension curve and narrative beats:""")
])


def generate_fallback_beats(events: list) -> list:
    """Generate narrative beats from events if LLM fails."""
    beats = []
    beat_types = ["SETUP", "INCITING_INCIDENT", "RISING_ACTION", "CLIMAX", "FALLING_ACTION"]
    
    for i, event in enumerate(events):
        beat_type = beat_types[min(i, len(beat_types) - 1)]
        if i >= len(beat_types):
            beat_type = "RISING_ACTION"
        
        beats.append({
            "beat_id": i + 1,
            "text": event.get("description", f"Event {i + 1}"),
            "beat_type": beat_type,
            "event_ref": event.get("event_id", f"E{i + 1:03d}"),
            "visual_prompt": f"{event.get('description', '')} - dramatic scene"
        })
    
    return beats


def generate_fallback_tension_curve(events: list) -> list:
    """Generate tension curve from event importance if LLM fails."""
    if not events:
        return [5]  # Default single value
    
    curve = []
    for event in events:
        # Use event importance (1-10) as base tension
        importance = event.get("importance", 5)
        # Clamp to 1-10 range
        tension = max(1, min(10, importance))
        curve.append(tension)
    
    return curve


async def plot_integration_node(state: dict) -> dict:
    """Plot Integrator Agent node function - Production Level.
    
    Role: "Story Structure Architect" - analyzes narrative structure.
    
    Key features:
    - 3-Act structure analysis
    - Foreshadowing detection with confidence scores
    - Tension curve array for audio/direction timing (with fallback)
    - Narrative beats for cut editing and illustration prompts (with fallback)
    """
    llm = get_standard_llm()
    
    events = state.get("extracted_events", [])
    characters = state.get("extracted_characters", [])
    relationships = state.get("relationship_graph", {}).get("relationships", [])
    
    # Get available event IDs for reference
    available_event_ids = [e.get("event_id", "") for e in events if e.get("event_id")]
    
    print(f"[PLOT] Analyzing {len(events)} events for narrative structure")
    print(f"[PLOT] Available event_ids: {available_event_ids}")
    
    chain = PLOT_INTEGRATION_PROMPT | llm
    
    try:
        response = await chain.ainvoke({
            "events": json.dumps(events, ensure_ascii=False, indent=2),
            "characters": json.dumps([c.get("name", "") for c in characters], ensure_ascii=False),
            "relationships": json.dumps(relationships, ensure_ascii=False, indent=2) if relationships else "[]"
        })
        
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        
    except Exception as e:
        print(f"[PLOT] LLM error: {e}, using fallback generation")
        result = {
            "plot_summary": {"narrative": "Auto-generated plot summary", "central_conflict": "Unknown"},
            "three_act_structure": [],
            "foreshadowing": [],
            "overall_tension": 5
        }
    
    # === PROGRAMMATIC BACKUP: Narrative Beats ===
    beats = result.get("narrative_beats", [])
    if not beats and events:
        print(f"[PLOT] Generating fallback narrative_beats from {len(events)} events")
        beats = generate_fallback_beats(events)
        result["narrative_beats"] = beats
    
    # === PROGRAMMATIC BACKUP: Tension Curve ===
    tension_curve = result.get("tension_curve", [])
    if not tension_curve and events:
        print(f"[PLOT] Generating fallback tension_curve from event importance")
        tension_curve = generate_fallback_tension_curve(events)
        result["tension_curve"] = tension_curve
    
    # Validate tension_curve length matches beats
    if len(tension_curve) != len(beats) and beats:
        print(f"[PLOT] Adjusting tension_curve length ({len(tension_curve)}) to match beats ({len(beats)})")
        if len(tension_curve) < len(beats):
            # Pad with average tension
            avg = sum(tension_curve) / len(tension_curve) if tension_curve else 5
            tension_curve.extend([int(avg)] * (len(beats) - len(tension_curve)))
        else:
            tension_curve = tension_curve[:len(beats)]
        result["tension_curve"] = tension_curve
    
    # === Neo4j-Ready Output: Foreshadowing Edges ===
    neo4j_foreshadowing = []
    for fs in result.get("foreshadowing", []):
        if fs.get("source_event"):
            edge = {
                "source": fs.get("source_event"),
                "target": fs.get("target_event"),
                "relationship_type": "FORESHADOWS",
                "attributes": {
                    "hint_text": fs.get("hint_text", ""),
                    "predicted_outcome": fs.get("predicted_outcome", ""),
                    "confidence": fs.get("confidence", 5)
                }
            }
            neo4j_foreshadowing.append(edge)
    
    result["neo4j_foreshadowing"] = neo4j_foreshadowing
    
    # === Summary for multimedia pipeline ===
    multimedia_summary = {
        "beat_count": len(beats),
        "tension_curve_length": len(tension_curve),
        "tension_curve_source": "llm" if result.get("tension_curve") else "fallback",
        "tension_range": {
            "min": min(tension_curve) if tension_curve else 0,
            "max": max(tension_curve) if tension_curve else 0,
            "peak_index": tension_curve.index(max(tension_curve)) if tension_curve else 0
        },
        "beat_types": list(set(b.get("beat_type", "") for b in beats)),
        "has_visual_prompts": all(b.get("visual_prompt") for b in beats)
    }
    result["multimedia_summary"] = multimedia_summary
    
    # === Summary stats ===
    foreshadow_count = len(result.get("foreshadowing", []))
    tension_avg = result.get("overall_tension", 5)
    act_count = len(result.get("three_act_structure", []))
    
    print(f"[PLOT] Beats: {len(beats)}, Tension curve: {tension_curve}")
    print(f"[PLOT] Foreshadowing: {foreshadow_count}, Acts: {act_count}")
    
    return {
        "plot_integration": result,
        "messages": [
            {"role": "plot_agent", 
             "content": f"Analyzed: {len(beats)} beats, tension curve {tension_curve}, {foreshadow_count} foreshadowing"}
        ]
    }
