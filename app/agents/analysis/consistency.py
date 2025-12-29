"""Consistency Checker Agent - with Structured Output.

Role: "Story Consistency Expert" / "Conflict Detector"
- Detects story conflicts between characters, events, relationships
- Provides detailed feedback for re-extraction
- Includes programmatic backup checks for obvious contradictions

Uses with_structured_output() for LLM calls.
Maintains programmatic validation for guaranteed detection.
"""
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_structured_llm, get_advanced_llm
from app.schemas.consistency import ConsistencyReport, Conflict, ConflictType, Severity, SuggestedAction


# Contradictory trait pairs for backup detection
CONTRADICTORY_TRAITS = [
    ("coward", "brave"), ("cowardly", "brave"), ("coward", "courageous"),
    ("timid", "brave"), ("weak", "strong"), ("unskilled", "skilled"),
    ("incompetent", "competent"), ("novice", "master"), ("beginner", "expert"),
    ("amateur", "professional"), ("kind", "cruel"), ("gentle", "violent"),
    ("honest", "dishonest"), ("truthful", "liar"), ("loyal", "traitor"),
]

# Relationship types that MUST be unidirectional
UNIDIRECTIONAL_TYPES = {"BETRAYED", "MENTOR"}


CONSISTENCY_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a "Story Consistency Expert" / "Conflict Detector".
Your job is to find ALL inconsistencies and contradictions across story elements.

=== CONFLICT TYPES ===

1. **CHARACTER_TRAIT_CONFLICT** (HIGH)
   - Opposite traits for same character (coward + brave)

2. **TIMELINE_CONFLICT** (MEDIUM-HIGH)
   - Events happen in impossible order

3. **RELATIONSHIP_CONFLICT** (MEDIUM)
   - Conflicting relationship states

4. **SETTING_CONFLICT** (MEDIUM)
   - Location descriptions contradict each other

=== SUGGESTED_ACTION VALUES ===
- AUTO_FIX: Can be fixed automatically by the system
- FLAG_FOR_HUMAN: Needs human review before resolution
- REEXTRACT: Needs re-extraction with corrected data
- IGNORE: Minor issue, can be ignored

=== SCORING ===
- Start at 100
- HIGH severity: -25 points each
- MEDIUM severity: -10 points each
- LOW severity: -5 points each

If score <= 50 or any HIGH severity conflict: requires_reextraction = true"""),
    ("human", """=== DATA TO VALIDATE ===

**Characters:**
{characters}

**Events:**
{events}

**Relationships:**
{relationships}

**Dialogues:**
{dialogues}

**Emotions:**
{emotions}

Find ALL conflicts and validate consistency.""")
])


def detect_trait_contradictions(characters: list) -> list[Conflict]:
    """Programmatic backup to detect obvious trait contradictions."""
    conflicts = []
    
    for char in characters:
        name = char.get("name", "Unknown")
        
        traits = char.get("traits", [])
        if not traits and isinstance(char.get("personality"), dict):
            traits = char.get("personality", {}).get("core_traits", [])
        
        traits_lower = [t.lower() for t in traits if isinstance(t, str)]
        
        for trait1, trait2 in CONTRADICTORY_TRAITS:
            has_trait1 = any(trait1 in t for t in traits_lower)
            has_trait2 = any(trait2 in t for t in traits_lower)
            
            if has_trait1 and has_trait2:
                conflicts.append(Conflict(
                    type=ConflictType.CHARACTER_TRAIT_CONFLICT,
                    severity=Severity.HIGH,
                    source="extracted",
                    existing=trait1,
                    new=trait2,
                    character=name,
                    description=f"Character '{name}' has contradictory traits: '{trait1}' and '{trait2}'",
                    suggested_action=SuggestedAction.FLAG_FOR_HUMAN
                ))
    
    return conflicts


def validate_relationship_directions(relationships: list) -> list[Conflict]:
    """Validate that BETRAYED/MENTOR relationships are unidirectional."""
    conflicts = []
    
    for rel in relationships:
        rel_type = rel.get("relation_type") or rel.get("type", "")
        bidirectional = rel.get("bidirectional", True)
        source = rel.get("source", "Unknown")
        target = rel.get("target", "Unknown")
        
        if rel_type.upper() in UNIDIRECTIONAL_TYPES and bidirectional:
            conflicts.append(Conflict(
                type=ConflictType.RELATIONSHIP_CONFLICT,
                severity=Severity.MEDIUM,
                source="extracted",
                existing=f"bidirectional=true",
                new=f"bidirectional=false",
                character=source,
                description=f"Relationship {rel_type} from '{source}' to '{target}' must be unidirectional",
                suggested_action=SuggestedAction.AUTO_FIX
            ))
    
    return conflicts


async def consistency_check_node(state: dict) -> dict:
    """Consistency Checker Agent node function - with Structured Output.
    
    Combines LLM analysis with programmatic validation for guaranteed detection.
    """
    characters = state.get("extracted_characters", [])
    events = state.get("extracted_events", [])
    relationships = state.get("relationship_graph", {}).get("relationships", [])
    dialogues = state.get("analyzed_dialogues", {})
    emotions = state.get("tracked_emotions", {})
    
    available_names = {c.get("name", "") for c in characters if c.get("name")}
    
    print(f"[CONSISTENCY] Validating: {len(characters)} chars, {len(events)} events, {len(relationships)} rels")
    
    try:
        # Get structured LLM
        structured_llm = get_structured_llm(ConsistencyReport)
        chain = CONSISTENCY_CHECK_PROMPT | structured_llm
        
        result: ConsistencyReport = await chain.ainvoke({
            "characters": str(characters),
            "events": str(events),
            "relationships": str(relationships),
            "dialogues": str(dialogues) if dialogues else "{}",
            "emotions": str(emotions) if emotions else "{}"
        })
        
    except Exception as e:
        print(f"[CONSISTENCY] Structured output error: {e}, using fallback")
        result = ConsistencyReport(
            overall_score=100,
            requires_reextraction=False,
            conflicts=[],
            warnings=[f"LLM validation failed: {str(e)}"]
        )
    
    # === PROGRAMMATIC BACKUP VALIDATIONS ===
    trait_conflicts = detect_trait_contradictions(characters)
    direction_conflicts = validate_relationship_directions(relationships)
    
    programmatic_conflicts = trait_conflicts + direction_conflicts
    
    # Merge programmatic conflicts avoiding duplicates
    existing_descriptions = {c.description[:50] for c in result.conflicts}
    for pc in programmatic_conflicts:
        if pc.description[:50] not in existing_descriptions:
            result.conflicts.append(pc)
            print(f"[CONSISTENCY] Programmatic: {pc.type} - {pc.description[:60]}...")
    
    # === CALCULATE FINAL SCORE ===
    conflicts = result.conflicts
    high_count = sum(1 for c in conflicts if c.severity == Severity.HIGH)
    medium_count = sum(1 for c in conflicts if c.severity == Severity.MEDIUM)
    low_count = sum(1 for c in conflicts if c.severity == Severity.LOW)
    
    # Recalculate score
    calculated_score = 100 - (high_count * 25) - (medium_count * 10) - (low_count * 5)
    result.overall_score = max(0, calculated_score)
    
    # Force re-extraction if score <= 50 OR any HIGH severity conflicts
    result.requires_reextraction = result.overall_score <= 50 or high_count >= 1
    
    # === Update resolution summary ===
    auto_fix_count = sum(1 for c in conflicts if c.suggested_action == SuggestedAction.AUTO_FIX)
    human_review_count = sum(1 for c in conflicts if c.suggested_action == SuggestedAction.FLAG_FOR_HUMAN)
    
    result.resolution_summary.auto_fixable = auto_fix_count
    result.resolution_summary.needs_human_review = human_review_count
    result.resolution_summary.total_conflicts = len(conflicts)
    
    # === Update neo4j validation ===
    result.neo4j_validation.is_valid = not result.requires_reextraction
    result.neo4j_validation.conflict_count = len(conflicts)
    result.neo4j_validation.high_severity_count = high_count
    
    print(f"[CONSISTENCY] Score: {result.overall_score}, HIGH: {high_count}, MEDIUM: {medium_count}")
    print(f"[CONSISTENCY] Auto-fix: {auto_fix_count}, Human review: {human_review_count}")
    print(f"[CONSISTENCY] Requires re-extraction: {result.requires_reextraction}")
    
    return {
        "consistency_report": result.model_dump(),
        "messages": [
            {"role": "consistency_agent", 
             "content": f"Score: {result.overall_score}, Conflicts: {len(conflicts)} (Structured Output)"}
        ]
    }
