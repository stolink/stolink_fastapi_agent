"""Supervisor Agent - Level 0 (Production Level).

Role: "Pipeline Orchestrator" / "Workflow Controller"
- Orchestrates the entire multi-agent pipeline
- Routes to extraction, analysis, or validation phases
- Controls workflow progression with feedback loops
- Handles error recovery and re-extraction
- Provides global trace_id for request tracking
- Routes to human_review if max retries exceeded

Routing Logic:
1. If extraction not done → parallel_extraction
2. If analysis not done → parallel_analysis
3. If validation not done → validation
4. If validation.action == "retry_extraction" → parallel_extraction (re-run)
5. If consistency.requires_reextraction → parallel_extraction (re-run)
6. If max_retries exceeded → human_review
7. All done → __end__
"""
import uuid
import datetime
from typing import Literal

from app.agents.llm import get_basic_llm


# Maximum retry counts to prevent infinite loops
MAX_EXTRACTION_RETRIES = 3
MAX_ANALYSIS_RETRIES = 2


def generate_trace_id() -> str:
    """Generate a unique trace ID for request tracking."""
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
    """Check if extraction should be retried based on validation/consistency."""
    retry_count = state.get("retry_count", 0)
    trace_id = state.get("trace_id", "unknown")
    
    if retry_count >= MAX_EXTRACTION_RETRIES:
        print(f"[{trace_id}] Max extraction retries ({MAX_EXTRACTION_RETRIES}) reached")
        return False, "max_retries_exceeded"
    
    validation_result = state.get("validation_result") or {}
    if validation_result.get("action") == "retry_extraction":
        print(f"[{trace_id}] Validation requested retry (attempt {retry_count + 1}/{MAX_EXTRACTION_RETRIES})")
        return True, "validation_rejected"
    
    consistency_report = state.get("consistency_report") or {}
    if consistency_report.get("requires_reextraction"):
        print(f"[{trace_id}] Consistency requires re-extraction (score: {consistency_report.get('overall_score')})")
        return True, "consistency_failed"
    
    return False, "no_retry_needed"


def supervisor_router(state: dict) -> Literal["extraction", "analysis", "validation", "__end__"]:
    """Supervisor routing logic - Production Level."""
    extraction_done = state.get("extraction_done", False)
    analysis_done = state.get("analysis_done", False)
    validation_done = state.get("validation_done", False)
    errors = state.get("errors") or []
    trace_id = state.get("trace_id", "unknown")
    
    phase_status = get_phase_status(state)
    retry_count = state.get("retry_count", 0)
    
    print(f"[{trace_id}] Phase Status:")
    print(f"  - Extraction: done={extraction_done}, chars={phase_status['extraction']['characters']}, events={phase_status['extraction']['events']}")
    print(f"  - Analysis: done={analysis_done}, rels={phase_status['analysis']['relationships']}, consistency={phase_status['analysis']['consistency_score']}")
    print(f"  - Validation: done={validation_done}, score={phase_status['validation']['quality_score']}, action={phase_status['validation']['action']}")
    print(f"  - Retries: {retry_count}/{MAX_EXTRACTION_RETRIES}, Errors: {len(errors)}")
    
    if len(errors) > 5:
        print(f"[{trace_id}] -> __end__ (too many errors)")
        return "__end__"
    
    if state.get("force_fail"):
        print(f"[{trace_id}] -> __end__ (force fail / human review needed)")
        return "__end__"
    
    if not extraction_done:
        print(f"[{trace_id}] -> extraction")
        return "extraction"
    
    if not analysis_done:
        print(f"[{trace_id}] -> analysis")
        return "analysis"
    
    if not validation_done:
        print(f"[{trace_id}] -> validation")
        return "validation"
    
    should_retry, reason = should_retry_extraction(state)
    if should_retry:
        print(f"[{trace_id}] -> extraction (retry: {reason})")
        return "extraction"
    elif reason == "max_retries_exceeded":
        print(f"[{trace_id}] -> __end__ (max retries exceeded)")
        return "__end__"
    
    print(f"[{trace_id}] -> __end__ (all done)")
    return "__end__"


async def supervisor_node(state: dict) -> dict:
    """Supervisor Agent node function - Production Level."""
    updates = {}
    
    trace_id = state.get("trace_id")
    if not trace_id:
        trace_id = generate_trace_id()
        updates["trace_id"] = trace_id
        print(f"[{trace_id}] New request started")
    
    next_action = supervisor_router(state)
    
    if next_action == "extraction" and state.get("extraction_done"):
        retry_count = state.get("retry_count", 0) + 1
        updates["retry_count"] = retry_count
        updates["extraction_done"] = False
        print(f"[{trace_id}] Resetting extraction for retry #{retry_count}")
    
    if state.get("force_fail") and next_action == "__end__":
        updates["force_fail_reason"] = "max_retries_exceeded"
    
    supervisor_state = get_supervisor_state({**state, **updates})
    
    updates["messages"] = [{
        "role": "supervisor",
        "content": f"Routing to: {next_action}",
        "trace_id": trace_id,
        "supervisor_state": supervisor_state
    }]
    updates["supervisor_state"] = supervisor_state
    
    return updates


def get_routing_summary(state: dict) -> dict:
    """Get a summary of the current routing state for debugging."""
    return {
        "trace_id": state.get("trace_id", "unknown"),
        "supervisor_state": get_supervisor_state(state),
        "phase_status": get_phase_status(state),
        "next_action": supervisor_router(state)
    }


async def human_review_node(state: dict) -> dict:
    """Human Review node for handling max retries exceeded cases."""
    trace_id = state.get("trace_id", "unknown")
    
    print(f"[{trace_id}] Pipeline requires human review")
    print(f"[{trace_id}] Reason: {state.get('force_fail_reason', 'unknown')}")
    
    return {
        "human_review_required": True,
        "human_review_reason": state.get("force_fail_reason", "max_retries_exceeded"),
        "validation_done": True,
        "messages": [{
            "role": "human_review",
            "content": f"Pipeline requires human intervention. Reason: {state.get('force_fail_reason', 'unknown')}",
            "trace_id": trace_id
        }]
    }
