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

=== EXCLUSION RULES (DO NOT FLAG THESE) ===
- Narrative Tension: Characters having different beliefs/memories (e.g., A thinks B is a traitor, B thinks they are loyal) is VALID story conflict, NOT an error.
- Character Growth: Personality changing over time (e.g., coward -> brave) is VALID, NOT an error.
- Lies/Deception: A character lying about their status is VALID.
- **Rank/Influence Defaults**: Rank=COMMON or Influence=0 are default values, NOT errors. Do NOT flag these as conflicts with character status/importance.

=== 15 CONFLICT TYPES (DETECT THESE DATA ERRORS) ===

**[1-6] Core Consistency Errors**

1. **CHARACTER_TRAIT_CONFLICT** (HIGH) - 캐릭터 설정 충돌
   - 성격/행동 모순: 겁쟁이가 이유 없이 선봉에 서는 경우
   - 능력치 불일치: "검술 초보"인데 기사를 이기는 경우

2. **RELATIONSHIP_CONFLICT** (MEDIUM) - 관계 논리 오류
   - 감정 급발진: 빌드업 없이 갑자기 사랑/적대
   - 관계 기억 상실: 화해 후 다시 이유 없이 적대
   - 구조 오류: A가 B의 "father"인데 B가 A의 "spouse"

3. **TIMELINE_CONFLICT** (HIGH) - 시간/인과 오류
   - 선후관계 오류: 결과가 원인보다 먼저 발생
   - 이동 시간 무시: 서울→부산 1시간 만에 도보 도착
   - 사망 후 등장: 죽은 캐릭터가 설명 없이 재등장

4. **SETTING_CONFLICT** (MEDIUM) - 세계관/배경 오류
   - 지리적 오류: 섬나라인데 육로로 침공당함
   - 시대착오: 중세에 지퍼, 손목시계 사용
   - 물리적 모순: "지하동굴"인데 "맑은 하늘" 묘사

5. **INVENTORY_CONFLICT** (MEDIUM-HIGH) - 아이템/소지품 오류
   - 미획득 아이템 사용: 받지 않은 물건을 사용
   - 외형-소지품 불일치: "검을 들고 있다"인데 인벤토리 비어있음

6. **STATS_CONFLICT** (MEDIUM) - 능력치/레벨 오류
   - 레벨 모순: Lv.1이 Lv.99를 이김 (설명 없이)

**[7-15] Extended Plausibility Errors**

7. **CONSEQUENCE_MISSING** (MEDIUM) - 후폭풍/반작용 부재
   - 공권력 부재: 도심 폭발인데 경찰/군대 미출동
   - 손상 무시: 칼에 찔렸는데 다음 장면에서 멀쩡함
   - 경제 여파 누락: 보물창고 약탈 후 인플레이션 없음

8. **INFORMATION_LOGIC_ERROR** (MEDIUM) - 정보 논리 오류
   - 전지적 캐릭터: 도청 없이 다른 장소 사건을 앎
   - 정보 전파 속도: 중세인데 소문이 순간이동
   - 설명조 대화: "자네도 알다시피..." 억지 설명

9. **PROBABILITY_BIAS** (LOW-MEDIUM) - 확률 편향
   - 주인공 보정: 화살 수백 발 중 주인공만 안 맞음
   - 우연의 연속: 필요한 것이 항상 우연히 등장

10. **POWER_BALANCE_ERROR** (MEDIUM) - 파워 밸런스 오류
    - 인플레이션 부조화: 중간보스가 최종보스보다 강함
    - 상성 무시: 불 약점 몬스터가 불에 안 죽음
    - 소모값 무시: 강력 기술을 피로 없이 난사

11. **POV_VIOLATION** (MEDIUM) - 시점 위반
    - 1인칭 이탈: 주인공 기절 중 다른 장소 묘사
    - 내면 혼선: 3인칭 제한에서 행인 속마음 서술

12. **SELECTIVE_INCOMPETENCE** (MEDIUM) - 선택적 무능
    - 능력 미사용: 비행 마법 있는데 절벽에서 절망
    - 아이템 방치: 만병통치약 있는데 약초 구하러 감
    - 지능 너프: 평소 현명한 캐릭터가 유치한 실수

13. **LOGISTICS_ERROR** (LOW-MEDIUM) - 병참/보급 오류
    - 무한 화살: 보충 없이 수백 발 사격
    - 보급 없는 대군: 수만 명이 식량 없이 행군
    - 화폐 불일치: 한 달 생활비 은화 1닢인데 밥값 10닢

14. **EMOTIONAL_CONTINUITY_ERROR** (MEDIUM) - 감정 지속성 오류
    - 트라우마 증발: 가족 몰살 직후 연애 시작
    - 피로/고통 삭제: 며칠 밤샘+부상 후 즉시 100% 컨디션

15. **SOCIAL_PROTOCOL_VIOLATION** (LOW-MEDIUM) - 사회 규범 위반
    - 무례함 허용: 황제 앞에서 반말하는데 처벌 없음
    - 현대 가치 주입: 고대 사회에서 인권 설파 시 즉시 감화

16. **WORLD_RULE_VIOLATION** (HIGH) - 세계관 규칙/마법 강제 조건 위반 ⭐ CRITICAL
    - 마법/시스템 규칙 위반: 작품 내에서 설정된 마법/규칙이 설명 없이 깨짐
    - 조건 우회: 특정 조건(나이, 자격, 혈통 등)을 충족해야만 가능한 행위를 미충족자가 수행
    - 물리적 제한 무시: 불가능하다고 명시된 행위가 발생
    
    **예시 (반드시 탐지!):**
    - "17세 이상만 이름을 넣을 수 있는 마법이 걸린 불의 잔"에 14세가 이름을 넣음
    - "왕족 혈통만 사용 가능한 검"을 평민이 사용함
    - "마나가 0이면 마법 사용 불가"인데 마나 0 상태에서 마법 사용
    - "낮에만 활동 가능한 뱀파이어"가 한낮에 돌아다님

=== CROSS_CHAPTER_CONFLICT (Special - VERY IMPORTANT) ===
Compare CURRENT data against HISTORICAL_CONTEXT. Flag these as HIGH severity:

**MUST DETECT (Critical Cross-Chapter Errors):**
1. **Status Change**: Character marked DECEASED in history but ALIVE in current (or vice versa)
   - 예: "카엘이 사망함" (1챕터) → "카엘이 눈을 떴다" (2챕터) = TIMELINE_CONFLICT (HIGH)
2. **Setting/Location Change**: Same location has contradictory descriptions
   - 예: "붉은 황무지(사막)" (1챕터) → "하얀 설원(눈)" (2챕터) = SETTING_CONFLICT (HIGH)
3. **Power Imbalance Reversal**: Weak character suddenly defeats powerful one without explanation
   - 예: "대마법사 말로스가 카엘을 압도" (1챕터) → "넘어져서 휘두른 칼에 말로스 즉사" (2챕터) = POWER_BALANCE_ERROR (HIGH)

=== CRITICAL PRIORITY CHECKS ===
Before outputting, VERIFY you have checked:
- [ ] Any character who DIED in historical_context appears alive? → TIMELINE_CONFLICT
- [ ] Same setting name but different climate/geography? → SETTING_CONFLICT
- [ ] Previous chapter's powerful entity defeated too easily? → POWER_BALANCE_ERROR
- [ ] **Any established world rule (magic, age limit, qualification) violated?** → WORLD_RULE_VIOLATION ⭐
      예: "17세 이상만 가능"인데 14세가 수행, "마법사만 가능"인데 평민이 사용

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

If score <= 50 or any HIGH severity conflict: requires_reextraction = true

=== LANGUAGE INSTRUCTION ===
**CRITICAL**: Respond in the SAME language as the input DATA.
- If the input characters/events data is in Korean (한글), ALL conflict descriptions, warnings, and recommendations MUST be in Korean.
- If the input data is in English, ALL text fields MUST be in English.
- Keep technical field names (like "type", "severity") in English, but "description" content should match the input language."""),
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
    is_short_text = state.get("is_short_text", False)
    
    # Support both legacy (c["name"]) and FullCharacter (c["profile"]["name"]) formats
    available_names = set()
    for c in characters:
        name = c.get("name") or (c.get("profile", {}) or {}).get("name")
        if name:
            available_names.add(name)
    
    print(f"[CONSISTENCY] Validating: {len(characters)} chars, {len(events)} events, {len(relationships)} rels (Short Text: {is_short_text})")
    
    # === RAG: Retrieve historical context ===
    historical_context = {"characters": [], "events": [], "search_performed": False}
    # 🆕 Always apply RAG regardless of is_short_text (user request: apply for all texts)
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
        
        # === LOG HISTORICAL CONTEXT BEING USED ===
        if historical_context["search_performed"]:
            print(f"\n{'='*60}", flush=True)
            print(f"[CONSISTENCY] 🔍 Historical Context for LLM", flush=True)
            print(f"{'='*60}", flush=True)
            print(f"[CONSISTENCY] Using {len(historical_context['characters'])} historical chars, {len(historical_context['events'])} events for consistency check", flush=True)
            hist_ctx_str = str(historical_context)[:800]
            print(f"[CONSISTENCY] Historical data preview: {hist_ctx_str}...", flush=True)
            print(f"{'='*60}\n", flush=True)
        
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
