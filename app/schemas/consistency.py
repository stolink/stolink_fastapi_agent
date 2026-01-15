"""Consistency checker schemas - Updated for Spring Boot compatibility.

Provides:
- Conflict detection and classification
- Resolution suggestions
- Neo4j validation status
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Conflict severity level."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ConflictType(str, Enum):
    """Type of consistency conflict - 15 narrative inconsistency categories."""
    # === Original Types (1-6) ===
    CHARACTER_TRAIT_CONFLICT = "CHARACTER_TRAIT_CONFLICT"      # 1. 성격/행동/능력치 모순
    RELATIONSHIP_CONFLICT = "RELATIONSHIP_CONFLICT"            # 2. 관계 급변, 신뢰도 부조화
    TIMELINE_CONFLICT = "TIMELINE_CONFLICT"                    # 3. 인과관계, 선후관계 오류
    SETTING_CONFLICT = "SETTING_CONFLICT"                      # 4. 세계관/지리/시대착오
    INVENTORY_CONFLICT = "INVENTORY_CONFLICT"                  # 5. 아이템 미사용/방치
    STATS_CONFLICT = "STATS_CONFLICT"                          # 6. 능력치 스케일링 문제
    
    # === Extended Types (7-15) ===
    CONSEQUENCE_MISSING = "CONSEQUENCE_MISSING"                # 7. 후폭풍/반작용 부재 (공권력, 신체 손상, 경제)
    INFORMATION_LOGIC_ERROR = "INFORMATION_LOGIC_ERROR"        # 8. 정보 비대칭성/전달 오류 (전지적 캐릭터, 설명조 대화)
    PROBABILITY_BIAS = "PROBABILITY_BIAS"                      # 9. 확률 편향/과도한 행운 (주인공 보정, 우연의 연속)
    POWER_BALANCE_ERROR = "POWER_BALANCE_ERROR"                # 10. 파워 밸런스/상성 무시
    POV_VIOLATION = "POV_VIOLATION"                            # 11. 서술 시점 위반
    SELECTIVE_INCOMPETENCE = "SELECTIVE_INCOMPETENCE"          # 12. 선택적 무능/건망증 (능력/아이템 미사용)
    LOGISTICS_ERROR = "LOGISTICS_ERROR"                        # 13. 병참/보급/경제 오류
    EMOTIONAL_CONTINUITY_ERROR = "EMOTIONAL_CONTINUITY_ERROR"  # 14. 감정 지속성 오류 (트라우마 증발)
    SOCIAL_PROTOCOL_VIOLATION = "SOCIAL_PROTOCOL_VIOLATION"    # 15. 사회적 신분/예법 파괴
    
    # === Legacy/Alias Types ===
    PERSONALITY_CONFLICT = "PERSONALITY_CONFLICT"              # Alias for CHARACTER_TRAIT_CONFLICT
    STATUS_CONFLICT = "STATUS_CONFLICT"                        # Alias for CHARACTER_TRAIT_CONFLICT
    PHYSICAL_CONFLICT = "PHYSICAL_CONFLICT"                    # Alias for SETTING_CONFLICT
    CROSS_CHAPTER_CONFLICT = "CROSS_CHAPTER_CONFLICT"          # Cross-chapter validation


class SuggestedAction(str, Enum):
    """Suggested action for conflict resolution."""
    AUTO_FIX = "AUTO_FIX"
    FLAG_FOR_HUMAN = "FLAG_FOR_HUMAN"
    IGNORE = "IGNORE"
    REEXTRACT = "REEXTRACT"


class Conflict(BaseModel):
    """Detected consistency conflict - Spring Boot compatible."""
    type: ConflictType = Field(..., description="Conflict type")
    severity: Severity = Field(default=Severity.MEDIUM)
    source: str = Field(default="extracted", description="Source of conflict")
    existing: Optional[str | list[str]] = Field(None, description="Existing value")
    new: Optional[str | list[str]] = Field(None, description="New conflicting value")
    character: Optional[str] = Field(None, description="Affected character name")
    description: str = Field(default="", description="Conflict description")
    suggested_action: SuggestedAction = Field(default=SuggestedAction.FLAG_FOR_HUMAN)


class ResolutionSummary(BaseModel):
    """Summary of conflict resolutions."""
    auto_fixable: int = Field(default=0)
    ready_for_update: int = Field(default=0)
    needs_human_review: int = Field(default=0)
    total_conflicts: int = Field(default=0)


class Neo4jValidation(BaseModel):
    """Neo4j graph validation status."""
    is_valid: bool = Field(default=True)
    conflict_count: int = Field(default=0)
    high_severity_count: int = Field(default=0)


class ConsistencyReport(BaseModel):
    """Result of consistency checker agent - Spring Boot compatible.
    
    Maps to Spring Boot's ConsistencyReport entity.
    """
    overall_score: int = Field(default=100, ge=0, le=100, description="Overall consistency score")
    requires_reextraction: bool = Field(default=False, description="Whether re-extraction is needed")
    conflicts: list[Conflict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
    resolution_summary: ResolutionSummary = Field(default_factory=ResolutionSummary)
    neo4j_validation: Neo4jValidation = Field(default_factory=Neo4jValidation)
