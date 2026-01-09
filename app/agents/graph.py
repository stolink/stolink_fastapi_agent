"""LangGraph workflow with Supervisor pattern and feedback loops.

Implements:
- Supervisor routing
- Parallel extraction/analysis
- Feedback loop for re-extraction on conflicts
- Max retry limit
"""
import asyncio
from typing import Any, TypedDict, Annotated, Literal
import operator
import time

from langgraph.graph import StateGraph, START, END

# Character Team (Hierarchical Multi-Agent System) - Direct graph access
from app.agents.extraction.character.supervisor import character_team_graph
from app.agents.extraction.character.state import CharacterTeamState
from app.agents.extraction.event import event_extraction_node
from app.agents.extraction.setting import setting_extraction_node
# Removed: dialogue_analysis_node, emotion_tracking_node
from app.agents.analysis.relationship import relationship_analysis_node
from app.agents.analysis.consistency import consistency_check_node
# Removed: plot_node
from app.agents.analysis.global_resolution import GlobalResolutionAgent, GlobalResolutionResult
from app.agents.validation.validator import validator_node


# Define state with proper reducers
class AnalysisState(TypedDict, total=False):
    # Input (never changes)
    content: str
    project_id: str
    document_id: str
    job_id: str
    callback_url: str
    requires_deep_analysis: bool
    is_short_text: bool  # 🆕 Fast Track flag
    
    # Tracing
    trace_id: str
    
    # Existing data (from Spring Boot context or DB query)
    existing_characters: list
    existing_events: list
    existing_relationships: list
    existing_settings: list
    
    # Extraction results
    extracted_characters: list
    extracted_events: list
    extracted_settings: list

    
    # Analysis results
    relationship_graph: dict
    consistency_report: dict
    # Removed: plot
    
    # Validation
    validation_result: dict
    
    # Control flags (supervisor uses these)
    extraction_done: bool
    analysis_done: bool
    validation_done: bool
    retry_count: int
    
    # Accumulating fields (use operator.add reducer)
    messages: Annotated[list, operator.add]
    errors: Annotated[list, operator.add]


# Supervisor Logic
from app.agents.supervisor import supervisor_router, supervisor_node, MAX_EXTRACTION_RETRIES


async def extraction_node(state: dict) -> dict:
    """Execute extraction agents in proper order.
    
    Phase 1: Master Data (병렬)
        - Character Agent
        - Setting Agent
        
    Phase 2: Narrative Flow (순차 - Phase 1 완료 후)
        - Event Agent (Character/Setting 결과 참조)
        - Dialogue Agent
        - Emotion Agent
    """
    print(f"[EXTRACTION] Starting, content length: {len(state.get('content', ''))}", flush=True)
    
    # === Phase 1: Master Data Extraction (병렬) ===
    print("[EXTRACTION] Phase 1: Master Data (Character Team + Setting) - 병렬 실행", flush=True)
    
    # Prepare CharacterTeamState for hierarchical character extraction
    async def run_character_team():
        team_state: CharacterTeamState = {
            "content": state.get("content", ""),
            "retry_count": state.get("retry_count", 0),
            "completed_agents": [],
            "errors": [],
            "messages": [],
            # Pass existing characters for ID reuse
            "existing_characters": state.get("existing_characters", []),
        }
        # CRITICAL: Set recursion_limit to prevent infinite loops
        result = await character_team_graph.ainvoke(
            team_state,
            config={"recursion_limit": 50}  # Default is 25, increase for safety
        )
        return {
            "extracted_characters": result.get("extracted_characters", []),
            "messages": result.get("messages", []),
        }
    
    phase1_tasks = [
        asyncio.create_task(run_character_team()),  # Hierarchical Character Team (Direct)
        asyncio.create_task(setting_extraction_node(state)),
    ]
    phase1_results = await asyncio.gather(*phase1_tasks, return_exceptions=True)
    
    # Merge Phase 1 results into state
    phase1_state = dict(state)  # Copy state
    for result in phase1_results:
        if isinstance(result, dict):
            for key, value in result.items():
                if key not in ("messages", "errors", "partial_failure"):
                    phase1_state[key] = value
    
    char_count = len(phase1_state.get("extracted_characters", []))
    setting_count = len(phase1_state.get("extracted_settings", []))
    print(f"[EXTRACTION] Phase 1 완료: Characters={char_count}, Settings={setting_count}", flush=True)
    
    # === Phase 2: Narrative Flow Extraction (순차 - Phase 1 결과 참조) ===
    print("[EXTRACTION] Phase 2: Narrative Flow (Event) - 순차 실행 (Character/Setting 참조)", flush=True)
    phase2_tasks = [
        asyncio.create_task(event_extraction_node(phase1_state)),  # Phase 1 결과 참조!
        # Removed: dialogue_analysis_node, emotion_tracking_node
    ]
    phase2_results = await asyncio.gather(*phase2_tasks, return_exceptions=True)
    
    # Combine all results
    updates = {
        "messages": [{"role": "extraction", "content": "Extraction complete (2-phase)"}],
        "errors": [],
        "extraction_done": True,
        "analysis_done": False,  # Reset for re-extraction
        "validation_done": False,  # Reset for re-extraction
        "retry_count": state.get("retry_count", 0) + (1 if state.get("extraction_done", False) else 0),
    }
    
    # Apply Phase 1 results
    for result in phase1_results:
        if isinstance(result, Exception):
            updates["errors"].append(f"Phase 1 agent failed: {str(result)}")
        elif isinstance(result, dict):
            for key, value in result.items():
                if key == "messages":
                    updates["messages"].extend(value)
                elif key == "errors":
                    updates["errors"].extend(value)
                elif key not in ("partial_failure",):
                    updates[key] = value
    
    # Apply Phase 2 results
    for result in phase2_results:
        if isinstance(result, Exception):
            updates["errors"].append(f"Phase 2 agent failed: {str(result)}")
        elif isinstance(result, dict):
            for key, value in result.items():
                if key == "messages":
                    updates["messages"].extend(value)
                elif key == "errors":
                    updates["errors"].extend(value)
                elif key not in ("partial_failure",):
                    updates[key] = value
    
    event_count = len(updates.get("extracted_events", []))
    print(f"[EXTRACTION] Phase 2 완료: Events={event_count}", flush=True)
    
    # === POST-PROCESSING: Link events to characters via event_refs ===
    extracted_characters = updates.get("extracted_characters", [])
    extracted_events = updates.get("extracted_events", [])
    
    if extracted_characters and extracted_events:
        print(f"[EXTRACTION] Post-processing: Linking {len(extracted_events)} events to {len(extracted_characters)} characters", flush=True)
        
        # Build character name -> event_ids mapping
        char_to_events = {}
        for event in extracted_events:
            event_id = event.get("event_id")
            if event_id:
                for participant in event.get("participants", []):
                    if participant not in char_to_events:
                        char_to_events[participant] = []
                    if event_id not in char_to_events[participant]:
                        char_to_events[participant].append(event_id)
        
        # Update each character's event_refs
        for char in extracted_characters:
            char_name = char.get("profile", {}).get("name") or char.get("name", "")
            if char_name and char_to_events.get(char_name):
                # Ensure relations dict exists
                if "relations" not in char:
                    char["relations"] = {"graph": [], "event_refs": []}
                
                char["relations"]["event_refs"] = char_to_events[char_name]
                print(f"[EXTRACTION] Linked {len(char_to_events[char_name])} events to {char_name}", flush=True)
        
        updates["extracted_characters"] = extracted_characters
    
    print(f"[EXTRACTION] Done: chars={char_count}, settings={setting_count}, events={event_count}", flush=True)
    return updates


async def analysis_node(state: dict) -> dict:
    """Execute all analysis agents in parallel."""
    requires_deep = state.get("requires_deep_analysis", False)
    is_short_text = state.get("is_short_text", False)
    extracted_chars = state.get("extracted_characters", [])
    print(f"[ANALYSIS] Starting - requires_deep_analysis={requires_deep}, is_short_text={is_short_text}, extracted_characters count={len(extracted_chars)}", flush=True)
    
    # Always run relationship analysis + consistency check (fast)
    tasks = [
        asyncio.create_task(relationship_analysis_node(state)),
        asyncio.create_task(consistency_check_node(state)),  # Always run for consistency_report
    ]
    
    # Removed: plot_node (no longer needed)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    updates = {
        "messages": [{"role": "analysis", "content": "Analysis complete"}],
        "errors": [],
        "analysis_done": True,
    }
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            updates["errors"].append(f"Analysis {i} failed: {str(result)}")
        elif isinstance(result, dict):
            for key, value in result.items():
                if key == "messages":
                    updates["messages"].extend(value)
                elif key == "errors":
                    updates["errors"].extend(value)
                else:
                    updates[key] = value
    
    # Log consistency score
    score = updates.get("consistency_report", {}).get("overall_score", "N/A")
    print(f"[ANALYSIS] Done, consistency score: {score}", flush=True)
    return updates



async def global_resolution_node(state: dict) -> dict:
    """Resolve duplicate entities before analysis."""
    print("[GLOBAL_RES] Executing Global Entity Resolution...", flush=True)
    
    agent = GlobalResolutionAgent()
    characters = state.get("extracted_characters", [])
    
    # If no characters, just pass through
    if not characters:
        return {}
        
    resolved_characters = await agent.resolve_entities(characters)
    
    return {
        "extracted_characters": resolved_characters, 
        "messages": [{"role": "global_resolution", "content": f"Resolved {len(characters)} -> {len(resolved_characters)} characters"}]
    }

async def validation_node_wrapper(state: dict) -> dict:
    """Wrapper for validation node."""
    result = await validator_node(state)
    result["validation_done"] = True
    print(f"[VALIDATION] Done, action: {result.get('validation_result', {}).get('action', 'N/A')}", flush=True)
    return result


def create_analysis_graph():
    """Create Supervisor-based analysis workflow with feedback loops."""
    
    graph = StateGraph(AnalysisState)
    
    # Add nodes
    graph.add_node("extraction", extraction_node)
    graph.add_node("global_resolution", global_resolution_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("validation", validation_node_wrapper)
    
    # Entry: supervisor decides first step
    graph.add_conditional_edges(
        START,
        supervisor_router,
        {
            "extraction": "extraction",
            "analysis": "global_resolution",
            "validation": "validation",
            "__end__": END,
        }
    )
    
    # After extraction: supervisor decides next
    graph.add_conditional_edges(
        "extraction",
        supervisor_router,
        {
            "extraction": "extraction",
            "analysis": "global_resolution",
            "validation": "validation",
            "__end__": END,
        }
    )
    # After global_resolution: always go to analysis
    graph.add_edge("global_resolution", "analysis")
    
    # After analysis: supervisor decides next (may loop back)
    graph.add_conditional_edges(
        "analysis",
        supervisor_router,
        {
            "extraction": "extraction",  # Feedback loop!
            "analysis": "analysis",
            "validation": "validation",
            "__end__": END,
        }
    )
    
    # After validation: supervisor decides (may loop back for retry)
    graph.add_conditional_edges(
        "validation",
        supervisor_router,
        {
            "extraction": "extraction",  # Feedback loop!
            "analysis": "analysis",
            "validation": "validation",
            "__end__": END,
        }
    )
    
    return graph.compile()


# Global graph instance
_analysis_graph = None


def get_analysis_graph():
    """Get or create the analysis graph singleton."""
    global _analysis_graph
    if _analysis_graph is None:
        _analysis_graph = create_analysis_graph()
    return _analysis_graph


async def run_analysis_pipeline(
    content: str,
    project_id: str,
    document_id: str,
    job_id: str,
    callback_url: str,
    existing_characters: list = None,
    existing_events: list = None,
    existing_relationships: list = None,
    existing_settings: list = None,
    trace_id: str = "",
    requires_deep_analysis: bool = False,
    is_short_text: bool = False, # 🆕 Add parameter
) -> dict[str, Any]:
    """Run the complete analysis pipeline with Supervisor."""
    
    # 🆕 디버그 로그
    print(f"[PIPELINE] run_analysis_pipeline called with requires_deep_analysis={requires_deep_analysis}, is_short_text={is_short_text}", flush=True)
    
    initial_state: AnalysisState = {
        "content": content,
        "project_id": project_id,
        "document_id": document_id,
        "job_id": job_id,
        "callback_url": callback_url,
        "trace_id": trace_id,
        "requires_deep_analysis": requires_deep_analysis,
        "is_short_text": is_short_text, # 🆕 Add to state
        "existing_characters": existing_characters or [],
        "existing_events": existing_events or [],
        "existing_relationships": existing_relationships or [],
        "existing_settings": existing_settings or [],
        "extracted_characters": [],
        "extracted_events": [],
        "extracted_settings": [],
        "relationship_graph": {},
        "consistency_report": {},
        "validation_result": {},
        "extraction_done": False,
        "analysis_done": False,
        "validation_done": False,
        "retry_count": 0,
        "messages": [],
        "errors": [],
    }
    
    start_time = time.time()
    
    graph = get_analysis_graph()
    final_state = await graph.ainvoke(initial_state)
    
    final_state["processing_time_ms"] = int((time.time() - start_time) * 1000)
    
    return dict(final_state)
