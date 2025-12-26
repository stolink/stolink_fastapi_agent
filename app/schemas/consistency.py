"""Consistency checker schemas."""
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


class Evidence(BaseModel):
    """Evidence for detected conflict."""
    existing_setting: str = Field(..., description="Existing setting content")
    new_content: str = Field(..., description="New conflicting content")
    chapter_reference: Optional[str] = None


class Conflict(BaseModel):
    """Detected consistency conflict."""
    id: str = Field(..., description="Conflict ID")
    rule_id: str = Field(..., description="Violated rule ID")
    severity: Severity
    conflict_type: ConflictType
    title: str = Field(..., description="Conflict title")
    description: str = Field(..., description="Conflict description")
    affected_characters: list[str] = Field(default_factory=list)
    evidence: Evidence
    suggestions: list[str] = Field(default_factory=list, description="Resolution suggestions")


class Warning(BaseModel):
    """Non-critical warning."""
    id: str
    warning_type: str
    message: str


class ConsistencyReport(BaseModel):
    """Result of consistency checker agent."""
    overall_score: int = Field(default=100, ge=0, le=100, description="Overall consistency score")
    status: str = Field(default="OK", description="OK, WARNING, or ERROR")
    conflicts: list[Conflict] = Field(default_factory=list)
    warnings: list[Warning] = Field(default_factory=list)
    checked_rules: list[str] = Field(default_factory=list, description="Rules that were checked")
