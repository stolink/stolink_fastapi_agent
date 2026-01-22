# StoLink Multi-Agent Architecture

> **Version**: 3.0.0  
> **Last Updated**: 2026-01-21  
> **Architecture Type**: LangGraph Supervisor Pattern  
> **Total Agents**: 8 (Character Team: 4개 서브에이전트 포함)

---

## 목차

1. [아키텍처 개요](#1-아키텍처-개요)
2. [에이전트 계층 구조](#2-에이전트-계층-구조)
3. [에이전트 상세 명세](#3-에이전트-상세-명세)
4. [파이프라인 흐름](#4-파이프라인-흐름)
5. [State 관리](#5-state-관리)
6. [Global Resolution](#6-global-resolution)
7. [개연성 검증 메커니즘](#7-개연성-검증-메커니즘)
8. [LLM 설정](#8-llm-설정)

---

## 1. 아키텍처 개요

### 1.1 설계 철학

StoLink AI 분석 시스템은 **LangGraph Supervisor Pattern**을 채택합니다:

| 원칙 | 설명 |
|------|------|
| **Task 격리** | 각 에이전트가 특화된 역할 수행 |
| **서브그래프 패턴** | Character Team은 4개 에이전트를 하나의 서브그래프로 묶음 |
| **재추출 루프** | Consistency 점수 낮으면 Extraction으로 회귀 |
| **Global Resolution** | 중복 캐릭터 병합 (Fuzzy Matching) |

### 1.2 전체 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────────┐
│                    🎯 SUPERVISOR (Router)                           │
│                 - 다음 단계 결정 및 라우팅                            │
│                 - 재추출 루프 제어                                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 📝 EXTRACTION   │    │ 🔄 RESOLUTION   │    │ 🔍 ANALYSIS     │
│    PHASE        │    │    PHASE        │    │    PHASE        │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ ┌─────────────┐ │    │ Global          │    │ Relationship    │
│ │ Character   │ │    │ Resolution      │    │ Agent           │
│ │ Team 🎭     │ │    │ (Fuzzy Match)   │    │                 │
│ │ (SubGraph)  │ │    │                 │    │ Consistency     │
│ └─────────────┘ │    │                 │    │ Agent           │
│ Setting Agent🌍 │    │                 │    │                 │
│ Event Agent 📅  │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                ▼
                    ┌─────────────────────┐
                    │  ✅ VALIDATION      │
                    │     PHASE           │
                    │ - 재추출 결정        │
                    │ - 최종 품질 검증     │
                    └─────────────────────┘
```

### 1.3 Character Team 서브그래프

```
┌─────────────────────────────────────────────────────────────────┐
│                    🎭 CHARACTER TEAM (SubGraph)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌───────────────┐    ┌───────────────┐    ┌───────────────┐  │
│   │ 🆔 Identity   │    │ 👁️ Appearance │    │ 💭 Personality│  │
│   │   Agent       │    │    Agent      │    │    Agent      │  │
│   │               │    │               │    │               │  │
│   │ - 이름/별칭   │    │ - 외모/복장   │    │ - 성격 특성   │  │
│   │ - 역할        │    │ - 시각적 특징 │    │ - 말투/행동   │  │
│   │ - 상태        │    │               │    │ - 동기        │  │
│   └───────────────┘    └───────────────┘    └───────────────┘  │
│           │                    │                    │          │
│           └────────────────────┼────────────────────┘          │
│                                ▼                               │
│                    ┌───────────────────┐                       │
│                    │ 🔗 Merge Agent    │                       │
│                    │                   │                       │
│                    │ - 4개 결과 병합   │                       │
│                    │ - FullCharacter   │                       │
│                    └───────────────────┘                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 에이전트 계층 구조

### 2.1 계층 정의

| Phase | 에이전트 | 역할 | 파일 위치 |
|-------|---------|------|----------|
| **Extraction** | 🎭 Character Team | 캐릭터 정보 추출 (서브그래프) | `agents/extraction/character/` |
| **Extraction** | 🌍 Setting Agent | 장소/배경 설정 추출 | `agents/extraction/setting.py` |
| **Extraction** | 📅 Event Agent | 사건/이벤트 추출 | `agents/extraction/event.py` |
| **Resolution** | 🔄 Global Resolution | 중복 캐릭터 병합 | `agents/analysis/global_resolution.py` |
| **Analysis** | 🔗 Relationship Agent | 관계 분석 | `agents/analysis/relationship.py` |
| **Analysis** | 🔍 Consistency Agent | 개연성 검사 | `agents/analysis/consistency.py` |
| **Validation** | ✅ Validator Agent | 최종 검증, 재추출 결정 | `agents/validation/validator.py` |

> **Note**: Dialogue Agent, Emotion Agent, Plot Agent는 현재 구현에서 제거됨

### 2.2 실행 순서

```
1. Supervisor → EXTRACTION 라우팅
       │
       ▼
2. Extraction Phase (병렬)
   ├── Character Team (Identity → Appearance → Personality → Merge)
   ├── Setting Agent
   └── Event Agent
       │
       ▼
3. Supervisor → GLOBAL_RESOLUTION 라우팅
       │
       ▼
4. Global Resolution
   └── Fuzzy Matching으로 중복 캐릭터 병합
       │
       ▼
5. Supervisor → ANALYSIS 라우팅
       │
       ▼
6. Analysis Phase (병렬)
   ├── Relationship Agent
   └── Consistency Agent
       │
       ▼
7. Supervisor → VALIDATION 라우팅
       │
       ▼
8. Validator
   ├── 점수 ≥ 20 (또는 ≥ 50)  → END
   └── 점수 < threshold       → EXTRACTION (재추출)
       │
       ▼
9. Supervisor → END 또는 Loop (max 2회)
```

---

## 3. 에이전트 상세 명세

### 3.1 Character Team (🎭 캐릭터 팀)

**구조**: 4개 에이전트로 구성된 서브그래프

| 에이전트 | 역할 | 추출 항목 |
|---------|------|----------|
| **Identity Agent** | 기본 정보 | 이름, 별칭, 역할, 상태 |
| **Appearance Agent** | 외모 정보 | 외모, 복장, 시각적 특징 |
| **Personality Agent** | 성격 정보 | 성격, 말투, 행동 패턴, 동기 |
| **Merge Agent** | 병합 | 3개 결과 → FullCharacter |

**출력 스키마** (`FullCharacter`):

```python
class FullCharacter(BaseModel):
    id: str
    name: str
    aliases: list[str]
    role: str  # PROTAGONIST, ANTAGONIST, SUPPORTING, MINOR
    status: str  # ALIVE, DEAD, UNKNOWN
    
    # Appearance
    appearance_description: str
    visual_traits: list[str]
    
    # Personality
    personality_traits: list[str]
    speech_pattern: str
    motivations: list[str]
    
    # Metadata
    first_appearance_chapter: int
    description: str
```

### 3.2 Setting Agent (🌍 장소/배경)

**역할**: 세계관, 장소, 배경 설정 추출

| 추출 항목 | 설명 |
|----------|------|
| `name` | 장소 이름 |
| `location_type` | 장소 유형 (CITY, BUILDING, NATURE 등) |
| `description` | 장소 설명 |
| `atmosphere` | 분위기 |
| `time_period` | 시대/시간대 |

### 3.3 Event Agent (📅 사건/이벤트)

**역할**: 스토리 사건, 시퀀스 추출

| 추출 항목 | 설명 |
|----------|------|
| `event_type` | 사건 유형 (ACTION, DIALOGUE, REVELATION 등) |
| `description` | 사건 설명 |
| `participants` | 참여 캐릭터 |
| `location` | 발생 장소 |
| `sequence_order` | 순서 |
| `emotional_tone` | 감정 톤 |
| `is_foreshadowing` | 복선 여부 |
| `narrative_summary` | 서사 요약 |

### 3.4 Relationship Agent (🔗 관계 분석)

**역할**: 캐릭터 간 관계 추론

| 필드 | 설명 |
|------|------|
| `source` | 관계 주체 캐릭터 |
| `target` | 관계 대상 캐릭터 |
| `relationship_type` | 관계 유형 (ALLY, ENEMY, FAMILY, ROMANTIC 등) |
| `strength` | 관계 강도 (1-10) |
| `bidirectional` | 양방향 여부 |
| `evidence` | 근거 |

### 3.5 Consistency Agent (🔍 개연성 검사)

**역할**: 스토리 일관성/개연성 검증

**15가지 충돌 유형**:

| 유형 | 심각도 | 설명 |
|------|--------|------|
| `TIMELINE_CONFLICT` | HIGH | 시간대 모순 |
| `CHARACTER_TRAIT_CONFLICT` | HIGH | 캐릭터 특성 모순 |
| `SETTING_CONFLICT` | HIGH | 설정 모순 |
| `RELATIONSHIP_CONFLICT` | HIGH | 관계 모순 |
| `PLOT_HOLE` | MEDIUM | 플롯 구멍 |
| `CROSS_CHAPTER_CONFLICT` | MEDIUM | 챕터 간 모순 |
| `RESURRECTION_ERROR` | HIGH | 사망 캐릭터 재등장 |
| `POWER_INCONSISTENCY` | MEDIUM | 능력 일관성 |
| `KNOWLEDGE_CONFLICT` | MEDIUM | 지식 모순 |
| `LOCATION_CONFLICT` | MEDIUM | 위치 모순 |
| `OBJECT_CONFLICT` | LOW | 물건 모순 |
| `MINOR_DETAIL_CONFLICT` | LOW | 사소한 디테일 |
| `MOTIVATION_CONFLICT` | MEDIUM | 동기 모순 |
| `DIALOGUE_INCONSISTENCY` | LOW | 대화 불일치 |
| `WORLD_RULE_VIOLATION` | HIGH | 세계관 규칙 위반 |

**점수 계산**:

```
초기 점수 = 100

HIGH 충돌 1개당: -15점
MEDIUM 충돌 1개당: -8점
LOW 충돌 1개당: -3점

최종 점수 = max(0, 100 - 차감합계)
```

**재추출 트리거**:

| 조건 | 임계값 | 동작 |
|------|--------|------|
| 일반 텍스트 | score ≤ 50 | 재추출 |
| 짧은 텍스트 | score ≤ 20 | 재추출 |
| HIGH 충돌 3개 이상 | - | 재추출 |

---

## 4. 파이프라인 흐름

### 4.1 LangGraph 그래프 정의

```python
from langgraph.graph import StateGraph, START, END

def create_analysis_graph():
    graph = StateGraph(AnalysisState)
    
    # 노드 등록
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("extraction", extraction_node)
    graph.add_node("global_resolution", global_resolution_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("validation", validation_node_wrapper)
    
    # 엣지 정의
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", supervisor_router)
    
    graph.add_edge("extraction", "supervisor")
    graph.add_edge("global_resolution", "supervisor")
    graph.add_edge("analysis", "supervisor")
    graph.add_edge("validation", "supervisor")
    
    return graph.compile()
```

### 4.2 Supervisor 라우팅 로직

```python
def supervisor_router(state: dict) -> str:
    """다음 실행할 노드 결정"""
    
    if not state.get("extraction_done"):
        return "extraction"
    
    if not state.get("resolution_done"):
        return "global_resolution"
    
    if not state.get("analysis_done"):
        return "analysis"
    
    if not state.get("validation_done"):
        return "validation"
    
    # 재추출 필요 여부 확인
    consistency = state.get("consistency_report", {})
    if consistency.get("requires_reextraction") and state.get("retry_count", 0) < 2:
        return "extraction"  # 루프
    
    return END
```

---

## 5. State 관리

### 5.1 AnalysisState 정의

```python
from typing import TypedDict, Annotated
import operator

class AnalysisState(TypedDict):
    # 입력
    content: str
    project_id: str
    document_id: str
    job_id: str
    callback_url: str
    
    # 추출 결과
    extracted_characters: list   # FullCharacter 리스트
    extracted_events: list       # Event 리스트
    extracted_settings: list     # Setting 리스트
    
    # 분석 결과
    relationship_graph: dict     # 관계 그래프
    consistency_report: dict     # 개연성 보고서
    validation_result: dict      # 검증 결과
    
    # 기존 데이터 (참조용)
    existing_characters: list
    existing_events: list
    existing_relationships: list
    existing_settings: list
    
    # 제어 플래그
    extraction_done: bool
    resolution_done: bool
    analysis_done: bool
    validation_done: bool
    retry_count: int
    
    # 메시지/에러
    messages: Annotated[list, operator.add]
    errors: Annotated[list, operator.add]
```

---

## 6. Global Resolution

### 6.1 목적

LLM이 같은 캐릭터를 다른 이름으로 추출한 경우 **하나의 캐릭터로 병합**

예: `"리안"`, `"Lian"`, `"마법사 리안"` → Primary: `"리안"`

### 6.2 매칭 알고리즘

1. **정확 일치**: 정규화된 이름 비교
2. **한글-영문 매핑**: 로마자 변환 테이블
3. **별칭 교차 매칭**: aliases 필드 확인
4. **Fuzzy Matching**: rapidfuzz 가중 평균

```
가중평균 = (fuzz.ratio × 0.5) + (fuzz.partial_ratio × 0.3) + (fuzz.token_sort_ratio × 0.2)
```

### 6.3 분류 기준

| 점수 | 분류 | 동작 |
|------|------|------|
| ≥ 95 | AUTO_MERGE | 자동 병합 |
| 80-94 | NEEDS_REVIEW | 검토 필요 플래그 |
| < 80 | DIFFERENT | 별개 캐릭터 |

---

## 7. 개연성 검증 메커니즘

### 7.1 검증 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                    Consistency Check Flow                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   1. 현재 추출 데이터 수집                                        │
│      ├── Characters                                              │
│      ├── Events                                                  │
│      └── Relationships                                           │
│                          │                                       │
│                          ▼                                       │
│   2. RAG: 히스토리 컨텍스트 조회                                  │
│      ├── retrieve_relevant_history()                             │
│      └── 유사 캐릭터/이벤트 검색 (Neo4j Vector)                   │
│                          │                                       │
│                          ▼                                       │
│   3. LLM 기반 충돌 분석                                          │
│      ├── 15가지 충돌 유형 검사                                   │
│      └── 심각도별 점수 차감                                      │
│                          │                                       │
│                          ▼                                       │
│   4. 프로그래밍 백업 검증                                         │
│      ├── detect_trait_contradictions()                           │
│      └── validate_relationship_directions()                      │
│                          │                                       │
│                          ▼                                       │
│   5. 최종 ConsistencyReport 생성                                 │
│      ├── overall_score                                           │
│      ├── conflicts[]                                             │
│      └── requires_reextraction                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 프로그래밍 백업 검증

#### 모순 특성 탐지

```python
CONTRADICTORY_TRAITS = [
    ("brave", "coward"), ("용감한", "겁쟁이"),
    ("honest", "liar"), ("정직한", "거짓말쟁이"),
    ("kind", "cruel"), ("친절한", "잔인한"),
    # ...
]

def detect_trait_contradictions(characters: list) -> list[Conflict]:
    for char in characters:
        traits = char.get("traits", [])
        for t1, t2 in CONTRADICTORY_TRAITS:
            if t1 in traits and t2 in traits:
                # HIGH severity conflict
```

#### 관계 방향성 검증

```python
def validate_relationship_directions(relationships: list) -> list[Conflict]:
    for rel in relationships:
        if rel["type"] in ["BETRAYED", "MENTOR"] and rel.get("bidirectional"):
            # MEDIUM severity - 이 관계는 단방향이어야 함
```

---

## 8. LLM 설정

### 8.1 LLM 티어 구성

| 티어 | Model | 용도 | 비용 |
|------|-------|------|------|
| 🥉 **Basic** | `gemini-2.0-flash-lite` | 간단한 분류, 라우팅 | 최저 |
| 🥈 **Standard** | `gemini-2.5-flash-lite` | 정보 추출, 요약 | 저 |
| 🥇 **Advanced** | `gemini-2.5-flash` | 복잡한 추론, 관계 분석 | 중 |
| 💎 **Premium** | `gemini-3-flash-preview` | 핵심 분석 (개연성 검사) | 고 |

### 8.2 에이전트별 티어 배정

| 에이전트 | 티어 | 이유 |
|---------|------|------|
| Supervisor | Basic | 단순 라우팅 |
| Identity Agent | Standard | 정보 추출 |
| Appearance Agent | Standard | 정보 추출 |
| Personality Agent | Standard | 정보 추출 |
| Merge Agent | Basic | 데이터 병합 |
| Setting Agent | Standard | 정보 추출 |
| Event Agent | Standard | 정보 추출 |
| Relationship Agent | Advanced | 복잡한 관계 추론 |
| **Consistency Agent** | **Premium** | **핵심! 충돌 감지** |
| Validator | Basic | 단순 검증 |

### 8.3 Structured Output

모든 에이전트는 **Pydantic 스키마**를 사용하여 구조화된 출력 강제:

```python
from langchain_core.output_parsers import PydanticOutputParser

parser = PydanticOutputParser(pydantic_object=FullCharacter)
chain = prompt | llm.with_structured_output(FullCharacter)
```

### 8.4 LLM 팩토리

```python
# app/agents/llm.py
def get_llm(tier: str = "standard"):
    model_map = {
        "basic": "gemini-2.0-flash-lite",
        "standard": "gemini-2.5-flash-lite",
        "advanced": "gemini-2.5-flash",
        "premium": "gemini-3-flash-preview",
    }
    return ChatGoogleGenerativeAI(model=model_map[tier], temperature=0)
```

---

## Appendix: 파일 구조

```
app/agents/
├── graph.py                    # 메인 파이프라인
├── supervisor.py               # Supervisor 라우터
├── state.py                    # AnalysisState 정의
├── llm.py                      # LLM 팩토리
│
├── extraction/
│   ├── character/              # Character Team (서브그래프)
│   │   ├── identity.py         # Identity Agent
│   │   ├── appearance.py       # Appearance Agent
│   │   ├── personality.py      # Personality Agent
│   │   ├── merge.py            # Merge Agent
│   │   └── team.py             # Team 오케스트레이션
│   ├── event.py                # Event Agent
│   └── setting.py              # Setting Agent
│
├── analysis/
│   ├── relationship.py         # Relationship Agent
│   ├── consistency.py          # Consistency Agent
│   └── global_resolution.py    # Global Resolution
│
└── validation/
    └── validator.py            # Validator Agent
```
