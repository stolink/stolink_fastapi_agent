"""Validator Agent - Level 3 (Production Level).

Role: "Quality Assurance Gate" / "Final Pipeline Validator"
- Validates ALL agent outputs before callback to Spring Boot
- Checks for required data completeness
- Validates referential integrity across agents
- Generates final quality score and action recommendation
- Provides structured validation summary for debugging
- Includes execution time metrics for performance monitoring

Validates outputs from:
- Character Agent: extracted_characters
- Event Agent: extracted_events
- Setting Agent: extracted_settings
- Relationship Agent: relationship_graph
- Consistency Agent: consistency_report
- Plot Agent: plot
"""
import json
import time


# Error codes for structured error reporting
class ValidationErrorCode:
    MISSING_REQUIRED = "VAL_001"
    EMPTY_DATA = "VAL_002"
    MISSING_FIELD = "VAL_003"
    INVALID_TYPE = "VAL_004"
    REF_INTEGRITY = "VAL_005"
    CONSISTENCY_FAIL = "VAL_006"


# Validation rules for each agent output
VALIDATION_RULES = {
    "extracted_characters": {
        "required": True,
        "min_count": 1,
        "penalty_missing": 20,
        "penalty_empty": 15,
        "required_fields": ["profile.name", "role"],  # Support nested paths
        "nested_paths": True
    },
    "extracted_events": {
        "required": True,
        "min_count": 1,
        "penalty_missing": 15,
        "penalty_empty": 10,
        "required_fields": ["event_id", "description"]
    },
    "extracted_settings": {
        "required": False,
        "penalty_missing": 5,
        "required_fields": ["location_name"]
    },
    "relationship_graph": {
        "required": False,
        "penalty_missing": 10,
        "required_fields": ["relationships"]
    },
    "consistency_report": {
        "required": True,
        "penalty_missing": 15,
        "required_fields": ["overall_score"]
    },
    "plot": {
        "required": False,
        "penalty_missing": 5,
        "required_fields": []
    }
}


def create_validation_error(field: str, code: str, message: str, value=None) -> dict:
    """Create a structured validation error object."""
    error = {
        "field": field,
        "code": code,
        "message": message
    }
    if value is not None:
        error["value"] = str(value)[:100]  # Limit value length
    return error


def get_nested_value(data: dict, path: str):
    """Get value from nested dict using dot notation (e.g., 'profile.name')."""
    keys = path.split(".")
    value = data
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    return value


def validate_required_fields(data: dict | list, fields: list, source: str, nested_paths: bool = False) -> list:
    """Check if required fields exist in data. Returns structured errors.
    
    Args:
        data: Data to validate (dict or list)
        fields: Required field names (can include dot notation like 'profile.name')
        source: Source name for error messages
        nested_paths: If True, support dot notation for nested fields
    """
    errors = []
    if isinstance(data, list):
        for idx, item in enumerate(data):
            for field in fields:
                if nested_paths and "." in field:
                    value = get_nested_value(item, field)
                else:
                    value = item.get(field)
                
                if not value:
                    errors.append(create_validation_error(
                        field=f"{source}[{idx}].{field}",
                        code=ValidationErrorCode.MISSING_FIELD,
                        message=f"Required field '{field}' is missing",
                        value=value
                    ))
    elif isinstance(data, dict):
        for field in fields:
            if nested_paths and "." in field:
                value = get_nested_value(data, field)
            else:
                value = data.get(field)
            
            if value is None:
                errors.append(create_validation_error(
                    field=f"{source}.{field}",
                    code=ValidationErrorCode.MISSING_FIELD,
                    message=f"Required field '{field}' is missing"
                ))
    return errors[:5]


def validate_referential_integrity(state: dict) -> list:
    """Validate that relationships reference valid characters. Returns structured errors."""
    errors = []
    
    # Support both legacy (c["name"]) and FullCharacter (c["profile"]["name"]) formats
    characters = state.get("extracted_characters") or []
    character_names = set()
    for c in characters:
        name = c.get("name") or (c.get("profile", {}) or {}).get("name")
        if name:
            character_names.add(name)
    
    # Check relationship_graph
    rel_graph = state.get("relationship_graph") or {}
    relationships = rel_graph.get("relationships") or []
    for idx, rel in enumerate(relationships):
        source = rel.get("source", "")
        target = rel.get("target", "")
        if source and source not in character_names:
            errors.append(create_validation_error(
                field=f"relationship_graph.relationships[{idx}].source",
                code=ValidationErrorCode.REF_INTEGRITY,
                message=f"Character '{source}' not found in extracted_characters",
                value=source
            ))
        if target and target not in character_names:
            errors.append(create_validation_error(
                field=f"relationship_graph.relationships[{idx}].target",
                code=ValidationErrorCode.REF_INTEGRITY,
                message=f"Character '{target}' not found in extracted_characters",
                value=target
            ))
    
    # Check event participants
    events = state.get("extracted_events") or []
    for idx, event in enumerate(events):
        participants = event.get("participants") or []
        for p in participants:
            if p and p not in character_names:
                errors.append(create_validation_error(
                    field=f"extracted_events[{idx}].participants",
                    code=ValidationErrorCode.REF_INTEGRITY,
                    message=f"Participant '{p}' not found in extracted_characters",
                    value=p
                ))
    
    return errors[:5]  # Limit to 5 errors


def validate_consistency_status(state: dict) -> tuple:
    """Check consistency report status. Returns (penalty, errors)."""
    report = state.get("consistency_report") or {}
    
    if not report:
        return 0, []
    
    score = report.get("overall_score", 0)
    requires_reextraction = report.get("requires_reextraction", False)
    conflicts = report.get("conflicts") or []
    high_severity = sum(1 for c in conflicts if c.get("severity") == "HIGH")
    
    errors = []
    penalty = 0
    
    if requires_reextraction:
        penalty += 20
        errors.append(create_validation_error(
            field="consistency_report",
            code=ValidationErrorCode.CONSISTENCY_FAIL,
            message=f"Consistency check requires re-extraction (score: {score})",
            value=score
        ))
    
    if high_severity > 0:
        penalty += high_severity * 5
        errors.append(create_validation_error(
            field="consistency_report.conflicts",
            code=ValidationErrorCode.CONSISTENCY_FAIL,
            message=f"{high_severity} HIGH severity conflicts detected",
            value=high_severity
        ))
    
    return penalty, errors


def validate_character_richness(state: dict) -> tuple:
    """Check if characters have rich data (personality, inventory, etc). Returns (penalty, warnings)."""
    characters = state.get("extracted_characters") or []
    if not characters:
        return 0, []
    
    penalty = 0
    warnings = []
    
    richness_score = 0
    total_checks = 0
    
    for idx, char in enumerate(characters[:5]): # Check top 5 characters
        name = char.get("name") or (char.get("profile", {}) or {}).get("name") or f"Char_{idx}"
        
        # Check Personality
        has_personality = bool(char.get("personality") or char.get("char_personality"))
        
        # Check Inventory
        has_inventory = bool(char.get("inventory") or char.get("char_inventory"))
        
        # Check Stats
        has_stats = bool(char.get("stats") or char.get("char_stats"))
        
        total_checks += 3
        if has_personality: richness_score += 1
        if has_inventory: richness_score += 1
        if has_stats: richness_score += 1
        
        if not has_personality:
            warnings.append(f"Character '{name}' missing personality data")
            penalty += 2
        if not has_inventory:
            warnings.append(f"Character '{name}' missing inventory data")
            penalty += 1 # Less critical
    
    # Cap penalty
    penalty = min(penalty, 15)
    
    return penalty, warnings


def calculate_data_completeness(state: dict) -> dict:
    """Calculate data completeness percentage for each agent."""
    completeness = {}
    
    for key, rules in VALIDATION_RULES.items():
        data = state.get(key)
        
        if data is None:
            completeness[key] = 0
        elif isinstance(data, list):
            completeness[key] = 100 if len(data) >= rules.get("min_count", 1) else 50
        elif isinstance(data, dict):
            if rules.get("required_fields"):
                present = sum(1 for f in rules["required_fields"] if f in data)
                completeness[key] = int(present / len(rules["required_fields"]) * 100)
            else:
                completeness[key] = 100 if data else 0
        else:
            completeness[key] = 0
    
    return completeness


async def validator_node(state: dict) -> dict:
    """Validator Agent node function - Production Level.
    
    Role: "Quality Assurance Gate" - validates all pipeline outputs.
    
    Validates:
    1. Required data presence and completeness
    2. Required fields in each data type
    3. Referential integrity across agents
    4. Consistency report status
    5. Data quality metrics
    
    Includes:
    - Structured error reporting (field, code, message, value)
    - Execution time metrics for performance monitoring
    """
    start_time = time.time()
    
    quality_score = 100
    warnings = []
    structured_errors = []
    validation_details = {}
    
    # === 1. Validate Each Agent Output ===
    for key, rules in VALIDATION_RULES.items():
        data = state.get(key)
        details = {"present": data is not None, "errors": [], "warnings": []}
        
        if data is None:
            if rules.get("required"):
                quality_score -= rules.get("penalty_missing", 10)
                structured_errors.append(create_validation_error(
                    field=key,
                    code=ValidationErrorCode.MISSING_REQUIRED,
                    message=f"Required data '{key}' is missing"
                ))
            else:
                quality_score -= rules.get("penalty_missing", 5) // 2
            details["status"] = "missing"
        elif isinstance(data, list) and len(data) == 0:
            quality_score -= rules.get("penalty_empty", 10)
            structured_errors.append(create_validation_error(
                field=key,
                code=ValidationErrorCode.EMPTY_DATA,
                message=f"Data '{key}' is empty (no items)"
            ))
            details["status"] = "empty"
        else:
            # Validate required fields (support nested paths if specified)
            nested_paths = rules.get("nested_paths", False)
            field_errors = validate_required_fields(
                data, rules.get("required_fields", []), key, nested_paths=nested_paths
            )
            if field_errors:
                details["errors"] = field_errors[:3]
                quality_score -= len(field_errors) * 2
                structured_errors.extend(field_errors[:3])
            details["status"] = "valid"
            details["count"] = len(data) if isinstance(data, list) else 1
        
        validation_details[key] = details
    
    # === 2. Referential Integrity ===
    ref_errors = validate_referential_integrity(state)
    if ref_errors:
        quality_score -= len(ref_errors) * 3
        structured_errors.extend(ref_errors)
        warnings.extend([e["message"] for e in ref_errors])
        validation_details["referential_integrity"] = {"status": "failed", "errors": ref_errors}
    else:
        validation_details["referential_integrity"] = {"status": "valid"}
    
    # === 3. Consistency Report Status ===
    consistency_penalty, consistency_errors = validate_consistency_status(state)
    quality_score -= consistency_penalty
    structured_errors.extend(consistency_errors)
    warnings.extend([e["message"] for e in consistency_errors])
    
    # === 4. Character Data Richness ===
    richness_penalty, richness_warnings = validate_character_richness(state)
    quality_score -= richness_penalty
    warnings.extend(richness_warnings)
    if richness_warnings:
        validation_details["character_richness"] = {"status": "warning", "warnings": richness_warnings}
    else:
        validation_details["character_richness"] = {"status": "valid"}

    # === 5. Existing Errors ===
    pipeline_errors = state.get("errors") or []
    if pipeline_errors:
        quality_score -= len(pipeline_errors) * 5
        for err in pipeline_errors[:3]:
            structured_errors.append(create_validation_error(
                field="pipeline",
                code="PIPELINE_ERROR",
                message=str(err)
            ))
            warnings.append(f"Pipeline error: {err}")
    
    # === Calculate Final Score ===
    quality_score = max(0, min(100, quality_score))
    
    # === Determine Action ===
    if quality_score >= 80:
        action = "approve"
        action_description = "Ready for callback to Spring Boot"
    elif quality_score >= 50:
        action = "human_review"
        action_description = "Needs human review before proceeding"
    else:
        action = "retry_extraction"
        action_description = "Quality too low - requires re-extraction"
    
    # === Data Completeness ===
    completeness = calculate_data_completeness(state)
    avg_completeness = sum(completeness.values()) / len(completeness) if completeness else 0
    
    # === Execution Time ===
    execution_time_ms = round((time.time() - start_time) * 1000, 2)
    
    # === Build Validation Result ===
    validation_result = {
        "is_valid": quality_score >= 50,
        "quality_score": quality_score,
        "action": action,
        "action_description": action_description,
        "data_completeness": completeness,
        "average_completeness": round(avg_completeness, 1),
        "validation_details": {
            "errors": structured_errors[:10],  # Limit to 10 errors
            "warnings": warnings[:10],
            "per_field": validation_details
        },
        "error_count": len(structured_errors),
        "warning_count": len(warnings),
        "execution_time_ms": execution_time_ms
    }
    
    print(f"[VALIDATOR] Score: {quality_score}, Action: {action}, Time: {execution_time_ms}ms")
    print(f"[VALIDATOR] Completeness: {avg_completeness:.1f}%, Errors: {len(structured_errors)}")
    
    return {
        "validation_result": validation_result,
        "validation_done": True,
        "messages": [
            {"role": "validator_agent", 
             "content": f"Score: {quality_score}, Action: {action}, Time: {execution_time_ms}ms"}
        ]
    }
