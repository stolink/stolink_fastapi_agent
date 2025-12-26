"""Analysis service that orchestrates the full analysis workflow."""
import structlog
from typing import Any

from app.schemas.messages import AnalysisTaskMessage
from app.agents.graph import run_analysis_pipeline
from app.services.callback_client import get_callback_client

logger = structlog.get_logger()


async def run_analysis(task: AnalysisTaskMessage) -> dict[str, Any]:
    """Run the complete analysis workflow for a task.
    
    1. Execute LangGraph multi-agent pipeline
    2. Compile results
    3. Send callback to Spring Boot
    
    Args:
        task: Analysis task message from RabbitMQ
        
    Returns:
        Final analysis results
    """
    job_id = task.job_id
    callback_client = get_callback_client()
    
    logger.info("Starting analysis", job_id=job_id)
    
    try:
        # Run the LangGraph pipeline
        final_state = await run_analysis_pipeline(
            content=task.content,
            project_id=task.project_id,
            document_id=task.document_id,
            job_id=job_id,
            callback_url=task.callback_url,
            existing_characters=task.context.previous_chapters if task.context else None,
            existing_events=None,
            existing_relationships=None,
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
        
        # Compile result for callback
        result = {
            "characters": final_state.get("extracted_characters", []),
            "events": final_state.get("extracted_events", []),
            "relationships": final_state.get("relationship_graph", {}).get("relationships", []),
            "timeline": [],  # Extracted from events
            "foreshadowing": [],  # Extracted from plot
            "settings": final_state.get("extracted_settings", {}),
            "dialogues": final_state.get("analyzed_dialogues", {}),
            "emotions": final_state.get("tracked_emotions", {}),
            "plot_integration": final_state.get("plot_integration", {}),
            "consistency_report": final_state.get("consistency_report", {}),
            "metadata": {
                "processing_time_ms": final_state.get("processing_time_ms", 0),
                "tokens_used": final_state.get("tokens_used", 0),
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
            error="; ".join(errors) if errors else None
        )
        
        if callback_success:
            logger.info("Analysis completed", job_id=job_id, status=status)
        else:
            logger.error("Callback failed", job_id=job_id)
        
        return result
        
    except Exception as e:
        logger.error("Analysis failed", job_id=job_id, error=str(e))
        
        # Send failure callback
        await callback_client.send_analysis_callback(
            job_id=job_id,
            status="FAILED",
            result=None,
            error=str(e)
        )
        
        raise


async def handle_analysis_message(task: AnalysisTaskMessage) -> None:
    """Message handler for RabbitMQ consumer.
    
    Args:
        task: Analysis task message
    """
    try:
        await run_analysis(task)
    except Exception as e:
        logger.error(
            "Analysis message handling failed",
            job_id=task.job_id,
            error=str(e)
        )
