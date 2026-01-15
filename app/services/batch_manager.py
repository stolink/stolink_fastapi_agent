"""Batch Manager for document ordering.

Ensures documents in a batch are processed in document_order sequence.
- Collects all documents until total_documents reached
- Timeout with retry request to Spring
- No partial processing - all or nothing
"""
import asyncio
import json
import time
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass, field

import structlog
import redis.asyncio as redis_async

from app.config import settings
from app.schemas.messages import DocumentAnalysisMessage

logger = structlog.get_logger()


@dataclass
class BatchStatus:
    """Status of a document batch."""
    batch_id: str
    project_id: str
    total_documents: int
    timeout_seconds: int
    received_documents: dict = field(default_factory=dict)  # {document_order: message}
    created_at: float = field(default_factory=time.time)
    
    @property
    def is_complete(self) -> bool:
        return len(self.received_documents) >= self.total_documents
    
    @property
    def missing_orders(self) -> list[int]:
        expected = set(range(1, self.total_documents + 1))
        received = set(self.received_documents.keys())
        return sorted(expected - received)
    
    @property
    def is_timed_out(self) -> bool:
        return (time.time() - self.created_at) > self.timeout_seconds
    
    def get_ordered_messages(self) -> list[DocumentAnalysisMessage]:
        """Get messages in document_order sequence."""
        return [self.received_documents[i] for i in sorted(self.received_documents.keys())]


class BatchManager:
    """Manages document batches for ordered processing.
    
    Flow:
    1. Message arrives with batch_id, total_documents, document_order
    2. Store in Redis until all documents arrive
    3. On complete: trigger processing in order
    4. On timeout: notify Spring for retry, cancel batch on failure
    """
    
    BATCH_PREFIX = "stolink:batch:"
    BATCH_TTL = 3600  # 1 hour max batch lifetime
    
    def __init__(self):
        self._redis: Optional[redis_async.Redis] = None
        self._initialized = False
        self._processing_callback: Optional[Callable[[DocumentAnalysisMessage], Awaitable[None]]] = None
        self._timeout_tasks: dict[str, asyncio.Task] = {}  # batch_id -> timeout task
    
    async def initialize(self) -> bool:
        """Initialize Redis connection."""
        if self._initialized:
            return True
        
        try:
            self._redis = redis_async.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5
            )
            await self._redis.ping()
            self._initialized = True
            logger.info("BatchManager initialized")
            return True
        except Exception as e:
            logger.warning("Redis unavailable for batch management", error=str(e))
            self._redis = None
            return False
    
    async def close(self):
        """Close Redis connection and cancel timeout tasks."""
        for task in self._timeout_tasks.values():
            task.cancel()
        self._timeout_tasks.clear()
        
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._initialized = False
    
    def set_processing_callback(self, callback: Callable[[DocumentAnalysisMessage], Awaitable[None]]):
        """Set callback for processing documents when batch is complete."""
        self._processing_callback = callback
    
    async def add_document(self, msg: DocumentAnalysisMessage) -> bool:
        """Add document to batch. Returns True if batch is now complete.
        
        If batch_id is None, returns True immediately (non-batch mode).
        """
        # Non-batch mode: process immediately
        if not msg.batch_id or not msg.total_documents:
            return True
        
        if not self._redis:
            logger.warning("Redis unavailable, processing without batch ordering")
            return True
        
        batch_key = f"{self.BATCH_PREFIX}{msg.batch_id}"
        doc_order = msg.document_order or 1
        
        try:
            # Store document in batch hash
            await self._redis.hset(
                batch_key,
                str(doc_order),
                msg.model_dump_json()
            )
            
            # Set batch metadata if first document
            meta_key = f"{batch_key}:meta"
            if not await self._redis.exists(meta_key):
                await self._redis.hset(meta_key, mapping={
                    "project_id": msg.project_id,
                    "total_documents": msg.total_documents,
                    "timeout_seconds": msg.batch_timeout_seconds,
                    "created_at": str(time.time())
                })
                await self._redis.expire(meta_key, self.BATCH_TTL)
                await self._redis.expire(batch_key, self.BATCH_TTL)
                
                # Start timeout watcher
                self._start_timeout_watcher(msg.batch_id, msg.batch_timeout_seconds)
            
            # Check if complete
            received_count = await self._redis.hlen(batch_key)
            logger.info(
                "Document added to batch",
                batch_id=msg.batch_id,
                document_order=doc_order,
                received=received_count,
                total=msg.total_documents
            )
            
            if received_count >= msg.total_documents:
                # Cancel timeout watcher
                self._cancel_timeout_watcher(msg.batch_id)
                
                # Process all in order
                await self._process_complete_batch(msg.batch_id)
                return True
            
            return False  # Not complete yet, don't process this message
            
        except Exception as e:
            logger.error("Failed to add document to batch", error=str(e), batch_id=msg.batch_id)
            return True  # Fallback to immediate processing
    
    def _start_timeout_watcher(self, batch_id: str, timeout_seconds: int):
        """Start background task to watch for batch timeout."""
        if batch_id in self._timeout_tasks:
            return
        
        async def timeout_handler():
            await asyncio.sleep(timeout_seconds)
            await self._handle_batch_timeout(batch_id)
        
        task = asyncio.create_task(timeout_handler())
        self._timeout_tasks[batch_id] = task
        logger.info("Started timeout watcher", batch_id=batch_id, timeout=timeout_seconds)
    
    def _cancel_timeout_watcher(self, batch_id: str):
        """Cancel timeout watcher for batch."""
        if batch_id in self._timeout_tasks:
            self._timeout_tasks[batch_id].cancel()
            del self._timeout_tasks[batch_id]
            logger.info("Cancelled timeout watcher", batch_id=batch_id)
    
    async def _handle_batch_timeout(self, batch_id: str):
        """Handle batch timeout - request retry from Spring."""
        batch_key = f"{self.BATCH_PREFIX}{batch_id}"
        meta_key = f"{batch_key}:meta"
        
        try:
            # Get batch metadata
            meta = await self._redis.hgetall(meta_key)
            if not meta:
                return
            
            total = int(meta.get("total_documents", 0))
            project_id = meta.get("project_id", "")
            
            # Get received documents
            received = await self._redis.hkeys(batch_key)
            received_orders = [int(o) for o in received]
            
            # Calculate missing
            expected = set(range(1, total + 1))
            missing = sorted(expected - set(received_orders))
            
            logger.warning(
                "Batch timeout - requesting retry from Spring",
                batch_id=batch_id,
                project_id=project_id,
                received=received_orders,
                missing=missing
            )
            
            # Request retry from Spring
            await self._request_retry_from_spring(batch_id, project_id, missing)
            
            # Clean up batch
            await self._cleanup_batch(batch_id)
            
        except Exception as e:
            logger.error("Failed to handle batch timeout", error=str(e), batch_id=batch_id)
    
    async def _request_retry_from_spring(self, batch_id: str, project_id: str, missing_orders: list[int]):
        """Request Spring to resend missing documents or cancel batch."""
        import httpx
        
        callback_url = f"{settings.spring_backend_url}/api/internal/ai/batch/retry"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(callback_url, json={
                    "batch_id": batch_id,
                    "project_id": project_id,
                    "missing_document_orders": missing_orders,
                    "action": "RETRY_OR_CANCEL"
                })
                
                if response.status_code == 200:
                    logger.info("Retry request sent to Spring", batch_id=batch_id)
                else:
                    logger.warning("Spring retry request failed", status=response.status_code)
                    
        except Exception as e:
            logger.error("Failed to request retry from Spring", error=str(e))
    
    async def _process_complete_batch(self, batch_id: str):
        """Process all documents in batch in order."""
        if not self._processing_callback:
            logger.error("No processing callback set")
            return
        
        batch_key = f"{self.BATCH_PREFIX}{batch_id}"
        
        try:
            # Get all documents
            docs = await self._redis.hgetall(batch_key)
            
            # Sort by document_order and process
            sorted_orders = sorted([int(k) for k in docs.keys()])
            
            logger.info(
                "Processing complete batch in order",
                batch_id=batch_id,
                order=sorted_orders
            )
            
            for order in sorted_orders:
                doc_json = docs[str(order)]
                msg = DocumentAnalysisMessage.model_validate_json(doc_json)
                
                logger.info(f"Processing batch document {order}/{len(sorted_orders)}", 
                           batch_id=batch_id, document_id=msg.document_id)
                
                # Process document (this should use the existing consumer logic)
                await self._processing_callback(msg)
            
            # Clean up
            await self._cleanup_batch(batch_id)
            
        except Exception as e:
            logger.error("Failed to process complete batch", error=str(e), batch_id=batch_id)
    
    async def _cleanup_batch(self, batch_id: str):
        """Clean up batch data from Redis."""
        batch_key = f"{self.BATCH_PREFIX}{batch_id}"
        meta_key = f"{batch_key}:meta"
        
        self._cancel_timeout_watcher(batch_id)
        
        await self._redis.delete(batch_key, meta_key)
        logger.info("Batch cleaned up", batch_id=batch_id)


# Singleton instance
_batch_manager: Optional[BatchManager] = None


async def get_batch_manager() -> BatchManager:
    """Get or create batch manager singleton."""
    global _batch_manager
    if _batch_manager is None:
        _batch_manager = BatchManager()
        await _batch_manager.initialize()
    return _batch_manager
