"""Validator Agent - Level 3.

Final quality gate that validates all agent outputs.
"""
import json


async def validator_node(state: dict) -> dict:
    """Validator Agent node function.
    
    Simple validation without LLM - just checks data quality.
    """
    characters = state.get("extracted_characters", [])
    events = state.get("extracted_events", [])
    errors = state.get("errors", [])
    
    # Calculate quality score
    quality_score = 100
    warnings = []
    
    if not characters:
        quality_score -= 20
        warnings.append("No characters extracted")
    
    if not events:
        quality_score -= 10
        warnings.append("No events extracted")
    
    if errors:
        quality_score -= len(errors) * 5
        warnings.extend(errors)
    
    # Determine action
    if quality_score >= 80:
        action = "approve"
    elif quality_score >= 50:
        action = "human_review"
    else:
        action = "retry_extraction"
    
    return {
        "validation_result": {
            "is_valid": quality_score >= 50,
            "quality_score": max(0, quality_score),
            "action": action,
            "warnings": warnings
        },
        "validation_done": True,
        "messages": state.get("messages", []) + [
            {"role": "validator_agent", "content": f"Score: {quality_score}, Action: {action}"}
        ]
    }
