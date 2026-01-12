"""Analysis service that orchestrates the full analysis workflow.

Updated for hybrid approach:
- Receives context from Spring Boot message
- Can optionally enrich data via DatabaseQueryService
- Supports trace ID for distributed tracing
"""
import asyncio
import time
import structlog
from typing import Any, Optional

from app.schemas.messages import AnalysisTaskMessage, AnalysisContext
from app.agents.graph import run_analysis_pipeline
from app.services.callback_client import get_callback_client
from app.services.db_query_service import get_db_service, DatabaseQueryService
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import get_embedding_service

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
        Initial state dict
    """
    context = task.context
    
    # Base state with minimal context
    state = {
        "content": task.content,
        "project_id": task.project_id,
        "document_id": task.document_id,
        "job_id": task.job_id,
        "callback_url": task.callback_url,
        "analysis_type": getattr(task, 'analysis_type', 'full_manuscript'),  # 🆕 분석 유형
        "existing_characters": [],
        "existing_events": [],
        "existing_relationships": [],
        "existing_settings": [],
        # Add lightweight references if present
        "character_refs": context.existing_characters if context else [],
        "event_refs": context.existing_events if context else [],
    }
    
    return state


async def enrich_state_with_db(
    state: dict[str, Any],
    db_service: DatabaseQueryService
) -> dict[str, Any]:
    """Enrich state with full details from DB if needed.
    
    If message only contained IDs (reference), fetch full objects.
    
    Args:
        state: Initial state dict
        db_service: DB Service instance
        
    Returns:
        Enriched state dict
    """
    project_id = state["project_id"]
    
    # 1. Fetch Characters (if only refs provided)
    if not state["existing_characters"] and state.get("character_refs"):
        # TODO: Implement bulk fetch or use what we have
        # For now, let's assume we might need to fetch all project chars
        # for proper consistency check, but optimized
        full_chars = await db_service.get_all_characters(project_id)
        state["existing_characters"] = full_chars
        
    # 2. Fetch Events (simplified for now)
    if not state["existing_events"]:
        recent_events = await db_service.get_recent_events(project_id, limit=10)
        state["existing_events"] = recent_events

    # 3. Settings
    if not state["existing_settings"]:
        settings_list = await db_service.get_all_settings(project_id)
        state["existing_settings"] = settings_list
        
    return state


async def run_analysis(
    task: AnalysisTaskMessage,
    trace_id: str = "",
    enrich_from_db: bool = False
) -> dict[str, Any]:
    """Run the complete analysis workflow for a task (Parallel Batch Processing).
    
    Updated to match DocumentAnalysisConsumer's logic:
    1. Semantic Chunking
    2. Parallel Batch Execution (with Semaphore)
    3. Result Aggregation
    
    Args:
        task: Analysis task message from RabbitMQ
        trace_id: Global trace ID for distributed tracing
        enrich_from_db: Whether to fetch additional data from DB
        
    Returns:
        Final analysis results
    """
    job_id = task.job_id
    callback_url = task.callback_url
    callback_client = get_callback_client()
    
    # Bind tracing context to logger
    bound_logger = logger.bind(job_id=task.job_id, trace_id=trace_id)
    
    # 🆕 Log content preview (first 200 chars, HTML stripped)
    import re
    content_preview = task.content[:500] if task.content else ""
    # Remove HTML tags for cleaner preview
    content_preview_clean = re.sub(r'<[^>]+>', ' ', content_preview).strip()
    # Remove extra whitespace
    content_preview_clean = re.sub(r'\s+', ' ', content_preview_clean)
    
    bound_logger.info(
        "Starting analysis (Parallel Batch Processing)...",
        content_length=len(task.content) if task.content else 0,
        content_preview=content_preview_clean[:200] + "..." if len(content_preview_clean) > 200 else content_preview_clean
    )
    
    # 0. Content Fetching (Claim Check Pattern)
    if not task.content and task.document_id:
        bound_logger.info("Content missing in message, fetching from DB", doc_id=task.document_id)
        try:
            db_service = await get_db_service()
            fetched_content = await db_service.get_document_content(task.document_id)
            if fetched_content:
                task.content = fetched_content
                bound_logger.info("Content fetched from DB", length=len(task.content))
            else:
                bound_logger.error("Document content not found in DB", doc_id=task.document_id)
                # Fail gracefully or proceed (likely to fail later if content is empty)
                return {
                    "status": "FAILED",
                    "error": f"Content not found for document {task.document_id}",
                    "jobId": task.job_id
                }
        except Exception as e:
            bound_logger.error("Failed to fetch content from DB", error=str(e))
            return {
                "status": "FAILED",
                "error": f"DB fetch failed: {str(e)}",
                "jobId": task.job_id
            }

    # 1. Enrich Initial State from Message (Lightweight Context)
    
    start_time = time.time()
    
    try:
        initial_context = await create_initial_state_from_message(task, trace_id)
        
        if enrich_from_db:
            try:
                db_service = await get_db_service()
                initial_context = await enrich_state_with_db(initial_context, db_service)
            except Exception as e:
                bound_logger.warning("DB enrichment failed, continuing with message context", error=str(e))
        
        # Log context summary
        bound_logger.info(
            "Analysis context",
            character_refs=len(initial_context.get("existing_characters", [])),
            event_refs=len(initial_context.get("existing_events", [])),
            relationship_refs=len(initial_context.get("existing_relationships", [])),
            setting_refs=len(initial_context.get("existing_settings", []))
        )
        
        # 1. Semantic Chunking & Fast Track Check
        FAST_TRACK_LIMIT = 10000
        is_short_text = len(task.content) < FAST_TRACK_LIMIT
        
        sections = []
        
        if is_short_text:
            bound_logger.info("Fast Track: Skipping chunking for short text", length=len(task.content))
            sections = [{"content": task.content, "title": "Full Text"}]
        else:
            bound_logger.info("Generating semantic sections...")
            try:
                emb_service = get_embedding_service()
                chunker = ChunkingService(emb_service)
                sections = await chunker.create_semantic_sections(task.content)
            except Exception as e:
                bound_logger.error("Chunking failed, falling back to full text", error=str(e))
                sections = []

        # Prepare Batches
        batches = []
        if sections:
             # Use semantic sections as batches
             batches = [{"content": sec["content"], "nav_title": sec["title"]} for sec in sections]
        else:
             batches = [{"content": task.content, "nav_title": "Full Text"}]
             
        bound_logger.info(f"Created {len(batches)} batches for parallel analysis")
        
        # Update Status
        await callback_client.update_job_status(
            job_id, 
            "ANALYZING", 
            f"Processing {len(batches)} chapters in parallel"
        )
        
        # 2. Parallel Execution
        # Limit concurrent tasks to avoid overloading LLM API limits
        semaphore = asyncio.Semaphore(5)
        
        async def process_batch(index: int, batch: dict):
            async with semaphore:
                bound_logger.info(f"Processing batch {index+1}/{len(batches)}", size=len(batch["content"]))
                
                try:
                    pipeline_result = await run_analysis_pipeline(
                        content=batch["content"],
                        project_id=task.project_id,
                        document_id=task.document_id,
                        job_id=f"{job_id}-batch-{index}",
                        callback_url="", # No callback for sub-tasks
                        existing_characters=initial_context.get("existing_characters", []),
                        existing_events=initial_context.get("existing_events", []),
                        existing_relationships=initial_context.get("existing_relationships", []),
                        existing_settings=initial_context.get("existing_settings", []),
                        trace_id=trace_id,
                        requires_deep_analysis=task.requires_deep_analysis,
                        is_short_text=is_short_text  # [NEW] Pass Fast Track flag
                    )
                    return pipeline_result
                except Exception as e:
                    bound_logger.error(f"Batch {index+1} failed", error=str(e))
                    return {} # Return empty dict on failure to allow others to proceed

        # Execute Parallel Tasks
        tasks = [process_batch(i, b) for i, b in enumerate(batches)]
        batch_results = await asyncio.gather(*tasks)
        
        # 3. Aggregation (Merge Results)
        final_characters_map = {}
        final_events = []
        final_settings = []
        final_relationships = []
        final_consistency = {}
        final_validation = {} 
        
        for i, res in enumerate(batch_results):
            if not res: continue
            
            # Characters
            chars = res.get("extracted_characters", [])
            for c in chars:
                c_data = c.model_dump() if hasattr(c, 'model_dump') else c
                c_name = c_data.get("name") or c_data.get("profile", {}).get("name")
                if c_name:
                    final_characters_map[c_name] = c_data
            
            # Events
            evts = res.get("extracted_events", [])
            for e in evts:
                e_data = e.model_dump() if hasattr(e, 'model_dump') else e
                e_data["chapter"] = i + 1
                e_data["sequence_order"] = e_data.get("sequence_order", 0) + (i * 100)
                final_events.append(e_data)
                
            # Settings
            stgs = res.get("extracted_settings", [])
            for s in stgs:
                s_data = s.model_dump() if hasattr(s, 'model_dump') else s
                final_settings.append(s_data)
                
            # Relationships
            rel_graph = res.get("relationship_graph", {})
            if rel_graph and isinstance(rel_graph, dict):
                 final_relationships.extend(rel_graph.get("relationships", []))
            
            # Last valid batch results for Consistency (simplified merge strategy)
            if res.get("consistency_report"): final_consistency = res.get("consistency_report")
            if res.get("validation_result"): final_validation = res.get("validation_result")

        # 🆕 Fallback: Extract relationships from character.relations.graph if top-level is empty
        if not final_relationships and final_characters_map:
            bound_logger.info("Extracting relationships from character.relations.graph (fallback)")
            extracted_rels = []
            seen_pairs = set()  # Avoid duplicates
            
            for char_name, char_data in final_characters_map.items():
                # Get relations from either nested format or direct format
                relations_data = char_data.get("relations", {})
                char_relations = []
                
                # Handle dict format: {"graph": [...], "event_refs": [...]}
                if isinstance(relations_data, dict):
                    char_relations = relations_data.get("graph", [])
                # Handle list format (direct list of relations)
                elif isinstance(relations_data, list):
                    char_relations = relations_data
                
                for rel in char_relations:
                    target = rel.get("target", "")
                    if not target:
                        continue
                    
                    # Create pair key for deduplication (sorted for bidirectional)
                    pair_key_fwd = (char_name, target)
                    pair_key_rev = (target, char_name)
                    
                    # Skip if we've already seen this pair (either direction)
                    if pair_key_fwd in seen_pairs:
                        continue
                    
                    # Determine bidirectionality  
                    rel_type = rel.get("type", "NEUTRAL")
                    bidirectional = rel_type not in ("BETRAYED", "MENTOR")  # Unidirectional types
                    
                    # Map embedded format to expected top-level format
                    extracted_rel = {
                        "source": char_name,
                        "target": target,
                        "type": rel_type,
                        "strength": rel.get("strength", 5),
                        "description": rel.get("description", ""),
                        "bidirectional": bidirectional
                    }
                    extracted_rels.append(extracted_rel)
                    seen_pairs.add(pair_key_fwd)
                    
                    # Mark reverse direction as seen if bidirectional
                    if bidirectional:
                        seen_pairs.add(pair_key_rev)
            
            if extracted_rels:
                final_relationships = extracted_rels
                bound_logger.info(f"Extracted {len(final_relationships)} relationships from characters (fallback)")

        # 4. Construct Final Result
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Fallback validation if missing
        if not final_validation:
             final_validation = {"is_valid": True, "action": "approve", "quality_score": 100}

        result_payload = {
            "characters": list(final_characters_map.values()),
            "events": final_events,
            "settings": final_settings,
            "relationships": final_relationships,
            "consistency_report": final_consistency,
            "validation": final_validation,
            "metadata": {
                "processing_time_ms": processing_time_ms,
                "tokens_used": 0,
                "trace_id": trace_id,
                "agents_executed": ["parallel_batch_pipeline"],
                "batch_count": len(batches)
            }
        }
        
        # Update Job Status to COMPLETED
        await callback_client.update_job_status(job_id, "COMPLETED", "Analysis finished successfully")
        
        # Send Callback
        callback_success = await callback_client.send_analysis_callback(
            job_id=job_id,
            status="COMPLETED",
            result=result_payload,
            callback_url=callback_url,
            processing_time_ms=processing_time_ms,
            trace_id=trace_id
        )
        
        if callback_success:
            bound_logger.info("Analysis completed", status="COMPLETED", processing_time_ms=processing_time_ms)
        else:
            bound_logger.error("Callback failed")
        
        return result_payload
        
    except Exception as e:
        bound_logger.error("Analysis failed", error=str(e))
        
        # Update job status to FAILED
        await callback_client.update_job_status(
            job_id=job_id,
            status="FAILED",
            message=str(e)[:200]
        )
        
        # Send failure callback
        await callback_client.send_analysis_callback(
            job_id=job_id,
            status="FAILED",
            result=None,
            error=str(e),
            callback_url=callback_url,
            processing_time_ms=int((time.time() - start_time) * 1000),
            trace_id=trace_id
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
