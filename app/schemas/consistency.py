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
    """Type of consistency conflict."""
    PERSONALITY_CONFLICT = "PERSONALITY_CONFLICT"
    RELATIONSHIP_CONFLICT = "RELATIONSHIP_CONFLICT"
    TIMELINE_CONFLICT = "TIMELINE_CONFLICT"
    STATUS_CONFLICT = "STATUS_CONFLICT"
    PHYSICAL_CONFLICT = "PHYSICAL_CONFLICT"
    SETTING_CONFLICT = "SETTING_CONFLICT"
    CHARACTER_TRAIT_CONFLICT = "CHARACTER_TRAIT_CONFLICT"


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
    existing: Optional[str] = Field(None, description="Existing value")
    new: Optional[str] = Field(None, description="New conflicting value")
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
