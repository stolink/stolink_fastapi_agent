"""Plot Integrator Agent - with Structured Output.

Role: "Story Structure Architect" / "Narrative Pattern Analyst"
- Analyzes events for story structure and pacing
- Detects foreshadowing and links to future events
- Provides 3-Act structure analysis
- Generates neo4j-ready connections for foreshadowing

Uses with_structured_output() for:
- Guaranteed valid JSON
- Pydantic schema validation
- No manual parsing required
"""
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_structured_llm, get_standard_llm
from app.schemas.plot import PlotIntegrationResult, NarrativeBeat, ThreeActSection, Foreshadowing, BeatType


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
   - beat_type: "SETUP", "INCITING_INCIDENT", "RISING_ACTION", "MIDPOINT", "COMPLICATION", "CRISIS", "CLIMAX", "FALLING_ACTION", "RESOLUTION"
   - event_ref: Related event_id (EXACT)
   - visual_prompt: Short prompt for illustration generation

3. **3-Act Structure Analysis**
   - act: "setup", "confrontation", "resolution"
   - event_ids: Events belonging to this act
   - purpose: What this act accomplishes

4. **Tension Curve Array** (REQUIRED for audio/direction timing)
   - Array of tension levels (1-10) at each beat
   - Length MUST match number of narrative_beats
   - CRITICAL: This field MUST NOT be empty!

5. **Foreshadowing Detection** (REQUIRED fields)
   - foreshadow_id: Unique ID (F001, F002...) - REQUIRED
   - source_event: Event where hint appears (EXACT event_id)
   - hint_text: The foreshadowing text/dialogue - REQUIRED
   - predicted_outcome: What this hints at
   - confidence: 1-10 (7+ = MAJOR foreshadowing)
   - target_event: If known, the event_id this foreshadows (null if future)

=== IMPORTANT FOR MULTIMEDIA AUTOMATION ===
1. tension_curve array length MUST match narrative_beats count
2. Each beat should have a concise visual_prompt for illustration AI
3. beat_type follows standard screenplay beat structure
4. tension_curve MUST NOT be empty - derive from event importance if needed
5. EVERY foreshadowing MUST have foreshadow_id and hint_text"""),
    ("human", """=== DATA TO ANALYZE ===

**Available Events** (use EXACT event_ids):
{events}

**Characters** (for context):
{characters}

**Character Personalities** (for motivation):
{personalities}

**Relationships** (for conflict understanding):
{relationships}

Analyze the plot structure with tension curve and narrative beats.
TIP: Use "Character Personalities" to understand WHY characters act this way (Motivations).""")
])


def generate_fallback_beats(events: list) -> list[NarrativeBeat]:
    """Generate narrative beats from events if LLM fails."""
    beat_types = [BeatType.SETUP, BeatType.INCITING_INCIDENT, BeatType.RISING_ACTION, 
                  BeatType.CLIMAX, BeatType.FALLING_ACTION]
    
    beats = []
    for i, event in enumerate(events):
        beat_type = beat_types[min(i, len(beat_types) - 1)]
        if i >= len(beat_types):
            beat_type = BeatType.RISING_ACTION
        
        beats.append(NarrativeBeat(
            beat_id=i + 1,
            text=event.get("description", f"Event {i + 1}"),
            beat_type=beat_type,
            event_ref=event.get("event_id", f"E{i + 1:03d}"),
            visual_prompt=f"{event.get('description', '')} - dramatic scene"
        ))
    
    return beats


def generate_fallback_tension_curve(events: list) -> list[float]:
    """Generate tension curve from event importance if LLM fails."""
    if not events:
        return [5.0]
    
    curve = []
    for event in events:
        importance = event.get("importance", 5)
        tension = max(1.0, min(10.0, float(importance)))
        curve.append(tension)
    
    return curve


async def plot_integration_node(state: dict) -> dict:
    """Plot Integrator Agent node function - with Structured Output.
    
    Uses with_structured_output() for guaranteed schema compliance.
    Includes fallback generation for critical fields.
    """
    events = state.get("extracted_events", [])
    characters = state.get("extracted_characters", [])
    relationships = state.get("relationship_graph", {}).get("relationships", [])
    
    available_event_ids = [e.get("event_id", "") for e in events if e.get("event_id")]
    
    # Extract Personalities for context
    available_personalities = []
    for c in characters:
        name = c.get("name") or (c.get("profile", {}) or {}).get("name")
        if name:
            pers = c.get("personality", {}) or c.get("char_personality", {})
            traits = []
            if isinstance(pers, dict):
                traits = pers.get("core_traits", [])
                if not traits and "traits" in pers:
                    traits = pers["traits"]
            
            if traits:
                clean_traits = [t if isinstance(t, str) else str(t) for t in traits]
                available_personalities.append(f"{name}: [{', '.join(clean_traits[:5])}]")
    
    pers_str = "\n".join(available_personalities) if available_personalities else "None"
    
    print(f"[PLOT] Analyzing {len(events)} events for narrative structure")
    print(f"[PLOT] Available event_ids: {available_event_ids}")
    
    # === GUARD: Return minimal result if no events ===
    if not events:
        print("[PLOT] No events available - returning minimal result without event_refs")
        
        # Extract character names for basic narrative
        char_names = [c.get("name") or (c.get("profile", {}) or {}).get("name") for c in characters if c.get("name") or (c.get("profile", {}) or {}).get("name")]
        
        return {
            "plot_integration": {
                "plot_summary": {
                    "narrative": f"Characters present: {', '.join(char_names[:5]) if char_names else 'Unknown'}. No detailed events extracted.",
                    "central_conflict": "Unable to determine without event data"
                },
                "overall_tension": 5.0,
                "narrative_beats": [],  # NO hallucinated event_refs
                "tension_curve": [],
                "three_act_structure": [],
                "foreshadowing": [],
                "multimedia_summary": {
                    "beat_count": 0,
                    "tension_curve_length": 0,
                    "has_visual_prompts": False
                }
            },
            "messages": [
                {"role": "plot_agent", "content": "No events available - skipped plot analysis to prevent hallucination"}
            ]
        }
    
    
    try:
        # Get structured LLM
        structured_llm = get_structured_llm(PlotIntegrationResult)
        chain = PLOT_INTEGRATION_PROMPT | structured_llm
        
        result: PlotIntegrationResult = await chain.ainvoke({
            "events": str(events),
            # Support both legacy (c["name"]) and FullCharacter (c["profile"]["name"]) formats
            "characters": str([c.get("name") or (c.get("profile", {}) or {}).get("name") for c in characters if c.get("name") or (c.get("profile", {}) or {}).get("name")]),
            "personalities": pers_str,
            "relationships": str(relationships) if relationships else "[]"
        })
        
    except Exception as e:
        print(f"[PLOT] Structured output error: {e}, using fallback generation")
        # Create minimal result
        result = PlotIntegrationResult(
            plot_summary={"narrative": "Auto-generated plot summary", "central_conflict": "Unknown"},
            overall_tension=5.0,
            narrative_beats=[],
            tension_curve=[],
            three_act_structure=[],
            foreshadowing=[]
        )
    
    # === PROGRAMMATIC BACKUP: Narrative Beats ===
    beats = result.narrative_beats
    if not beats and events:
        print(f"[PLOT] Generating fallback narrative_beats from {len(events)} events")
        result.narrative_beats = generate_fallback_beats(events)
        beats = result.narrative_beats
    
    # === PROGRAMMATIC BACKUP: Tension Curve ===
    tension_curve = result.tension_curve
    if not tension_curve and events:
        print(f"[PLOT] Generating fallback tension_curve from event importance")
        result.tension_curve = generate_fallback_tension_curve(events)
        tension_curve = result.tension_curve
    
    # Validate tension_curve length matches beats
    if len(tension_curve) != len(beats) and beats:
        print(f"[PLOT] Adjusting tension_curve length ({len(tension_curve)}) to match beats ({len(beats)})")
        if len(tension_curve) < len(beats):
            avg = sum(tension_curve) / len(tension_curve) if tension_curve else 5.0
            tension_curve.extend([avg] * (len(beats) - len(tension_curve)))
        else:
            tension_curve = tension_curve[:len(beats)]
        result.tension_curve = tension_curve
    
    # === Update multimedia summary ===
    result.multimedia_summary.beat_count = len(beats)
    result.multimedia_summary.tension_curve_length = len(tension_curve)
    result.multimedia_summary.has_visual_prompts = all(b.visual_prompt for b in beats)
    
    # Convert to dict for state
    result_dict = result.model_dump()
    
    # === Summary stats ===
    foreshadow_count = len(result.foreshadowing)
    tension_avg = result.overall_tension
    beat_count = len(beats)
    
    print(f"[PLOT] Beats: {beat_count}, Tension curve: {tension_curve}")
    print(f"[PLOT] Foreshadowing: {foreshadow_count}")
    
    return {
        "plot_integration": result_dict,
        "messages": [
            {"role": "plot_agent", 
             "content": f"Analyzed: {beat_count} beats, tension {tension_curve}, {foreshadow_count} foreshadowing (Structured Output)"}
        ]
    }
