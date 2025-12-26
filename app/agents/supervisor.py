"""Supervisor Agent - Level 0.

Orchestrates the entire multi-agent pipeline:
- Routes to extraction, analysis, or validation phases
- Controls workflow progression
- Handles error recovery
"""
from typing import Literal

from app.agents.llm import get_basic_llm


def supervisor_router(state: dict) -> Literal["parallel_extraction", "parallel_analysis", "validation", "__end__"]:
    """Supervisor routing logic.
    
    Determines the next phase based on current state.
    
    Args:
        state: Current pipeline state
        
    Returns:
        Next node to execute
    """
    extraction_done = state.get("extraction_done", False)
    analysis_done = state.get("analysis_done", False)
    validation_done = state.get("validation_done", False)
    errors = state.get("errors", [])
    
    print(f"[ROUTER] extraction_done={extraction_done}, analysis_done={analysis_done}, validation_done={validation_done}, errors={len(errors)}")
    
    # Check for critical errors that should abort
    if len(errors) > 5:  # Too many errors
        print("[ROUTER] -> __end__ (too many errors)")
        return "__end__"
    
    # Phase 1: Extraction not done
    if not extraction_done:
        print("[ROUTER] -> parallel_extraction")
        return "parallel_extraction"
    
    # Phase 2: Analysis not done
    if not analysis_done:
        print("[ROUTER] -> parallel_analysis")
        return "parallel_analysis"
    
    # Phase 3: Validation not done
    if not validation_done:
        print("[ROUTER] -> validation")
        return "validation"
    
    # All phases complete
    print("[ROUTER] -> __end__ (all done)")
    return "__end__"


async def supervisor_node(state: dict) -> dict:
    """Supervisor Agent node function.
    
    Simple routing node that determines next phase.
    Uses LLM only for complex decisions if needed.
    
    Args:
        state: Current pipeline state
        
    Returns:
        Updated state with routing decision
    """
    # Determine next action
    next_action = supervisor_router(state)
    
    # Return ONLY the updates
    return {
        "messages": state.get("messages", []) + [
            {"role": "supervisor", "content": f"Routing to: {next_action}"}
        ]
    }
