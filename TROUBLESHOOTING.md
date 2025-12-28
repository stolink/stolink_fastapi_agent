# StoLink AI Backend - Troubleshooting Guide

> **Last Updated**: 2025-12-27

이 문서는 개발 과정에서 발생한 주요 문제와 해결책을 기록합니다.

---

## 목차

1. [Setting Agent - 인물/사건 혼입 문제](#1-setting-agent---인물사건-혼입-문제)
2. [Event Agent - 배경 묘사 혼입 및 참조 매칭 문제](#2-event-agent---배경-묘사-혼입-및-참조-매칭-문제)
3. [Dialogue Agent - Production Level 업그레이드](#3-dialogue-agent---production-level-업그레이드)
4. [Emotion Agent - Production Level 업그레이드](#4-emotion-agent---production-level-업그레이드)
5. [Consistency Agent - Production Level 업그레이드](#5-consistency-agent---production-level-업그레이드)
6. [Plot Integration Agent - Production Level 업그레이드](#6-plot-integration-agent---production-level-업그레이드)

---

## 1. Setting Agent - 인물/사건 혼입 문제

### 📅 날짜
2025-12-27

### 🔴 문제 (Problem)
Setting Agent가 배경만 추출해야 하는데, 캐릭터 이름과 행동을 포함함.

**실패 출력 예시**:
```json
{
  "visual_background": "Seojin standing in a dark forest holding a sword..."
}
```

**기대 출력**:
```json
{
  "visual_background": "Dark ancient forest, dense twisted trees, thick fog on ground..."
}
```

### 🟡 원인 분석 (Root Cause)
1. LLM이 "Setting(배경)"과 "Scene(장면)"을 혼동
2. 단순히 "하지 마(Don't)"라고만 지시하면 무시함
3. Gemini Flash/Llama 3 등은 텍스트 요약 성향이 강함

### 🟢 해결책 (Solution)

#### 1. Bad vs Good 예시 (Few-shot Learning)
```
❌ BAD: "Seojin standing in a dark forest holding a sword."
✅ GOOD: "Dark ancient forest, dense twisted trees, thick fog on ground."
```

#### 2. 필드명 변경
| 변경 전 | 변경 후 |
|---------|---------|
| `description` | `static_visual_prompt` |
| `visual_background` | `static_visual_prompt` |

#### 3. Chain of Thought 프로세스
```
1. IDENTIFY: 텍스트에서 캐릭터 이름/행동 동사 찾기
2. REMOVE: 완전히 제거
3. FOCUS: 남은 물리적 환경에만 집중
4. DESCRIBE: 텍스처, 재질, 조명, 색상으로 묘사
5. CREATIVELY INFER: 간단한 묘사면 디테일 추가
```

#### 4. 페널티 경고 추가
```
PENALTY WARNING: If ANY character name or action verb is included, 
the output is INVALID and will be REJECTED.
```

### 📁 수정된 파일
- `app/agents/extraction/setting.py` - 프롬프트 전면 개선
- `app/schemas/settings.py` - `is_primary`, `art_style` 필드 추가

### ✅ 결과
- 인물/사건 완전 제거됨
- 순수 배경 데이터(Clean Background Data) 생성 성공
- 이미지 생성 AI에 직접 사용 가능한 프롬프트 품질 달성

---

## 2. Event Agent - 배경 묘사 혼입 및 참조 매칭 문제

### 📅 날짜
2025-12-27

### 🔴 문제 (Problem)
1. `visual_scene`에 배경 묘사가 포함됨 (Setting Agent와 중복)
2. `participants`가 Character Agent의 이름과 정확히 매칭되지 않음
3. `location_ref`가 Setting Agent의 이름과 매칭되지 않음

**실패 출력 예시**:
```json
{
  "visual_scene": "A man holding a sword in a dark forest with tall trees and fog.",
  "participants": ["the protagonist"],
  "location_ref": "A dark forest where trees are twisted"
}
```

**기대 출력**:
```json
{
  "visual_scene": "A tall man with dark hair gripping a sword, tense posture, alert expression",
  "participants": ["서진"],
  "location_ref": "Dark Forest"
}
```

### 🟡 원인 분석 (Root Cause)
1. Event Agent에게 Character/Setting 정보가 전달되지 않음
2. 프롬프트에 명확한 역할 분리 지시 없음
3. 참조용 데이터 없이 LLM이 자체 생성

### 🟢 해결책 (Solution)

#### 1. Phase 분리 (graph.py)
```python
# Phase 1: Character + Setting (병렬)
# Phase 2: Event (순차 - Phase 1 결과 참조)
```

#### 2. Bad vs Good 예시 추가
```
❌ BAD: visual_scene에 "dark forest with trees"
✅ GOOD: visual_scene에 "intense eye contact, low angle shot" (구도만)
```

#### 3. 참조 데이터 전달
```python
response = await chain.ainvoke({
    "story_text": state["content"],
    "available_characters": ["서진", "이민호", ...],  # Character Agent 결과
    "available_settings": ["Dark Forest", ...],       # Setting Agent 결과
})
```

#### 4. 페널티 경고
```
If visual_scene contains "forest", "trees", "moon", "fog" - REJECTED
```

### 📁 수정된 파일
- `app/agents/graph.py` - 2-Phase Extraction 구현
- `app/agents/extraction/event.py` - 프롬프트 전면 개선
- `app/schemas/events.py` - (이미 Production Level)

### ✅ 결과
- Event의 `visual_scene`에서 배경 묘사 제거
- `participants`가 Character Agent 이름과 정확히 매칭
- `location_ref`가 Setting Agent 이름과 정확히 매칭
- Neo4j 그래프 엣지 자동 생성 가능

---

## 3. Dialogue Agent - Production Level 업그레이드

### 📅 날짜
2025-12-27

### 🔴 문제 (Problem)
1. 기본적인 프롬프트만 있어서 출력 구조가 단순함
2. Character Agent와 이름 매칭이 안 됨
3. Neo4j 엣지 생성에 필요한 속성(formality, power, intimacy)이 없음

**기존 출력**:
```json
{
  "key_dialogues": ["..."],
  "speech_patterns": {}
}
```

### 🟡 원인 분석 (Root Cause)
1. Dialogue Agent가 Character Agent 결과를 참조하지 않음
2. 스키마(`dialogues.py`)에 상세 모델이 있지만 프롬프트에서 활용 안 함
3. 관계성(speaker → listener)이 구조화되지 않음

### 🟢 해결책 (Solution)

#### 1. Character 참조 전달
```python
available_characters = [c.get("name", "") for c in state.get("extracted_characters", [])]
response = await chain.ainvoke({
    "story_text": state["content"],
    "available_characters": json.dumps(available_characters)
})
```

#### 2. 3차원 관계 모델링
- `formality`: "formal", "informal", "mixed"
- `power_dynamic`: "superior", "equal", "subordinate"
- `intimacy_level`: 1-10 정량화

#### 3. Neo4j 엣지 속성 추출
```json
{
  "dialogue_relationships": [
    {
      "speaker": "하나",
      "listener": "서진",
      "formality_to_listener": "formal",
      "power_dynamic": "subordinate",
      "intimacy_level": 7
    }
  ]
}
```

### ⚠️ 주의사항 (Data Integrity)

#### Enum 유효성 검증
LLM이 "polite" 대신 "formal", "lower" 대신 "subordinate" 등 유의어를 출력할 수 있음.
→ Pydantic 또는 후처리에서 허용값 검증 필요

#### 노드 키 무결성
Character Agent가 "Seojin"(영문), Dialogue Agent가 "서진"(한글) 출력 시 매칭 실패
→ 일관된 식별자(Identifier) 사용 권장

### 📁 수정된 파일
- `app/agents/extraction/dialogue.py` - 프롬프트 Production Level 업그레이드
- `tests/test_agents/test_dialogue_analysis.ipynb` - 테스트 노트북 상세화

### ✅ 결과
- `key_dialogues`: 중요 대사 + 숨겨진 의미(subtext) 추출
- `speech_patterns`: 캐릭터별 말투 특성
- `dialogue_relationships`: Neo4j 엣지 속성 (formality, power, intimacy)
- Character Agent 이름과 정확히 매칭

### 💡 향후 개선 사항 (Future Enhancements)

#### 1. 친밀도(Intimacy) 변수 분리
현재: 단일 `intimacy_level` (1-10)
문제: 소꿉친구 설정에도 현재 적대적이면 낮게 측정됨

**제안된 분리**:
```json
{
  "friendliness": 2,      // 현재 우호도 (낮음)
  "bond_strength": 9      // 관계의 깊이/역사 (높음)
}
```
→ "죽이고 싶을 만큼 미우면서도 서로를 가장 잘 아는 애증 관계" 표현 가능

#### 2. 권력 관계 비대칭성 검증
A→B가 "superior"면 B→A는 "subordinate"여야 함
현재: LLM이 상황에 따라 다르게 판단 (하나가 이민호에게 맞서는 태도 = equal)

**검증 로직 추가 제안**:
```python
if power_ab == "superior" and power_ba != "subordinate":
    conflicts.append("Power asymmetry detected")
```

#### 3. 식별자 일관성 강제
이미 `available_characters` 전달로 해결됨
추가 보완: 프롬프트에 **"캐릭터 이름은 반드시 제공된 리스트 표기를 그대로 따를 것"** 명시

---

## 4. Emotion Agent - Production Level 업그레이드

### 📅 날짜
2025-12-27

### 🔴 문제 (Problem)
1. 기본적인 프롬프트로 출력 구조가 단순함 (emotion, intensity만)
2. Character Agent와 이름 매칭이 안 됨
3. 감정 트리거, 표현 방식 등 컨텍스트 부족

### 🟢 해결책 (Solution)

#### 1. 감정 필드 확장
- `primary_emotion`, `secondary_emotion`: 복합 감정 표현
- `trigger`: 감정 유발 원인
- `expression`: 물리적 표현 방식
- `is_hidden`: 숨겨진 감정 여부

#### 2. Neo4j 노드 속성 업데이트
```json
{
  "neo4j_updates": [
    {
      "character_name": "서진",
      "property_updates": {
        "current_emotion": "분노",
        "emotion_intensity": 8,
        "emotion_valence": "negative"
      }
    }
  ]
}
```

### 💡 향후 개선 사항 (Event Sourcing)

현재 방식은 캐릭터 노드의 속성을 덮어쓰기(Overwrite)합니다.
감정 변화의 역사(History)를 추적해야 한다면:

**현재 (State Update)**:
```cypher
SET (Character).emotion = "분노"
```

**고도화 (Event Graph)**:
```cypher
CREATE (c:Character)-[:FELT {timestamp: t, chapter: 3}]->(e:Emotion {type: "분노"})
```

→ 스토리 진행에 따른 감정 변화 궤적(Trajectory) 분석 가능

### 📁 수정된 파일
- `app/agents/extraction/emotion.py` - 프롬프트 Production Level 업그레이드
- `tests/test_agents/test_emotion_tracking.ipynb` - 테스트 노트북 상세화

### ✅ 결과
- `emotion_states`: 상세 감정 분석 (trigger, expression, is_hidden)
- `neo4j_updates`: Character 노드 속성 업데이트용 JSON
- Character Agent 이름과 정확히 매칭

---

## 5. Consistency Agent - Production Level 업그레이드

### 📅 날짜
2025-12-27

### 🔴 문제 (Problem)
1. Dialogue/Emotion Agent 결과를 활용하지 않음 (Level 1 데이터 미통합)
2. 관계 방향성 검증 없음 (BETRAYED/MENTOR는 단방향이어야 함)
3. 참조 무결성 검증 없음 (존재하지 않는 캐릭터 참조 가능)
4. Neo4j-ready 출력 구조 없음

**기존 검증 범위**:
- Character trait 충돌만 감지
- 단순 점수 계산 (HIGH: -25, MEDIUM: -10)

### 🟡 원인 분석 (Root Cause)
1. 초기 구현에서 Level 1 Agent 결과 통합을 고려하지 않음
2. 관계 방향성 규칙(BETRAYED: 배신자→피해자)이 프롬프트에 없음
3. 프로그래매틱 검증이 trait 충돌에만 한정됨

### 🟢 해결책 (Solution)

#### 1. Level 1 Agent 데이터 통합
```python
dialogues = state.get("analyzed_dialogues", {})
emotions = state.get("tracked_emotions", {})
```

#### 2. 충돌 유형 확장
| 충돌 유형 | Severity | 설명 |
|----------|----------|------|
| `CHARACTER_TRAIT_CONFLICT` | HIGH | 모순된 성격 특성 |
| `DIRECTION_CONFLICT` | MEDIUM | BETRAYED/MENTOR 방향성 오류 |
| `REFERENTIAL_INTEGRITY_ERROR` | HIGH | 존재하지 않는 캐릭터 참조 |
| `DIALOGUE_CONSISTENCY_CONFLICT` | LOW-MEDIUM | 대화 패턴-성격 불일치 |
| `EMOTION_CONSISTENCY_CONFLICT` | LOW-MEDIUM | 감정-행동 불일치 |

#### 3. 프로그래매틱 검증 확장
```python
def validate_relationship_directions(relationships: list) -> list:
    """BETRAYED/MENTOR는 bidirectional=false여야 함"""
    ...

def validate_character_references(relationships: list, available_names: set) -> list:
    """모든 source/target이 character list에 존재해야 함"""
    ...
```

#### 4. Neo4j-Ready 출력 추가
```json
{
  "neo4j_validation": {
    "is_valid": true,
    "conflict_count": 0,
    "high_severity_count": 0
  }
}
```

### 📁 수정된 파일
- `app/agents/analysis/consistency.py` - Production Level 전면 개선
- `tests/test_agents/test_consistency_check.ipynb` - 7개 테스트 섹션으로 확장

### ✅ 결과
- Dialogue/Emotion 데이터 교차 검증
- 관계 방향성 자동 검증 (BETRAYED, MENTOR)
- 참조 무결성 자동 검증
- Neo4j 검증 결과 구조화된 출력

### 💡 추가 기능: 자동 해결 전략 (Auto-Resolution Strategy)

각 충돌에 `suggested_action` 및 `final_value_candidate` 필드 제공:

| Action | 설명 |
|--------|------|
| `KEEP_DB_VALUE` | 기존 DB 값 유지 |
| `OVERWRITE_WITH_NEW` | 새 값으로 덮어쓰기 (저위험) |
| `FLAG_FOR_HUMAN` | 인간 검토 필요 |
| `AUTO_FIX` | 시스템 자동 수정 가능 |

**🆕 final_value_candidate 구조** (AUTO_FIX 시):
```json
{
  "table": "relationships",
  "key": {"source": "이민호", "target": "서진", "relation_type": "BETRAYED"},
  "update": {"bidirectional": false}
}
```
→ 별도 연산 없이 바로 UPDATE 쿼리에 바인딩 가능!

**Resolution Summary 출력**:
```json
{
  "resolution_summary": {
    "auto_fixable": 2,
    "ready_for_update": 2,  // 🆕 바로 DB UPDATE 가능한 수
    "needs_human_review": 3,
    "total_conflicts": 6
  }
}
```

**백엔드 로직 예시**:
```python
for conflict in conflicts:
    if conflict['suggested_action'] == 'AUTO_FIX':
        fvc = conflict['final_value_candidate']
        # 바로 UPDATE 쿼리 실행 가능!
        db.execute(f\"\"\"
            UPDATE {fvc['table']} 
            SET {', '.join(f'{k}={v}' for k,v in fvc['update'].items())}
            WHERE source='{fvc['key']['source']}' AND target='{fvc['key']['target']}'
        \"\"\")
```

---

## 6. Plot Integration Agent - Production Level 업그레이드

### 📅 날짜
2025-12-27

### 🔴 문제 (Problem)
1. 기본적인 프롬프트로 단순 요약만 제공
2. 멀티미디어 파이프라인에 필요한 시계열 데이터 없음
3. 이벤트/캐릭터 참조 없이 자체 이름 생성

**기존 출력**:
```json
{
  "plot_summary": "...",
  "foreshadowing": ["..."],
  "tension_level": 5
}
```

### 🟡 원인 분석 (Root Cause)
1. Tension이 단일 숫자로 시간 흐름에 따른 변화 표현 불가
2. 비트 단위 분할 없어 컷 연출/삽화 생성 활용 불가
3. Event Agent 결과 참조하지 않음

### 🟢 해결책 (Solution)

#### 1. Tension Curve 배열 도입
```json
"tension_curve": [3, 5, 7, 8, 6]
```
→ 오디오 빌드업(↑), 드롭(↓) 타이밍 자동 생성 가능

#### 2. Narrative Beats 분할
```json
"narrative_beats": [
  {
    "beat_id": 1,
    "text": "서진과 하나가 어두운 숲에서 만남",
    "beat_type": "SETUP",
    "event_ref": "E001",
    "visual_prompt": "Two figures meeting in dark forest"
  }
]
```
- `beat_type`: SETUP, INCITING_INCIDENT, CLIMAX 등
- `visual_prompt`: 삽화 AI 직접 입력 가능

#### 3. Multimedia Pipeline Summary
```json
{
  "multimedia_summary": {
    "beat_count": 5,
    "tension_curve_length": 5,
    "has_visual_prompts": true,
    "tension_range": {"min": 3, "max": 8, "peak_index": 3}
  }
}
```

### 📁 수정된 파일
- `app/agents/analysis/plot.py` - Production Level 업그레이드
- `tests/test_agents/test_plot_integration.ipynb` - 7개 섹션으로 확장

### ✅ 결과
- 3-Act 구조 + Foreshadowing + Neo4j 엣지
- Tension Curve 배열 (오디오/연출 타이밍용)
- Narrative Beats (컷 편집/삽화 프롬프트용)
- Multimedia Summary (파이프라인 검증용)

### 💡 추가 수정: Tension Curve 빈 배열 문제

**문제**: LLM이 `tension_curve`를 빈 배열 `[]`로 반환하는 경우 발생

**해결**: 프로그래매틱 백업 함수 추가
```python
def generate_fallback_tension_curve(events: list) -> list:
    """이벤트 importance로 tension 자동 생성"""
    return [max(1, min(10, e.get("importance", 5))) for e in events]

def generate_fallback_beats(events: list) -> list:
    """이벤트에서 narrative beats 자동 생성"""
    ...
```

**결과 (로그)**:
```
[PLOT] Generating fallback tension_curve from event importance
[PLOT] Beats: 5, Tension curve: [7, 9, 8, 8, 6]
```
→ Raw Data 배열이 항상 보장됨

---

## 템플릿 (새 이슈 추가 시 사용)

```markdown
## N. [에이전트명] - [문제 요약]

### 📅 날짜
YYYY-MM-DD

### 🔴 문제 (Problem)
[문제 설명]

### 🟡 원인 분석 (Root Cause)
[원인]

### 🟢 해결책 (Solution)
[해결 방법]

### 📁 수정된 파일
- [파일 목록]

### ✅ 결과
[결과]
```

