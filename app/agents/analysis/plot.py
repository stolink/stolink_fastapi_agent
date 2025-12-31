"""Plot Integrator Agent - Simplified version.

Role: "Story Structure Architect"
- Generates plot summary and central conflict
- Uses simplified PlotResult schema
"""
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_structured_llm
from app.schemas.plot import PlotResult, PlotSummary


PLOT_INTEGRATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a "Story Structure Architect".
Your job is to analyze events and create a plot summary.

=== YOUR TASK ===

1. **Plot Summary**
   - narrative: Brief narrative summary (2-3 sentences)
   - central_conflict: Main conflict identification

Use the EXACT event_ids and character names from the provided data."""),
    ("human", """=== DATA TO ANALYZE ===

**Events:**
{events}

**Characters:**
{characters}

Create a plot summary with narrative and central conflict.""")
])


async def plot_node(state: dict) -> dict:
    """Plot Integrator Agent - Simplified.
    
    Returns simplified PlotResult with just summary.
    """
    events = state.get("extracted_events", [])
    characters = state.get("extracted_characters", [])
    
    print(f"[PLOT] Analyzing {len(events)} events for narrative structure")
    
    # Extract character names
    char_names = []
    for c in characters:
        name = c.get("name") or (c.get("profile", {}) or {}).get("name")
        if name:
            char_names.append(name)
    
    # Return minimal result if no events
    if not events:
        print("[PLOT] No events available - returning minimal result")
        return {
            "plot": {
                "summary": {
                    "narrative": f"Characters present: {', '.join(char_names[:5]) if char_names else 'Unknown'}. No detailed events extracted.",
                    "central_conflict": "Unable to determine without event data"
                }
            },
            "messages": [
                {"role": "plot_agent", "content": "No events - skipped plot analysis"}
            ]
        }
    
    try:
        structured_llm = get_structured_llm(PlotResult)
        chain = PLOT_INTEGRATION_PROMPT | structured_llm
        
        result: PlotResult = await chain.ainvoke({
            "events": str(events),
            "characters": str(char_names)
        })
        
    except Exception as e:
        print(f"[PLOT] Structured output error: {e}, using fallback")
        result = PlotResult(
            summary=PlotSummary(
                narrative="Auto-generated plot summary",
                central_conflict="Unknown"
            )
        )
    
    result_dict = result.model_dump()
    
    print(f"[PLOT] Summary generated: {result.summary.narrative[:50]}...")
    
    return {
        "plot": result_dict,
        "messages": [
            {"role": "plot_agent", "content": f"Plot analyzed (Simplified)"}
        ]
    }
