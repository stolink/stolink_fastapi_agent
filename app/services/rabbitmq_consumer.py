"""RabbitMQ consumer for analysis task messages."""
import json
import asyncio
import structlog
from typing import Callable, Awaitable

import aio_pika
from aio_pika import IncomingMessage

from app.config import settings
from app.schemas.messages import AnalysisTaskMessage

logger = structlog.get_logger()


class RabbitMQConsumer:
    """Async RabbitMQ consumer for analysis tasks."""
    
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
            prefetch_count: Number of messages to prefetch
        """
        self.rabbitmq_url = rabbitmq_url or settings.rabbitmq_url
        self.queue_name = queue_name or settings.rabbitmq_analysis_queue
        self.prefetch_count = prefetch_count
        self.connection = None
        self.channel = None
        self.queue = None
        self._message_handler: Callable[[AnalysisTaskMessage], Awaitable[None]] = None
    
    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        logger.info("Connecting to RabbitMQ", url=self.rabbitmq_url)
        
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=self.prefetch_count)
        
        # Declare queue (idempotent)
        self.queue = await self.channel.declare_queue(
            self.queue_name,
            durable=True
        )
        
        logger.info("Connected to RabbitMQ", queue=self.queue_name)
    
    async def disconnect(self) -> None:
        """Close RabbitMQ connection."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("Disconnected from RabbitMQ")
    
    def set_message_handler(
        self,
        handler: Callable[[AnalysisTaskMessage], Awaitable[None]]
    ) -> None:
        """Set the message handler callback.
        
        Args:
            handler: Async function to handle incoming messages
        """
        self._message_handler = handler
    
    async def _process_message(self, message: IncomingMessage) -> None:
        """Process incoming RabbitMQ message.
        
        Args:
            message: Incoming AMQP message
        """
        async with message.process():
            try:
                # Parse message body
                body = json.loads(message.body.decode())
                task_message = AnalysisTaskMessage(**body)
                
                logger.info(
                    "Received analysis task",
                    job_id=task_message.job_id,
                    project_id=task_message.project_id,
                    document_id=task_message.document_id
                )
                
                # Call handler
                if self._message_handler:
                    await self._message_handler(task_message)
                else:
                    logger.warning("No message handler set")
                    
            except json.JSONDecodeError as e:
                logger.error("Failed to parse message", error=str(e))
            except Exception as e:
                logger.error("Failed to process message", error=str(e))
    
    async def start_consuming(self) -> None:
        """Start consuming messages from queue."""
        if not self.queue:
            await self.connect()
        
        logger.info("Starting message consumption", queue=self.queue_name)
        
        # Start consuming
        await self.queue.consume(self._process_message)
    
    async def consume_forever(self) -> None:
        """Start consuming and run forever."""
        await self.start_consuming()
        
        # Keep running
        try:
            await asyncio.Future()  # Run forever
        except asyncio.CancelledError:
            await self.disconnect()


# Global consumer instance
_consumer = None


def get_consumer() -> RabbitMQConsumer:
    """Get or create consumer singleton."""
    global _consumer
    if _consumer is None:
        _consumer = RabbitMQConsumer()
    return _consumer
