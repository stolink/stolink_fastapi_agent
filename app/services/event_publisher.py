"""Event Publisher for Analysis Events.

분석 완료/실패 이벤트를 RabbitMQ에 발행합니다.
Spring Boot Consumer가 이 이벤트를 수신하여 RDB에 저장합니다.

Event Sourcing 아키텍처:
- AnalysisCompletedEvent → analysis.completed 큐
- AnalysisFailedEvent → analysis.completed 큐 (status로 구분)
- DLQ → analysis.dlq 큐 (실패 시 재처리용)
"""
import json
from datetime import datetime, timedelta
from typing import Optional
import structlog
import aio_pika
from aio_pika import DeliveryMode, Message

from app.config import settings
from app.schemas.event_messages import (
    AnalysisCompletedEvent,
    AnalysisFailedEvent,
    DLQMessage,
)

logger = structlog.get_logger()


class AnalysisEventPublisher:
    """분석 이벤트를 RabbitMQ에 발행하는 Publisher.
    
    Singleton 패턴으로 구현되어 애플리케이션 전역에서 재사용됩니다.
    """
    
    def __init__(self):
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.Channel] = None
        self._exchange: Optional[aio_pika.Exchange] = None
        self._connected = False
    
    async def connect(self) -> None:
        """RabbitMQ 연결 및 Exchange/Queue 선언."""
        if self._connected:
            return
        
        try:
            rabbitmq_url = settings.rabbitmq_url
            logger.info("Connecting to RabbitMQ for event publishing", url=rabbitmq_url.split("@")[-1])
            
            self._connection = await aio_pika.connect_robust(rabbitmq_url)
            self._channel = await self._connection.channel()
            
            # Direct Exchange 선언
            self._exchange = await self._channel.declare_exchange(
                settings.analysis_events_exchange,
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )
            
            # 큐 선언 및 바인딩
            # 1. Analysis Completed Queue (with DLQ routing)
            # Spring Backend와 동일한 DLQ 설정 필요
            completed_queue = await self._channel.declare_queue(
                settings.analysis_completed_queue,
                durable=True,
                arguments={
                    'x-dead-letter-exchange': '',  # 기본 exchange
                    'x-dead-letter-routing-key': settings.analysis_dlq
                }
            )
            await completed_queue.bind(
                self._exchange,
                routing_key="analysis.completed"
            )
            
            # 2. Dead Letter Queue
            dlq = await self._channel.declare_queue(
                settings.analysis_dlq,
                durable=True
            )
            await dlq.bind(
                self._exchange,
                routing_key="analysis.dlq"
            )
            
            self._connected = True
            logger.info(
                "Event Publisher connected",
                exchange=settings.analysis_events_exchange,
                completed_queue=settings.analysis_completed_queue,
                dlq=settings.analysis_dlq
            )
            
        except Exception as e:
            logger.error("Failed to connect Event Publisher", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """연결 종료."""
        if self._connection:
            await self._connection.close()
            self._connected = False
            logger.info("Event Publisher disconnected")
    
    async def publish_completed(self, event: AnalysisCompletedEvent) -> bool:
        """분석 완료 이벤트 발행.
        
        Args:
            event: 분석 완료 이벤트
            
        Returns:
            발행 성공 여부
        """
        if not self._connected:
            await self.connect()
        
        try:
            message = Message(
                body=event.model_dump_json().encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                message_id=event.event_id,
                timestamp=datetime.utcnow(),
                content_type="application/json",
                headers={
                    "event_type": event.event_type,
                    "project_id": event.project_id,
                    "document_id": event.document_id,
                }
            )
            
            await self._exchange.publish(
                message,
                routing_key="analysis.completed"
            )
            
            logger.info(
                "Published ANALYSIS_COMPLETED event",
                event_id=event.event_id,
                document_id=event.document_id,
                project_id=event.project_id
            )
            return True
            
        except Exception as e:
            logger.error(
                "Failed to publish completed event",
                error=str(e),
                event_id=event.event_id
            )
            # DLQ에 발행 시도
            await self._publish_to_dlq(event.model_dump(), str(e))
            return False
    
    async def publish_failed(self, event: AnalysisFailedEvent) -> bool:
        """분석 실패 이벤트 발행.
        
        Args:
            event: 분석 실패 이벤트
            
        Returns:
            발행 성공 여부
        """
        if not self._connected:
            await self.connect()
        
        try:
            message = Message(
                body=event.model_dump_json().encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                message_id=event.event_id,
                timestamp=datetime.utcnow(),
                content_type="application/json",
                headers={
                    "event_type": event.event_type,
                    "project_id": event.project_id,
                    "document_id": event.document_id,
                    "error_code": event.error_code,
                }
            )
            
            await self._exchange.publish(
                message,
                routing_key="analysis.completed"  # 같은 큐로 발행, type으로 구분
            )
            
            logger.info(
                "Published ANALYSIS_FAILED event",
                event_id=event.event_id,
                document_id=event.document_id,
                error_code=event.error_code
            )
            return True
            
        except Exception as e:
            logger.error(
                "Failed to publish failed event",
                error=str(e),
                event_id=event.event_id
            )
            return False
    
    async def _publish_to_dlq(self, original_event: dict, error: str) -> None:
        """실패한 이벤트를 DLQ에 발행.
        
        Args:
            original_event: 원본 이벤트 데이터
            error: 실패 원인
        """
        if not self._connected:
            await self.connect()
        
        try:
            dlq_message = DLQMessage(
                original_event=original_event,
                error=error,
                failed_at=datetime.utcnow(),
                retry_count=0,
                next_retry_at=datetime.utcnow() + timedelta(minutes=5),
                original_event_id=original_event.get("event_id"),
                original_event_type=original_event.get("event_type"),
            )
            
            message = Message(
                body=dlq_message.model_dump_json().encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                timestamp=datetime.utcnow(),
                content_type="application/json",
            )
            
            await self._exchange.publish(
                message,
                routing_key="analysis.dlq"
            )
            
            logger.warning(
                "Event moved to DLQ",
                original_event_id=original_event.get("event_id"),
                error=error
            )
            
        except Exception as dlq_error:
            logger.error(
                "Failed to publish to DLQ",
                error=str(dlq_error),
                original_error=error
            )


# ===== Singleton 인스턴스 관리 =====

_event_publisher: Optional[AnalysisEventPublisher] = None


async def get_event_publisher() -> AnalysisEventPublisher:
    """Event Publisher 싱글톤 인스턴스 반환."""
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = AnalysisEventPublisher()
        await _event_publisher.connect()
    return _event_publisher


async def shutdown_event_publisher() -> None:
    """Event Publisher 종료."""
    global _event_publisher
    if _event_publisher:
        await _event_publisher.disconnect()
        _event_publisher = None
