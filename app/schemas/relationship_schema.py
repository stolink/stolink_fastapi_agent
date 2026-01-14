"""Pydantic schemas for relationship extraction with structured output.

This module defines type-safe schemas for character relationships,
ensuring LLM outputs are always valid JSON with correct field types.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class RelationshipItem(BaseModel):
    """Single relationship between two characters.
    
    This schema enforces type safety and field validation,
    eliminating JSON parsing errors.
    """
    source: str = Field(
        ..., 
        description="Source character name (EXACT name from available characters list)"
    )
    target: str = Field(
        ..., 
        description="Target character name (EXACT name from available characters list)"
    )
    relation_type: str = Field(
        ..., 
        description="Relationship type: ALLY, ENEMY, RIVAL, NEUTRAL, FRIENDLY, FAMILY, ROMANTIC, MENTOR, or BETRAYED"
    )
    strength: int = Field(
        ..., 
        ge=1, 
        le=10, 
        description="Relationship strength/intensity from 1 (weak) to 10 (very strong)"
    )
    description: str = Field(
        ..., 
        description="Brief description of the relationship in the same language as input text"
    )
    bidirectional: bool = Field(
        default=True, 
        description="Is this relationship bidirectional? Set to False for BETRAYED and MENTOR types"
    )
    evolved_from: Optional[str] = Field(
        default=None, 
        description="Previous relationship type if this relationship has changed (e.g., FRIENDLY -> BETRAYED)"
    )
    conflict_resolution: Optional[str] = Field(
        default=None,
        description="Explanation of how conflicts were resolved (only used during re-analysis)"
    )


class RelationshipExtractionResult(BaseModel):
    """Complete relationship extraction result with guaranteed valid structure.
    
    Using this schema with structured LLM output eliminates:
    - JSON parsing errors
    - Invalid field types
    - Missing required fields
    - Malformed JSON strings
    """
    relationships: List[RelationshipItem] = Field(
        default_factory=list,
        description="List of all character relationships found in the text"
    )
