"""Relationship analysis schemas."""
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class RelationType(str, Enum):
    """Relationship type classification."""
    FRIENDLY = "FRIENDLY"
    RIVAL = "RIVAL"
    FAMILY = "FAMILY"
    ROMANTIC = "ROMANTIC"
    MENTOR = "MENTOR"
    SUBORDINATE = "SUBORDINATE"
    BETRAYED = "BETRAYED"
    UNKNOWN = "UNKNOWN"


class RelationshipNode(BaseModel):
    """Graph node representing a character."""
    id: str = Field(..., description="Character unique ID")
    name: str = Field(..., description="Character name")
    properties: dict[str, Any] = Field(default_factory=dict)


class Relationship(BaseModel):
    """Relationship between two characters."""
    source: str = Field(..., description="Source character ID")
    target: str = Field(..., description="Target character ID")
    relation_type: RelationType = Field(..., description="Relationship type")
    strength: int = Field(default=5, ge=1, le=10, description="Relationship strength")
    description: str = Field(default="", description="Relationship description")
    bidirectional: bool = Field(default=True, description="Whether relationship is bidirectional")
    revealed_in_chapter: Optional[int] = None


class RelationshipChange(BaseModel):
    """Tracked change in relationship."""
    source: str
    target: str
    previous_type: Optional[RelationType] = None
    new_type: RelationType
    change_trigger: str = Field(..., description="Event that triggered the change")
    chapter: int


class RelationshipAnalysisResult(BaseModel):
    """Result of relationship analyzer agent."""
    nodes: list[RelationshipNode] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    relationship_changes: list[RelationshipChange] = Field(default_factory=list)
