"""Analysis service that orchestrates the full analysis workflow.

Updated for hybrid approach:
- Receives context from Spring Boot message
- Can optionally enrich data via DatabaseQueryService
- Supports trace ID for distributed tracing
"""
import structlog
from typing import Any, Optional

from app.schemas.messages import AnalysisTaskMessage, AnalysisContext
from app.agents.graph import run_analysis_pipeline
from app.services.callback_client import get_callback_client
from app.services.db_query_service import get_db_service, DatabaseQueryService

logger = structlog.get_logger()


async def create_initial_state_from_message(
    task: AnalysisTaskMessage,
    trace_id: str
) -> dict[str, Any]:
    """Create initial state dict from RabbitMQ message.
    
    Converts the lightweight context references from Spring Boot
    into the format expected by the LangGraph state.
    
    Args:
        task: Analysis task message
        trace_id: Global trace ID
        
    Returns:
        Initial state dictionary for LangGraph
    """
    state = {
        "content": task.content,
        "project_id": task.project_id,
        "document_id": task.document_id,
        "job_id": task.job_id,
        "callback_url": task.callback_url,
        "trace_id": trace_id,
    }
    
    # Add context if available
    if task.context:
        ctx = task.context
        state["chapter_number"] = ctx.chapter_number
        state["total_chapters"] = ctx.total_chapters
        state["world_rules_summary"] = ctx.world_rules_summary
        
        # Convert references to dicts
        state["existing_characters"] = [
            char.model_dump() for char in ctx.existing_characters
        ]
        state["existing_events"] = [
            event.model_dump() for event in ctx.existing_events
        ]
        state["existing_relationships"] = [
            rel.model_dump() for rel in ctx.existing_relationships
        ]
        state["existing_settings"] = [
            setting.model_dump() for setting in ctx.existing_settings
        ]
    
    return state


async def enrich_state_with_db(
    state: dict[str, Any],
    db_service: DatabaseQueryService
) -> dict[str, Any]:
    """Optionally enrich state with additional data from DB.
    
    This is called when the context from Spring Boot is insufficient
    and agents need more detailed data.
    
    Args:
        state: Current state dict
        db_service: Database query service
        
    Returns:
        Enriched state dict
    """
    project_id = state["project_id"]
    
    # If no existing characters provided, fetch from DB
    if not state.get("existing_characters"):
        characters = await db_service.get_all_characters(project_id)
        state["existing_characters"] = characters
        logger.info("Enriched state with DB characters", count=len(characters))
    
    # If no existing settings provided, fetch from DB
    if not state.get("existing_settings"):
        settings = await db_service.get_all_settings(project_id)
        state["existing_settings"] = settings
        logger.info("Enriched state with DB settings", count=len(settings))
    
    # If no existing relationships provided, fetch from Neo4j
    if not state.get("existing_relationships"):
        relationships = await db_service.get_all_relationships(project_id)
        state["existing_relationships"] = relationships
        logger.info("Enriched state with Neo4j relationships", count=len(relationships))
    
    return state


async def run_analysis(
    task: AnalysisTaskMessage,
    trace_id: str = "",
    enrich_from_db: bool = False
) -> dict[str, Any]:
    """Run the complete analysis workflow for a task.
    
    1. Create initial state from message
    2. Optionally enrich with DB data
    3. Execute LangGraph multi-agent pipeline
    4. Compile results
    5. Send callback to Spring Boot
    
    Args:
        task: Analysis task message from RabbitMQ
        trace_id: Global trace ID for distributed tracing
        enrich_from_db: Whether to fetch additional data from DB
        
    Returns:
        Final analysis results
    """
    job_id = task.job_id
    callback_url = task.callback_url  # Get callback URL from message
    callback_client = get_callback_client()
    
    # Bind tracing context to logger
    bound_logger = logger.bind(job_id=job_id, trace_id=trace_id)
    bound_logger.info("Starting analysis")
    
    try:
        # Create initial state from message
        initial_state = await create_initial_state_from_message(task, trace_id)
        
        # Optionally enrich with DB data
        if enrich_from_db:
            try:
                db_service = await get_db_service()
                initial_state = await enrich_state_with_db(initial_state, db_service)
            except Exception as e:
                bound_logger.warning("DB enrichment failed, continuing with message context", error=str(e))
        
        # Log context summary
        bound_logger.info(
            "Analysis context",
            character_refs=len(initial_state.get("existing_characters", [])),
            event_refs=len(initial_state.get("existing_events", [])),
            relationship_refs=len(initial_state.get("existing_relationships", [])),
            setting_refs=len(initial_state.get("existing_settings", []))
        )
        
        # Run the LangGraph pipeline
        final_state = await run_analysis_pipeline(
            content=initial_state["content"],
            project_id=initial_state["project_id"],
            document_id=initial_state["document_id"],
            job_id=job_id,
            callback_url=initial_state["callback_url"],
            existing_characters=initial_state.get("existing_characters"),
            existing_events=initial_state.get("existing_events"),
            existing_relationships=initial_state.get("existing_relationships"),
            trace_id=trace_id,
        )
        
        # Determine status based on validation result
        validation = final_state.get("validation_result", {})
        errors = final_state.get("errors", [])
        
        if errors:
            status = "WARNING"
        elif validation.get("action") == "approve":
            status = "COMPLETED"
        elif validation.get("action") == "human_review":
            status = "WARNING"
        else:
            status = "COMPLETED"
        
        # Compile result for callback - matches Spring Boot FullAnalysisResult
        result = {
            # Level 1 Extraction Results
            "characters": final_state.get("extracted_characters", []),
            "events": final_state.get("extracted_events", []),
            "settings": final_state.get("extracted_settings", []),  # List, not dict
            "relationships": final_state.get("relationship_graph", {}).get("relationships", []),
            
            # Level 1 Analysis Results
            "dialogues": final_state.get("analyzed_dialogues", {}),
            "emotions": final_state.get("tracked_emotions", {}),
            
            # Level 2 Analysis Results
            "plot_integration": final_state.get("plot_integration", {}),
            "consistency_report": final_state.get("consistency_report", {}),
            "validation": validation,
            
            # Metadata
            "metadata": {
                "processing_time_ms": final_state.get("processing_time_ms", 0),
                "tokens_used": final_state.get("tokens_used", 0),
                "trace_id": trace_id,
                "agents_executed": [
                    "character", "event", "setting", "dialogue", "emotion",
                    "relationship", "consistency", "plot", "validator"
                ]
            }
        }
        
        # Send callback
        callback_success = await callback_client.send_analysis_callback(
            job_id=job_id,
            status=status,
            result=result,
            error="; ".join(errors) if errors else None,
            callback_url=callback_url  # Pass callback URL from message
        )
        
        if callback_success:
            bound_logger.info("Analysis completed", status=status)
        else:
            bound_logger.error("Callback failed")
        
        return result
        
    except Exception as e:
        bound_logger.error("Analysis failed", error=str(e))
        
        # Send failure callback
        await callback_client.send_analysis_callback(
            job_id=job_id,
            status="FAILED",
            result=None,
            error=str(e),
            callback_url=callback_url  # Pass callback URL from message
        )
        
        raise


async def handle_analysis_message(
    task: AnalysisTaskMessage,
    trace_id: str = ""
) -> None:
    """Message handler for RabbitMQ consumer.
    
    Args:
        task: Analysis task message
        trace_id: Global trace ID
    """
    # Bind trace context
    bound_logger = logger.bind(job_id=task.job_id, trace_id=trace_id)
    
    try:
        # Determine if we need to enrich from DB
        # If context has no existing data, we may want to fetch from DB
        needs_enrichment = False
        if task.context:
            needs_enrichment = (
                not task.context.existing_characters and
                not task.context.existing_events
            )
        
        await run_analysis(
            task=task,
            trace_id=trace_id,
            enrich_from_db=needs_enrichment
        )
    except Exception as e:
        bound_logger.error(
            "Analysis message handling failed",
            error=str(e)
        )
