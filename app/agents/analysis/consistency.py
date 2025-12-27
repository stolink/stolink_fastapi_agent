"""Consistency Checker Agent - Level 2 (Production Level).

Role: "Story Consistency Expert" / "Conflict Detector"
- Detects story conflicts between characters, events, relationships
- Provides detailed feedback for re-extraction
- Includes programmatic backup checks for obvious contradictions
- Validates direction semantics for relationships
- Suggests auto-resolution actions for each conflict
- Provides final_value_candidate for direct DB UPDATE binding

Key: Cross-validates data from all Level 1 agents:
- Character Agent: traits, roles, status
- Dialogue Agent: speech patterns, formality
- Emotion Agent: emotional states, triggers
- Relationship Agent: relation types, directions
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_advanced_llm


# Contradictory trait pairs for backup detection
CONTRADICTORY_TRAITS = [
    ("coward", "brave"),
    ("cowardly", "brave"),
    ("coward", "courageous"),
    ("timid", "brave"),
    ("weak", "strong"),
    ("unskilled", "skilled"),
    ("incompetent", "competent"),
    ("novice", "master"),
    ("beginner", "expert"),
    ("amateur", "professional"),
    ("kind", "cruel"),
    ("gentle", "violent"),
    ("honest", "dishonest"),
    ("truthful", "liar"),
    ("loyal", "traitor"),
    ("friend", "enemy"),
]

# Relationship types that MUST be unidirectional
UNIDIRECTIONAL_TYPES = {"BETRAYED", "MENTOR"}

# Auto-resolution action types
class SuggestedAction:
    """Constants for suggested_action field."""
    KEEP_DB_VALUE = "KEEP_DB_VALUE"          # Use existing DB value
    OVERWRITE_WITH_NEW = "OVERWRITE_WITH_NEW"  # Use new extracted value
    FLAG_FOR_HUMAN = "FLAG_FOR_HUMAN"          # Needs human review
    AUTO_FIX = "AUTO_FIX"                      # Can be fixed automatically


def get_suggested_action(severity: str, conflict_type: str) -> str:
    """Determine suggested action based on severity and conflict type.
    
    Rules:
    - LOW severity + simple fix → AUTO_FIX or OVERWRITE_WITH_NEW
    - MEDIUM severity → FLAG_FOR_HUMAN (需要확인)
    - HIGH severity → FLAG_FOR_HUMAN (must review)
    - DIRECTION_CONFLICT → AUTO_FIX (can fix bidirectional flag automatically)
    - REFERENTIAL_INTEGRITY_ERROR → FLAG_FOR_HUMAN (need to add missing character)
    """
    if conflict_type == "DIRECTION_CONFLICT":
        return SuggestedAction.AUTO_FIX
    
    if conflict_type == "REFERENTIAL_INTEGRITY_ERROR":
        return SuggestedAction.FLAG_FOR_HUMAN
    
    if severity == "LOW":
        return SuggestedAction.OVERWRITE_WITH_NEW
    elif severity == "MEDIUM":
        return SuggestedAction.FLAG_FOR_HUMAN
    else:  # HIGH
        return SuggestedAction.FLAG_FOR_HUMAN


CONSISTENCY_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a "Story Consistency Expert" / "Conflict Detector".
Your job is to find ALL inconsistencies and contradictions across story elements.

=== CONFLICT TYPES ===

1. **CHARACTER_TRAIT_CONFLICT** (HIGH)
   - Opposite traits for same character (coward + brave)
   - suggested_action: FLAG_FOR_HUMAN

2. **TIMELINE_CONFLICT** (MEDIUM-HIGH)
   - Events happen in impossible order
   - suggested_action: FLAG_FOR_HUMAN

3. **EVENT_CONTRADICTION** (MEDIUM-HIGH)
   - Actions contradict stated abilities
   - suggested_action: FLAG_FOR_HUMAN

4. **RELATIONSHIP_CONFLICT** (MEDIUM)
   - Conflicting relationship states
   - suggested_action: FLAG_FOR_HUMAN

5. **DIRECTION_CONFLICT** (MEDIUM)
   - BETRAYED/MENTOR must be unidirectional
   - suggested_action: AUTO_FIX (set bidirectional=false)
   - final_value_candidate: {{"bidirectional": false}}

6. **DIALOGUE_CONSISTENCY_CONFLICT** (LOW-MEDIUM)
   - Speech patterns don't match personality
   - suggested_action: OVERWRITE_WITH_NEW (LOW) / FLAG_FOR_HUMAN (MEDIUM)

7. **EMOTION_CONSISTENCY_CONFLICT** (LOW-MEDIUM)
   - Emotional state doesn't match trigger
   - suggested_action: OVERWRITE_WITH_NEW (LOW) / FLAG_FOR_HUMAN (MEDIUM)

=== SUGGESTED_ACTION VALUES ===
- KEEP_DB_VALUE: Use existing database value (new data is wrong)
- OVERWRITE_WITH_NEW: Use new extracted value (low-risk auto-update)
- FLAG_FOR_HUMAN: Needs human review before resolution
- AUTO_FIX: Can be fixed automatically by the system

=== OUTPUT STRUCTURE ===
Return ONLY valid JSON:
{{
  "overall_score": 0-100,
  "conflicts": [
    {{
      "type": "CONFLICT_TYPE",
      "description": "Clear explanation",
      "severity": "HIGH/MEDIUM/LOW",
      "affected_elements": ["character/event names"],
      "resolution_hint": "Suggestion to fix",
      "suggested_action": "FLAG_FOR_HUMAN/AUTO_FIX/OVERWRITE_WITH_NEW/KEEP_DB_VALUE",
      "final_value_candidate": {{"field": "corrected_value"}} // Only for AUTO_FIX/OVERWRITE
    }}
  ],
  "warnings": ["Minor issues that don't affect score"]
}}"""),
    ("human", """=== DATA TO VALIDATE ===

**Characters:**
{characters}

**Events:**
{events}

**Relationships:**
{relationships}

**Dialogue Analysis:**
{dialogues}

**Emotion Tracking:**
{emotions}

=== VALIDATION RULES ===
1. Check each character's traits for contradictions
2. Check if events contradict character abilities
3. Check relationship direction semantics (BETRAYED, MENTOR must be unidirectional)
4. Check if speech patterns match character personalities
5. Check if emotional states match their triggers

Find ALL conflicts and return structured JSON with suggested_action and final_value_candidate:""")
])


def detect_trait_contradictions(characters: list) -> list:
    """Programmatic backup to detect obvious trait contradictions."""
    conflicts = []
    
    for char in characters:
        name = char.get("name", "Unknown")
        
        # Handle both legacy 'traits' and production 'personality.core_traits'
        traits = char.get("traits", [])
        if not traits and isinstance(char.get("personality"), dict):
            traits = char.get("personality", {}).get("core_traits", [])
        
        traits_lower = [t.lower() for t in traits if isinstance(t, str)]
        
        # Check for contradictory trait pairs
        for trait1, trait2 in CONTRADICTORY_TRAITS:
            has_trait1 = any(trait1 in t for t in traits_lower)
            has_trait2 = any(trait2 in t for t in traits_lower)
            
            if has_trait1 and has_trait2:
                # For trait conflicts, we can't auto-fix - need human decision
                conflicts.append({
                    "type": "CHARACTER_TRAIT_CONFLICT",
                    "description": f"Character '{name}' has contradictory traits: '{trait1}' and '{trait2}' cannot both be true.",
                    "severity": "HIGH",
                    "affected_elements": [name],
                    "resolution_hint": f"Remove either '{trait1}' or '{trait2}' based on story context.",
                    "suggested_action": SuggestedAction.FLAG_FOR_HUMAN,
                    "final_value_candidate": {
                        "options": [
                            {"remove_trait": trait1, "keep_trait": trait2},
                            {"remove_trait": trait2, "keep_trait": trait1}
                        ],
                        "requires_selection": True
                    },
                    "programmatic": True
                })
    
    return conflicts


def validate_relationship_directions(relationships: list) -> list:
    """Validate that BETRAYED/MENTOR relationships are unidirectional."""
    conflicts = []
    
    for idx, rel in enumerate(relationships):
        rel_type = rel.get("relation_type") or rel.get("type", "")
        bidirectional = rel.get("bidirectional", True)
        source = rel.get("source", "Unknown")
        target = rel.get("target", "Unknown")
        
        # Check if unidirectional types are marked as bidirectional
        if rel_type.upper() in UNIDIRECTIONAL_TYPES and bidirectional:
            conflicts.append({
                "type": "DIRECTION_CONFLICT",
                "description": f"Relationship {rel_type} from '{source}' to '{target}' must be unidirectional (bidirectional=false), but is marked as bidirectional.",
                "severity": "MEDIUM",
                "affected_elements": [source, target],
                "resolution_hint": f"Set bidirectional=false for {rel_type} relationship.",
                "suggested_action": SuggestedAction.AUTO_FIX,
                # final_value_candidate: Direct value to use in UPDATE query
                "final_value_candidate": {
                    "table": "relationships",
                    "key": {"source": source, "target": target, "relation_type": rel_type},
                    "update": {"bidirectional": False}
                },
                "programmatic": True
            })
    
    return conflicts


def validate_character_references(relationships: list, available_names: set) -> list:
    """Validate that all relationship sources/targets exist in character list."""
    conflicts = []
    
    for rel in relationships:
        source = rel.get("source", "")
        target = rel.get("target", "")
        rel_type = rel.get("relation_type") or rel.get("type", "")
        
        if source and source not in available_names:
            conflicts.append({
                "type": "REFERENTIAL_INTEGRITY_ERROR",
                "description": f"Relationship source '{source}' not found in character list.",
                "severity": "HIGH",
                "affected_elements": [source],
                "resolution_hint": f"Add '{source}' to character extraction or fix the name.",
                "suggested_action": SuggestedAction.FLAG_FOR_HUMAN,
                # final_value_candidate: Candidate names from available characters
                "final_value_candidate": {
                    "action": "choose_or_create",
                    "invalid_name": source,
                    "suggestions": list(available_names)[:5],  # Top 5 available names
                    "context": f"relationship {rel_type} to {target}"
                },
                "programmatic": True
            })
        
        if target and target not in available_names:
            conflicts.append({
                "type": "REFERENTIAL_INTEGRITY_ERROR",
                "description": f"Relationship target '{target}' not found in character list.",
                "severity": "HIGH",
                "affected_elements": [target],
                "resolution_hint": f"Add '{target}' to character extraction or fix the name.",
                "suggested_action": SuggestedAction.FLAG_FOR_HUMAN,
                # final_value_candidate: Candidate names from available characters
                "final_value_candidate": {
                    "action": "choose_or_create",
                    "invalid_name": target,
                    "suggestions": list(available_names)[:5],
                    "context": f"relationship {rel_type} from {source}"
                },
                "programmatic": True
            })
    
    return conflicts


def enrich_with_suggested_action(conflicts: list) -> list:
    """Add suggested_action and final_value_candidate to LLM-generated conflicts if missing."""
    for conflict in conflicts:
        if "suggested_action" not in conflict:
            severity = conflict.get("severity", "MEDIUM")
            conflict_type = conflict.get("type", "UNKNOWN")
            conflict["suggested_action"] = get_suggested_action(severity, conflict_type)
        
        # Add default final_value_candidate if missing
        if "final_value_candidate" not in conflict:
            if conflict.get("suggested_action") == SuggestedAction.FLAG_FOR_HUMAN:
                conflict["final_value_candidate"] = None  # Requires human decision
            else:
                conflict["final_value_candidate"] = {
                    "note": "Value determined by LLM - see resolution_hint"
                }
    
    return conflicts


async def consistency_check_node(state: dict) -> dict:
    """Consistency Checker Agent node function - Production Level.
    
    Role: "Story Consistency Expert" - cross-validates all extracted data.
    
    Key principle: Validate data from all Level 1 agents for consistency.
    Provides detailed feedback for re-extraction when conflicts detected.
    Includes suggested_action and final_value_candidate for auto-resolution.
    """
    llm = get_advanced_llm()
    
    # === Gather all data from Level 1 agents ===
    characters = state.get("extracted_characters", [])
    events = state.get("extracted_events", [])
    relationships = state.get("relationship_graph", {}).get("relationships", [])
    dialogues = state.get("analyzed_dialogues", {})
    emotions = state.get("tracked_emotions", {})
    
    # Get available character names for reference validation
    available_names = {c.get("name", "") for c in characters if c.get("name")}
    
    print(f"[CONSISTENCY] Validating: {len(characters)} chars, {len(events)} events, {len(relationships)} rels")
    print(f"[CONSISTENCY] Available names: {available_names}")
    
    chain = CONSISTENCY_CHECK_PROMPT | llm
    
    try:
        response = await chain.ainvoke({
            "characters": json.dumps(characters, ensure_ascii=False, indent=2),
            "events": json.dumps(events, ensure_ascii=False, indent=2),
            "relationships": json.dumps(relationships, ensure_ascii=False, indent=2),
            "dialogues": json.dumps(dialogues, ensure_ascii=False, indent=2) if dialogues else "{}",
            "emotions": json.dumps(emotions, ensure_ascii=False, indent=2) if emotions else "{}"
        })
        
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        
        # Ensure all LLM conflicts have suggested_action and final_value_candidate
        if "conflicts" in result:
            result["conflicts"] = enrich_with_suggested_action(result["conflicts"])
        
    except Exception as e:
        print(f"[CONSISTENCY] LLM error: {e}")
        result = {
            "overall_score": 100,
            "conflicts": [],
            "warnings": []
        }
    
    # === PROGRAMMATIC BACKUP VALIDATIONS ===
    
    # 1. Trait contradiction detection
    trait_conflicts = detect_trait_contradictions(characters)
    
    # 2. Relationship direction validation
    direction_conflicts = validate_relationship_directions(relationships)
    
    # 3. Character reference validation
    reference_conflicts = validate_character_references(relationships, available_names)
    
    # Merge all programmatic conflicts
    programmatic_conflicts = trait_conflicts + direction_conflicts + reference_conflicts
    
    # Avoid duplicates when merging
    existing_descriptions = {c.get("description", "")[:50] for c in result.get("conflicts", [])}
    for pc in programmatic_conflicts:
        if pc["description"][:50] not in existing_descriptions:
            result.setdefault("conflicts", []).append(pc)
            print(f"[CONSISTENCY] Programmatic: {pc['type']} - {pc['description'][:60]}...")
    
    # === CALCULATE FINAL SCORE ===
    conflicts = result.get("conflicts", [])
    high_count = sum(1 for c in conflicts if c.get("severity") == "HIGH")
    medium_count = sum(1 for c in conflicts if c.get("severity") == "MEDIUM")
    low_count = sum(1 for c in conflicts if c.get("severity") == "LOW")
    
    # Recalculate score with programmatic conflicts
    if programmatic_conflicts:
        calculated_score = 100 - (high_count * 25) - (medium_count * 10) - (low_count * 5)
        result["overall_score"] = max(0, calculated_score)
    
    score = result.get("overall_score", 100)
    
    # Force re-extraction if score <= 50 OR any HIGH severity conflicts
    result["requires_reextraction"] = score <= 50 or high_count >= 1
    
    # === Auto-resolution summary ===
    auto_fix_count = sum(1 for c in conflicts if c.get("suggested_action") == SuggestedAction.AUTO_FIX)
    human_review_count = sum(1 for c in conflicts if c.get("suggested_action") == SuggestedAction.FLAG_FOR_HUMAN)
    auto_overwrite_count = sum(1 for c in conflicts if c.get("suggested_action") == SuggestedAction.OVERWRITE_WITH_NEW)
    
    # Count conflicts with ready-to-use final_value_candidate
    ready_for_update = sum(
        1 for c in conflicts 
        if c.get("final_value_candidate") and c.get("suggested_action") == SuggestedAction.AUTO_FIX
    )
    
    result["resolution_summary"] = {
        "auto_fixable": auto_fix_count,
        "ready_for_update": ready_for_update,  # Can directly UPDATE in DB
        "needs_human_review": human_review_count,
        "auto_overwritable": auto_overwrite_count,
        "total_conflicts": len(conflicts)
    }
    
    # === Neo4j-Ready Output ===
    neo4j_validation = {
        "is_valid": not result["requires_reextraction"],
        "conflict_count": len(conflicts),
        "high_severity_count": high_count,
        "auto_fixable_count": auto_fix_count,
        "ready_for_update": ready_for_update,
        "validation_timestamp": state.get("processing_start_time")
    }
    result["neo4j_validation"] = neo4j_validation
    
    print(f"[CONSISTENCY] Score: {score}, HIGH: {high_count}, MEDIUM: {medium_count}, LOW: {low_count}")
    print(f"[CONSISTENCY] Auto-fix: {auto_fix_count} (ready_for_update: {ready_for_update}), Human review: {human_review_count}")
    print(f"[CONSISTENCY] Requires re-extraction: {result['requires_reextraction']}")
    
    return {
        "consistency_report": result,
        "messages": [
            {"role": "consistency_agent", 
             "content": f"Score: {score}, Conflicts: {len(conflicts)} (AUTO_FIX: {auto_fix_count}, READY: {ready_for_update})"}
        ]
    }
