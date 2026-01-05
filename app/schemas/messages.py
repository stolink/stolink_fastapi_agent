"""RabbitMQ message schemas for analysis requests.

Updated for hybrid approach:
- Spring Boot sends basic context (counts, identifiers)
- FastAPI can query DB directly for detailed data when needed
"""
from typing import Any, Optional
from pydantic import BaseModel, Field


class ExistingCharacterRef(BaseModel):
    """Reference to existing character (lightweight)."""
    id: str = Field(..., description="Character UUID from PostgreSQL")
    name: str = Field(..., description="Character name for matching")
    role: Optional[str] = Field(None, description="Character role (protagonist, antagonist, etc)")


class ExistingEventRef(BaseModel):
    """Reference to existing event (lightweight)."""
    id: str = Field(..., description="Event UUID from PostgreSQL")
    event_type: str = Field(..., description="Event type")
    summary: str = Field(..., description="Brief summary for context")
    chapter: Optional[int] = Field(None, description="Chapter number")


class ExistingRelationshipRef(BaseModel):
    """Reference to existing relationship from Neo4j (lightweight)."""
    source_name: str = Field(..., description="Source character name")
    target_name: str = Field(..., description="Target character name")
    relation_type: str = Field(..., description="Relationship type")
    strength: int = Field(default=5, ge=1, le=10)


class ExistingSettingRef(BaseModel):
    """Reference to existing setting/location (lightweight)."""
    id: str = Field(..., description="Setting UUID")
    name: str = Field(..., description="Location name")
    location_type: Optional[str] = Field(None, description="Location type")


class AnalysisContext(BaseModel):
    """Context information for analysis.
    
    This contains lightweight references to existing data.
    FastAPI can use these references to query full details from DB when needed.
    """
    # Previous chapter texts (for continuity analysis)
    previous_chapters: list[str] = Field(
        default_factory=list, 
        description="Previous chapter contents for context"
    )
    
    # Current document position
    chapter_number: Optional[int] = Field(None, description="Current chapter number")
    total_chapters: Optional[int] = Field(None, description="Total chapters in project")
    
    # Lightweight references (for matching and quick lookups)
    existing_characters: list[ExistingCharacterRef] = Field(
        default_factory=list,
        description="Existing character references from DB"
    )
    existing_events: list[ExistingEventRef] = Field(
        default_factory=list,
        description="Recent event references from DB"
    )
    existing_relationships: list[ExistingRelationshipRef] = Field(
        default_factory=list,
        description="Existing relationship references from Neo4j"
    )
    existing_settings: list[ExistingSettingRef] = Field(
        default_factory=list,
        description="Existing setting/location references"
    )
    
    # World rules summary (for consistency checking)
    world_rules_summary: Optional[str] = Field(
        None, 
        description="Summary of established world rules"
    )
    
    # Statistics for quick reference
    @property
    def character_count(self) -> int:
        return len(self.existing_characters)
    
    @property
    def event_count(self) -> int:
        return len(self.existing_events)


class AnalysisTaskMessage(BaseModel):
    """RabbitMQ message schema for analysis tasks.
    
    This message is published by Spring Boot when a writer requests
    story analysis from the AI system.
    
    Design: Hybrid approach
    - Spring Boot sends text + lightweight context
    - FastAPI can query DB directly for full details when needed
    """
    # Job identification
    job_id: str = Field(..., description="Unique job identifier")
    project_id: str = Field(..., description="Project UUID")
    document_id: str = Field(..., description="Document UUID being analyzed")
    
    # Story content
    content: str = Field(..., description="Story text content to analyze")
    
    # Context (optional, for enhanced analysis)
    context: Optional[AnalysisContext] = Field(
        default=None, 
        description="Analysis context with existing data references"
    )
    
    # Callback configuration
    callback_url: str = Field(..., description="Spring callback URL for results")
    
    # 🆕 Deep Analysis Flag
    requires_deep_analysis: bool = Field(default=True, description="Whether to run deep analysis (plot, consistency)")
    
    # Tracing
    trace_id: Optional[str] = Field(
        None, 
        description="Global trace ID for distributed tracing"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job-12345",
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_id": "doc-uuid-123",
                "content": "아린은 검을 받아들었다. 카엘이 그녀를 바라보았다.",
                "context": {
                    "previous_chapters": [],
                    "chapter_number": 3,
                    "total_chapters": 10,
                    "existing_characters": [
                        {"id": "char-001", "name": "아린", "role": "protagonist"},
                        {"id": "char-002", "name": "카엘", "role": "supporting"}
                    ],
                    "existing_events": [],
                    "existing_relationships": [
                        {"source_name": "아린", "target_name": "카엘", "relation_type": "ALLY", "strength": 7}
                    ],
                    "existing_settings": [],
                    "world_rules_summary": "마법은 왕국에서 금지됨"
                },
                "callback_url": "http://spring:8080/api/internal/ai/analysis/callback",
                "trace_id": "trace-abc-123"
            }
        }


# ============================================================
# 대용량 문서 분석 아키텍처 (Document Analysis Architecture)
# ============================================================

class DocumentAnalysisMessage(BaseModel):
    """Spring → Python: 문서 분석 요청 메시지.
    
    Claim Check Pattern: content는 DB에서 조회
    """
    message_type: str = Field(default="DOCUMENT_ANALYSIS")
    job_id: Optional[str] = Field(None, alias="jobId", description="Spring AnalysisJob UUID")
    document_id: str = Field(..., description="Document(TEXT) UUID - 분석 대상")
    content: Optional[str] = Field(None, description="Optional content override (useful for testing/dev)")
    project_id: str = Field(..., description="Project UUID")
    parent_folder_id: Optional[str] = Field(None, description="상위 FOLDER UUID")
    chapter_title: Optional[str] = Field(None, description="챕터 제목 (네비게이션용)")
    document_order: Optional[int] = Field(None, description="문서 순서")
    total_documents_in_chapter: Optional[int] = Field(None, description="챕터 내 총 문서 수")
    analysis_pass: int = Field(default=1, description="분석 단계 (1차 Pass, 2차 Pass)")
    requires_deep_analysis: bool = Field(default=False, alias="requiresDeepAnalysis", description="1차 분석 시에도 심층 분석(복선, 플롯, 일관성) 수행 여부")
    callback_url: str = Field(..., description="결과 콜백 URL")
    context: Optional[AnalysisContext] = Field(None, description="기존 데이터 컨텍스트")
    trace_id: Optional[str] = Field(None, description="추적 ID")

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True
        extra = "ignore"  # Allow Spring to send additional fields


class GlobalMergeMessage(BaseModel):
    """Spring → Python: 2차 Pass 글로벌 병합 요청."""
    message_type: str = Field(default="GLOBAL_MERGE")
    project_id: str = Field(..., description="Project UUID")
    callback_url: str = Field(..., description="결과 콜백 URL")
    trace_id: Optional[str] = Field(None, description="추적 ID")


class SectionOutput(BaseModel):
    """Python → Spring: Section 데이터."""
    sequence_order: int = Field(..., description="섹션 순서")
    nav_title: str = Field(..., description="네비게이션 제목")
    content: str = Field(..., description="섹션 내용")
    embedding: Optional[list[float]] = Field(None, description="임베딩 벡터 (1024차원)")
    related_characters: list[str] = Field(default_factory=list, description="관련 캐릭터 이름")
    related_events: list[str] = Field(default_factory=list, description="관련 이벤트 ID")


class DocumentAnalysisCallback(BaseModel):
    """Python → Spring: 문서 분석 결과 콜백."""
    message_type: str = Field(default="DOCUMENT_ANALYSIS_RESULT")
    document_id: str = Field(..., description="분석된 Document UUID")
    parent_folder_id: Optional[str] = Field(None, description="상위 FOLDER UUID")
    status: str = Field(..., description="COMPLETED 또는 FAILED")
    error: Optional[dict] = Field(None, description="에러 정보")
    sections: list[SectionOutput] = Field(default_factory=list, description="생성된 Section 목록")
    characters: list[dict] = Field(default_factory=list, description="추출된 캐릭터")
    events: list[dict] = Field(default_factory=list, description="추출된 이벤트")
    settings: list[dict] = Field(default_factory=list, description="추출된 배경/장소")
    relationships: list[dict] = Field(default_factory=list, description="캐릭터 간 관계")  # 🆕
    # 🆕 Level 2 Analysis Results (Spring 요청)
    plot_integration: Optional[dict] = Field(None, description="플롯 분석 (복선, 서사 아크, 상징)")
    consistency_report: Optional[dict] = Field(None, description="일관성 검증 결과")
    validation: Optional[dict] = Field(None, description="검증 결과 (품질 점수, 액션 등)")
    processing_time_ms: Optional[int] = Field(None, description="처리 시간(ms)")
    trace_id: Optional[str] = Field(None, description="추적 ID")


class CharacterMergeResult(BaseModel):
    """Python → Spring: 캐릭터 병합 결과."""
    primary_id: str = Field(..., description="주 캐릭터 ID")
    merged_ids: list[str] = Field(default_factory=list, description="병합된 캐릭터 ID들")
    canonical_name: str = Field(..., description="표준 이름")
    merged_aliases: list[str] = Field(default_factory=list, description="통합된 별칭")
    confidence: float = Field(..., ge=0, le=1, description="병합 신뢰도 (0-1)")
    conflicts: list[str] = Field(default_factory=list, description="속성 충돌 목록")


class GlobalMergeCallback(BaseModel):
    """Python → Spring: 글로벌 병합 결과 콜백."""
    message_type: str = Field(default="GLOBAL_MERGE_RESULT")
    project_id: str = Field(..., description="Project UUID")
    status: str = Field(..., description="COMPLETED 또는 FAILED")
    error: Optional[dict] = Field(None, description="에러 정보")
    character_merges: list[CharacterMergeResult] = Field(default_factory=list, description="캐릭터 병합 결과")
    consistency_report: Optional[dict] = Field(None, description="일관성 보고서")
    processing_time_ms: Optional[int] = Field(None, description="처리 시간(ms)")
    trace_id: Optional[str] = Field(None, description="추적 ID")

