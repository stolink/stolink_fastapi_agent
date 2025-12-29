"""RabbitMQ consumer for analysis task messages.

Enhanced for production:
- Global Trace ID support for distributed tracing
- Integration with Supervisor graph
- Graceful error handling and recovery
- DB service integration for on-demand queries
"""
import json
import asyncio
import time
import uuid
import structlog
from typing import Callable, Awaitable, Optional

import aio_pika
from aio_pika import IncomingMessage

from pydantic import ValidationError
from app.config import settings
from app.schemas.messages import AnalysisTaskMessage

logger = structlog.get_logger()


class RabbitMQConsumer:
    """Async RabbitMQ consumer for analysis tasks.
    
    Production features:
    - Trace ID propagation for distributed tracing
    - Message acknowledgment strategies
    - Dead letter queue support (TODO)
    - Graceful shutdown handling
    """
    
    def __init__(
        self,
        rabbitmq_url: str = None,
        queue_name: str = None,
        prefetch_count: int = 1
    ):
        """Initialize RabbitMQ consumer.
        
        Args:
            rabbitmq_url: RabbitMQ connection URL
            queue_name: Queue to consume from
            prefetch_count: Number of messages to prefetch (controls concurrency)
        """
        self.rabbitmq_url = rabbitmq_url or settings.rabbitmq_url
        self.queue_name = queue_name or settings.rabbitmq_analysis_queue
        self.prefetch_count = prefetch_count
        self.connection = None
        self.channel = None
        self.queue = None
        self._message_handler: Callable[[AnalysisTaskMessage, str], Awaitable[None]] = None
        self._is_consuming = False
        self._shutdown_event = asyncio.Event()
    
    async def connect(self) -> None:
        """Establish connection to RabbitMQ with retry logic."""
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(
                    "Connecting to RabbitMQ", 
                    url=self.rabbitmq_url.replace(settings.rabbitmq_password, "***"),
                    attempt=attempt + 1
                )
                
                self.connection = await aio_pika.connect_robust(
                    self.rabbitmq_url,
                    timeout=10
                )
                self.channel = await self.connection.channel()
                await self.channel.set_qos(prefetch_count=self.prefetch_count)
                
                # Declare main queue (idempotent)
                self.queue = await self.channel.declare_queue(
                    self.queue_name,
                    durable=True,
                    arguments={
                        # Dead letter exchange for failed messages (TODO: implement DLX)
                        # "x-dead-letter-exchange": "stolink.dlx",
                        # "x-dead-letter-routing-key": "stolink.analysis.failed"
                    }
                )
                
                logger.info("Connected to RabbitMQ", queue=self.queue_name)
                return
                
            except Exception as e:
                logger.error(
                    "Failed to connect to RabbitMQ", 
                    error=str(e), 
                    attempt=attempt + 1
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    raise
    
    async def disconnect(self) -> None:
        """Close RabbitMQ connection gracefully."""
        self._shutdown_event.set()
        
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("Disconnected from RabbitMQ")
    
    def set_message_handler(
        self,
        handler: Callable[[AnalysisTaskMessage, str], Awaitable[None]]
    ) -> None:
        """Set the message handler callback.
        
        Args:
            handler: Async function to handle incoming messages.
                     Signature: (message: AnalysisTaskMessage, trace_id: str) -> None
        """
        self._message_handler = handler
    
    def _generate_trace_id(self) -> str:
        """Generate a new trace ID if not provided."""
        return f"trace-{uuid.uuid4().hex[:12]}"
    
    async def _process_message(self, message: IncomingMessage) -> None:
        """Process incoming RabbitMQ message.
        
        Args:
            message: Incoming AMQP message
        """
        start_time = time.time()
        trace_id = None
        job_id = None
        
        async with message.process(requeue=True):  # Requeue on failure
            try:
                # Parse message body
                body = json.loads(message.body.decode())
                task_message = AnalysisTaskMessage(**body)
                
                # Extract or generate trace ID
                trace_id = task_message.trace_id or self._generate_trace_id()
                job_id = task_message.job_id
                
                # Bind trace ID to logger context
                bound_logger = logger.bind(
                    trace_id=trace_id,
                    job_id=job_id,
                    project_id=task_message.project_id,
                    document_id=task_message.document_id
                )
                
                bound_logger.info(
                    "Received analysis task",
                    content_length=len(task_message.content),
                    has_context=task_message.context is not None
                )
                
                # Log context summary if available
                if task_message.context:
                    ctx = task_message.context
                    bound_logger.info(
                        "Task context",
                        character_refs=len(ctx.existing_characters),
                        event_refs=len(ctx.existing_events),
                        relationship_refs=len(ctx.existing_relationships),
                        chapter=ctx.chapter_number
                    )
                
                # Call handler with trace ID
                if self._message_handler:
                    await self._message_handler(task_message, trace_id)
                else:
                    bound_logger.warning("No message handler set")
                
                # Log completion
                elapsed_ms = int((time.time() - start_time) * 1000)
                bound_logger.info(
                    "Analysis task completed",
                    elapsed_ms=elapsed_ms
                )
                    
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(
                    "Invalid message format",
                    error=str(e),
                    trace_id=trace_id or "unknown"
                )
                # Don't requeue malformed or invalid messages
                
            except Exception as e:
                logger.error(
                    "Failed to process message",
                    error=str(e),
                    error_type=type(e).__name__,
                    job_id=job_id,
                    trace_id=trace_id
                )
                # Message will be requeued due to async with message.process(requeue=True)
                raise  # Re-raise to trigger requeue
    
    async def start_consuming(self) -> None:
        """Start consuming messages from queue."""
        if not self.queue:
            await self.connect()
        
        logger.info("Starting message consumption", queue=self.queue_name)
        
        self._is_consuming = True
        
        # Start consuming with callback
        await self.queue.consume(self._process_message)
    
    async def consume_forever(self) -> None:
        """Start consuming and run until shutdown signal."""
        await self.start_consuming()
        
        # Keep running until shutdown
        try:
            await self._shutdown_event.wait()
        except asyncio.CancelledError:
            logger.info("Consumer cancelled, shutting down")
        finally:
            await self.disconnect()
    
    async def health_check(self) -> dict:
        """Check consumer health status.
        
        Returns:
            Health status dict
        """
        return {
            "connected": self.connection is not None and not self.connection.is_closed,
            "consuming": self._is_consuming,
            "queue": self.queue_name,
            "prefetch_count": self.prefetch_count
        }


# ===== Global Consumer Instance =====

_consumer: Optional[RabbitMQConsumer] = None


def get_consumer() -> RabbitMQConsumer:
    """Get or create consumer singleton."""
    global _consumer
    if _consumer is None:
        _consumer = RabbitMQConsumer()
    return _consumer


async def shutdown_consumer() -> None:
    """Shutdown consumer gracefully."""
    global _consumer
    if _consumer:
        await _consumer.disconnect()
        _consumer = None
