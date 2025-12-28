"""Supervisor Agent - Level 0 (Production Level).

Role: "Pipeline Orchestrator" / "Workflow Controller"
- Orchestrates the entire multi-agent pipeline
- Routes to extraction, analysis, or validation phases
- Controls workflow progression with feedback loops
- Handles error recovery and re-extraction
- Provides global trace_id for request tracking
- Maintains supervisor_state for monitoring

Routing Logic:
1. If extraction not done → parallel_extraction
2. If analysis not done → parallel_analysis
3. If validation not done → validation
4. If validation.action == "retry_extraction" → parallel_extraction (re-run)
5. If consistency.requires_reextraction → parallel_extraction (re-run)
6. If max_retries exceeded → human_review or __end__
7. All done → __end__
"""
import uuid
from typing import Literal

from app.agents.llm import get_basic_llm


# Maximum retry counts to prevent infinite loops
MAX_EXTRACTION_RETRIES = 3
MAX_ANALYSIS_RETRIES = 2


def generate_trace_id() -> str:
    """Generate a unique trace ID for request tracking."""
    import datetime
    date_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    return f"req-{date_str}-{short_uuid}"


def get_supervisor_state(state: dict) -> dict:
    """Get or create supervisor state with retry tracking."""
    return {
        "trace_id": state.get("trace_id", "unknown"),
        "current_phase": get_current_phase(state),
        "retry_counts": {
            "extraction": state.get("extraction_retry_count", 0),
            "analysis": state.get("analysis_retry_count", 0)
        },
        "max_retries": {
            "extraction": MAX_EXTRACTION_RETRIES,
            "analysis": MAX_ANALYSIS_RETRIES
        },
        "error_count": len(state.get("errors") or []),
        "force_fail": state.get("force_fail", False)
    }


def get_current_phase(state: dict) -> str:
    """Determine the current phase based on state flags."""
    if not state.get("extraction_done"):
        return "extraction"
    elif not state.get("analysis_done"):
        return "analysis"
    elif not state.get("validation_done"):
        return "validation"
    else:
        return "complete"


def get_phase_status(state: dict) -> dict:
    """Get detailed status of each pipeline phase."""
    return {
        "extraction": {
            "done": state.get("extraction_done", False),
            "characters": len(state.get("extracted_characters") or []),
            "events": len(state.get("extracted_events") or []),
            "settings": len(state.get("extracted_settings") or []),
            "dialogues": bool(state.get("analyzed_dialogues")),
            "emotions": bool(state.get("tracked_emotions"))
        },
        "analysis": {
            "done": state.get("analysis_done", False),
            "relationships": len((state.get("relationship_graph") or {}).get("relationships", [])),
            "consistency_score": (state.get("consistency_report") or {}).get("overall_score", 0),
            "plot_beats": len((state.get("plot_integration") or {}).get("narrative_beats", []))
        },
        "validation": {
            "done": state.get("validation_done", False),
            "quality_score": (state.get("validation_result") or {}).get("quality_score", 0),
            "action": (state.get("validation_result") or {}).get("action", "pending")
        }
    }


def should_retry_extraction(state: dict) -> tuple[bool, str]:
    """Check if extraction should be retried based on validation/consistency.
    
    Returns:
        (should_retry, reason): Tuple of retry decision and reason
    """
    retry_count = state.get("extraction_retry_count", 0)
    trace_id = state.get("trace_id", "unknown")
    
    # Check if max retries exceeded
    if retry_count >= MAX_EXTRACTION_RETRIES:
        print(f"[{trace_id}] Max extraction retries ({MAX_EXTRACTION_RETRIES}) reached -> FORCE FAIL")
        return False, "max_retries_exceeded"
    
    # Check validation result
    validation_result = state.get("validation_result") or {}
    if validation_result.get("action") == "retry_extraction":
        print(f"[{trace_id}] Validation requested retry_extraction (attempt {retry_count + 1}/{MAX_EXTRACTION_RETRIES})")
        return True, "validation_rejected"
    
    # Check consistency report
    consistency_report = state.get("consistency_report") or {}
    if consistency_report.get("requires_reextraction"):
        print(f"[{trace_id}] Consistency requires re-extraction (score: {consistency_report.get('overall_score')})")
        return True, "consistency_failed"
    
    return False, "no_retry_needed"


def supervisor_router(state: dict) -> Literal["parallel_extraction", "parallel_analysis", "validation", "human_review", "__end__"]:
    """Supervisor routing logic - Production Level.
    
    Determines the next phase based on current state.
    Supports feedback loops for re-extraction when quality is low.
    Routes to human_review if max retries exceeded.
    
    Args:
        state: Current pipeline state
        
    Returns:
        Next node to execute
    """
    extraction_done = state.get("extraction_done", False)
    analysis_done = state.get("analysis_done", False)
    validation_done = state.get("validation_done", False)
    errors = state.get("errors") or []
    trace_id = state.get("trace_id", "unknown")
    
    phase_status = get_phase_status(state)
    supervisor_state = get_supervisor_state(state)
    
    print(f"[{trace_id}] Phase Status:")
    print(f"  - Extraction: done={extraction_done}, chars={phase_status['extraction']['characters']}, events={phase_status['extraction']['events']}")
    print(f"  - Analysis: done={analysis_done}, rels={phase_status['analysis']['relationships']}, consistency={phase_status['analysis']['consistency_score']}")
    print(f"  - Validation: done={validation_done}, score={phase_status['validation']['quality_score']}, action={phase_status['validation']['action']}")
    print(f"  - Retries: extraction={supervisor_state['retry_counts']['extraction']}/{MAX_EXTRACTION_RETRIES}")
    print(f"  - Errors: {len(errors)}")
    
    # Check for critical errors that should abort
    if len(errors) > 5:
        print(f"[{trace_id}] -> __end__ (too many errors)")
        return "__end__"
    
    # Check if force fail (max retries exceeded in previous run)
    if state.get("force_fail"):
        print(f"[{trace_id}] -> human_review (force fail - max retries exceeded)")
        return "human_review"
    
    # Phase 1: Extraction not done
    if not extraction_done:
        print(f"[{trace_id}] -> parallel_extraction (initial)")
        return "parallel_extraction"
    
    # Phase 2: Analysis not done
    if not analysis_done:
        print(f"[{trace_id}] -> parallel_analysis")
        return "parallel_analysis"
    
    # Phase 3: Validation not done
    if not validation_done:
        print(f"[{trace_id}] -> validation")
        return "validation"
    
    # === Feedback Loop: Check if re-extraction is needed ===
    should_retry, reason = should_retry_extraction(state)
    if should_retry:
        print(f"[{trace_id}] -> parallel_extraction (retry: {reason})")
        return "parallel_extraction"
    elif reason == "max_retries_exceeded":
        # Max retries reached, route to human review
        print(f"[{trace_id}] -> human_review (max retries exceeded)")
        return "human_review"
    
    # All phases complete
    print(f"[{trace_id}] -> __end__ (all done)")
    return "__end__"


async def supervisor_node(state: dict) -> dict:
    """Supervisor Agent node function - Production Level.
    
    Role: "Pipeline Orchestrator" - routes to appropriate phases.
    
    Features:
    - Generates trace_id for request tracking
    - Tracks retry counts for feedback loops
    - Routes to human_review if max retries exceeded
    - Provides detailed routing information
    
    Args:
        state: Current pipeline state
        
    Returns:
        Updated state with routing decision
    """
    updates = {}
    
    # Generate or preserve trace_id
    trace_id = state.get("trace_id")
    if not trace_id:
        trace_id = generate_trace_id()
        updates["trace_id"] = trace_id
        print(f"[{trace_id}] New request started")
    
    # Determine next action
    next_action = supervisor_router(state)
    
    # Track retry count if going back to extraction
    if next_action == "parallel_extraction" and state.get("extraction_done"):
        # This is a retry
        retry_count = state.get("extraction_retry_count", 0) + 1
        updates["extraction_retry_count"] = retry_count
        updates["extraction_done"] = False  # Reset for retry
        print(f"[{trace_id}] Resetting extraction for retry #{retry_count}")
    
    # Check if max retries exceeded and mark for human review
    if next_action == "human_review":
        updates["force_fail"] = True
        updates["force_fail_reason"] = "max_retries_exceeded"
    
    # Get supervisor state for message
    supervisor_state = get_supervisor_state({**state, **updates})
    phase_status = get_phase_status(state)
    
    # Build message
    message = {
        "role": "supervisor",
        "content": f"Routing to: {next_action}",
        "trace_id": trace_id,
        "supervisor_state": supervisor_state,
        "phase_status": phase_status
    }
    
    updates["messages"] = [message]
    updates["supervisor_state"] = supervisor_state
    
    return updates


def get_routing_summary(state: dict) -> dict:
    """Get a summary of the current routing state for debugging."""
    trace_id = state.get("trace_id", "unknown")
    return {
        "trace_id": trace_id,
        "supervisor_state": get_supervisor_state(state),
        "phase_status": get_phase_status(state),
        "next_action": supervisor_router(state)
    }


async def human_review_node(state: dict) -> dict:
    """Human Review node for handling max retries exceeded cases.
    
    This node is called when the pipeline cannot complete automatically
    and requires human intervention.
    """
    trace_id = state.get("trace_id", "unknown")
    
    print(f"[{trace_id}] Pipeline requires human review")
    print(f"[{trace_id}] Reason: {state.get('force_fail_reason', 'unknown')}")
    
    return {
        "human_review_required": True,
        "human_review_reason": state.get("force_fail_reason", "max_retries_exceeded"),
        "validation_done": True,  # Mark as done to exit loop
        "messages": [
            {
                "role": "human_review",
                "content": f"Pipeline requires human intervention. Reason: {state.get('force_fail_reason', 'unknown')}",
                "trace_id": trace_id
            }
        ]
    }
