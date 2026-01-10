"""Event Sourcing message schemas for analysis results.

이벤트 기반 아키텍처를 위한 메시지 스키마:
- AnalysisCompletedEvent: 분석 완료 이벤트 (RabbitMQ 발행)
- AnalysisFailedEvent: 분석 실패 이벤트
- DLQMessage: Dead Letter Queue 메시지

Spring Boot Consumer가 이 이벤트를 수신하여 RDB에 저장합니다.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class AnalysisCompletedEvent(BaseModel):
    """분석 완료 이벤트 - RabbitMQ로 발행됨.
    
    Spring Boot의 Event Consumer가 이 메시지를 수신하여
    RDB에 저장합니다 (Single Source of Truth).
    """
    # 이벤트 메타데이터
    event_type: str = Field(default="ANALYSIS_COMPLETED", description="이벤트 타입")
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Idempotency key - 중복 처리 방지용"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="이벤트 발생 시간 (UTC)"
    )
    
    # 분석 대상 식별자
    project_id: str = Field(..., description="Project UUID")
    document_id: str = Field(..., description="Document UUID")
    job_id: Optional[str] = Field(None, description="Analysis Job UUID (Spring에서 생성)")
    parent_folder_id: Optional[str] = Field(None, description="상위 FOLDER UUID")
    trace_id: Optional[str] = Field(None, description="분산 추적 ID")
    
    # 분석 결과 페이로드
    # sections: AI 백엔드 PostgreSQL에서만 사용, Event Sourcing에서 제외
    
    # Level 2 분석 결과
    # Removed: plot_integration
    consistency_report: Optional[dict] = Field(None, description="일관성 검증 결과")
    validation: Optional[dict] = Field(None, description="검증 결과 (품질 점수, 액션 등)")
    document_summary: Optional[dict] = Field(None, description="문서 요약 (RDB 저장용 - 구조화됨)")
    character_timelines: Optional[list[dict]] = Field(None, description="캐릭터 타임라인 (RDB 저장용 - 구조화됨)")
    
    # 처리 정보
    processing_time_ms: int = Field(default=0, description="처리 시간(ms)")

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "ANALYSIS_COMPLETED",
                "event_id": "evt-12345-abcde",
                "timestamp": "2026-01-07T12:00:00Z",
                "project_id": "proj-uuid",
                "document_id": "doc-uuid",
                "job_id": "job-uuid",
                "characters": [{"name": "서진", "role": "PROTAGONIST"}],
                "events": [{"event_id": "evt-1", "event_type": "BATTLE"}],
                "processing_time_ms": 5000
            }
        }


class AnalysisFailedEvent(BaseModel):
    """분석 실패 이벤트.
    
    분석 파이프라인에서 예외 발생 시 발행됩니다.
    """
    event_type: str = Field(default="ANALYSIS_FAILED", description="이벤트 타입")
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Idempotency key"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="이벤트 발생 시간"
    )
    
    # 분석 대상 식별자
    project_id: str = Field(..., description="Project UUID")
    document_id: str = Field(..., description="Document UUID")
    job_id: Optional[str] = Field(None, description="Analysis Job UUID")
    trace_id: Optional[str] = Field(None, description="분산 추적 ID")
    
    # 에러 정보
    error_code: str = Field(..., description="에러 코드")
    error_message: str = Field(..., description="에러 메시지")
    error_details: Optional[dict] = Field(None, description="추가 에러 상세 정보")
    
    # 처리 정보
    processing_time_ms: int = Field(default=0, description="실패까지 소요 시간(ms)")


class DLQMessage(BaseModel):
    """Dead Letter Queue 메시지.
    
    이벤트 발행/처리 실패 시 DLQ에 저장됩니다.
    재처리 Worker가 이 메시지를 수신하여 재시도합니다.
    """
    original_event: dict = Field(..., description="원본 이벤트 데이터")
    error: str = Field(..., description="실패 원인")
    failed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="실패 시간"
    )
    retry_count: int = Field(default=0, description="재시도 횟수")
    max_retries: int = Field(default=3, description="최대 재시도 횟수")
    next_retry_at: Optional[datetime] = Field(None, description="다음 재시도 시간")
    
    # 원본 메시지 식별
    original_event_id: Optional[str] = Field(None, description="원본 이벤트 ID")
    original_event_type: Optional[str] = Field(None, description="원본 이벤트 타입")

    def should_retry(self) -> bool:
        """재시도 가능 여부 확인"""
        return self.retry_count < self.max_retries
    
    def increment_retry(self):
        """재시도 횟수 증가"""
        self.retry_count += 1
