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

=== EXCLUSION RULES (DO NOT FLAGG THESE) ===
- Narrative Tension: Characters having different beliefs/memories (e.g., A thinks B is a traitor, B thinks they are loyal) is VALID story conflict, NOT an error.
- Character Growth: Personality changing over time (e.g., coward -> brave) is VALID, NOT an error.
- Lies/Deception: A character lying about their status is VALID.

=== CONFLICT TYPES (ONLY FLAGG DATA ERRORS) ===

1. **CHARACTER_TRAIT_CONFLICT** (HIGH)
   - Impossible contradiction at the SAME moment (e.g., "dead" and "alive" simultaneously).

2. **TIMELINE_CONFLICT** (MEDIUM-HIGH)
   - Events physically impossible (e.g., Character A dies in Event 1 but appears in Event 3).
   - NOT for conflicting memories between characters.

3. **RELATIONSHIP_CONFLICT** (MEDIUM)
   - Graph structure errors (e.g., A is "father" of B, but B is "spouse" of A).
   - NOT for dynamic relationship changes (Friends -> Enemies is valid).

4. **SETTING_CONFLICT** (MEDIUM)
   - Location descriptions physically contradict (e.g., "Underground" and "Sunny sky").

5. **INVENTORY_CONFLICT** (MEDIUM-HIGH)
   - Character uses item they NEVER acquired.
   - Appearance says "holding sword", Inventory says "empty".

6. **STATS_CONFLICT** (MEDIUM)
   - Level 1 character defeating Level 99 boss without explanation.

7. **CROSS_CHAPTER_CONFLICT** (HIGH) [NEW - Check against historical_context]
   - Character marked "deceased" in previous chapter appears alive without explanation.
   - Relationship type changes drastically without narrative justification.
   - Event contradicts previously established facts.

=== SUGGESTED_ACTION VALUES ===
- AUTO_FIX: Can be fixed automatically
- FLAG_FOR_HUMAN: True data error needing review
- REEXTRACT: Data is garbage/corrupted
- IGNORE: Narrative conflict or minor issue (Use this for legitimate story tension)

=== SCORING ===
- Start at 100
- HIGH severity: -25 points each
- MEDIUM severity: -10 points each
- LOW severity: -5 points each

If score <= 50 or any HIGH severity conflict: requires_reextraction = true"""),
    ("human", """=== CURRENT CHAPTER DATA ===

**Characters (Current):**
{characters}

**Events (Current):**
{events}

**Relationships (Current):**
{relationships}

=== HISTORICAL CONTEXT (Previous Chapters) ===
{historical_context}

Find ALL conflicts including CROSS_CHAPTER_CONFLICT between current and historical data.""")
])


def detect_trait_contradictions(characters: list) -> list[Conflict]:
    """Programmatic backup to detect obvious trait contradictions."""
    conflicts = []
    
    for char in characters:
        # Support both legacy (c["name"]) and FullCharacter (c["profile"]["name"]) formats
        name = char.get("name") or (char.get("profile", {}) or {}).get("name") or "Unknown"
        
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
    """Consistency Checker Agent node function - with Structured Output + RAG.
    
    Combines LLM analysis with programmatic validation and historical context.
    """
    from app.services.db_query_service import get_db_service
    
    characters = state.get("extracted_characters", [])
    events = state.get("extracted_events", [])
    relationships = state.get("relationship_graph", {}).get("relationships", [])
    project_id = state.get("project_id")
    
    # Support both legacy (c["name"]) and FullCharacter (c["profile"]["name"]) formats
    available_names = set()
    for c in characters:
        name = c.get("name") or (c.get("profile", {}) or {}).get("name")
        if name:
            available_names.add(name)
    
    print(f"[CONSISTENCY] Validating: {len(characters)} chars, {len(events)} events, {len(relationships)} rels")
    
    # === RAG: Retrieve historical context ===
    historical_context = {"characters": [], "events": [], "search_performed": False}
    if project_id:
        try:
            db_service = await get_db_service()
            historical_context = await db_service.retrieve_relevant_history(
                project_id=project_id,
                current_characters=characters,
                current_events=events,
                top_k=10
            )
            print(f"[CONSISTENCY] RAG: Found {len(historical_context['characters'])} historical chars, {len(historical_context['events'])} historical events")
        except Exception as e:
            print(f"[CONSISTENCY] RAG failed (non-critical): {e}")
    
    try:
        # Get structured LLM
        structured_llm = get_structured_llm(ConsistencyReport, tier="basic")
        chain = CONSISTENCY_CHECK_PROMPT | structured_llm
        
        result: ConsistencyReport = await chain.ainvoke({
            "characters": str(characters),
            "events": str(events),
            "relationships": str(relationships),
            "historical_context": str(historical_context) if historical_context["search_performed"] else "No historical data available",
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
    
    # Force re-extraction only for critical issues:
    # - Score <= 20 (very severe problems) - Relaxed from 30 for short texts
    # - OR 2+ HIGH severity conflicts (multiple critical issues)
    result.requires_reextraction = result.overall_score <= 20 or high_count >= 2
    
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
