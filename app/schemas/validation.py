"""Validation result schemas - For Spring Boot compatibility.

Provides final validation status and quality metrics.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ValidationAction(str, Enum):
    """Validation action to take."""
    APPROVE = "approve"
    HUMAN_REVIEW = "human_review"
    REEXTRACT = "reextract"
    REJECT = "reject"


class DataCompleteness(BaseModel):
    """Completeness metrics for each data category."""
    extracted_characters: float = Field(default=100.0, ge=0, le=100)
    extracted_events: float = Field(default=100.0, ge=0, le=100)
    extracted_settings: float = Field(default=100.0, ge=0, le=100)
    extracted_relationships: float = Field(default=100.0, ge=0, le=100)


class ValidationDetails(BaseModel):
    """Detailed validation errors and warnings."""
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Result of validator agent - Spring Boot compatible.
    
    Maps to Spring Boot's ValidationResult entity.
    """
    is_valid: bool = Field(default=True, description="Overall validation status")
    quality_score: float = Field(default=100.0, ge=0, le=100, description="Quality score 0-100")
    action: ValidationAction = Field(default=ValidationAction.APPROVE)
    action_description: str = Field(default="Ready for callback to Spring Boot")
    average_completeness: float = Field(default=100.0, ge=0, le=100)
    error_count: int = Field(default=0)
    warning_count: int = Field(default=0)
    execution_time_ms: float = Field(default=0.0)
    data_completeness: DataCompleteness = Field(default_factory=DataCompleteness)
    validation_details: ValidationDetails = Field(default_factory=ValidationDetails)
