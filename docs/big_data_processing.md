# StoLink AI Backend - 시스템 아키텍처 문서

> **Last Updated**: 2026-01-01

---

## 현재 시스템 구조 (Current Architecture)

### 📅 날짜
2026-01-01

### 🎯 현재 시스템 개요
**단일 텍스트 분석** 중심의 Multi-Agent LangGraph 파이프라인

---

## 1️⃣ 시스템 아키텍처 (Current)

### 전체 흐름
```
┌──────────────────────────────────────────────────────────────────────────┐
│                        현재 시스템 데이터 흐름                             │
│                                                                          │
│  ┌────────────┐      ┌─────────────┐     ┌──────────────┐                │
│  │ Spring Boot│────▶│  RabbitMQ   │────▶│ Python Worker│                │
│  │  (Publisher)│     │   Queue     │     │  (Consumer)  │                │
│  └────────────┘      └─────────────┘     └──────┬───────┘                │
│                                                 │                        │
│                                    ┌────────────▼───────────┐            │
│                                    │   LangGraph Pipeline   │            │
│                                    │   (Multi-Agent System) │            │
│                                    └────────────┬───────────┘            │
│                                                 │                        │
│                      ┌─────────────────────────▼────────────────────── ┐ │
│                      │              Callback to Spring Boot            │ │
│                      │   POST /api/ai-callback/{jobId}/analysis-result │ │
│                      └─────────────────────────┬────────────────────── ┘ │
│                                                 │                        │
│                                    ┌────────────▼───────────┐            │
│                                    │  PostgreSQL + Neo4j    │            │
│                                    │    (Data Persistence)  │            │
│                                    └────────────────────────┘            │
└──────────────────────────────────────────────────────────────────────────┘
```

### 메시지 스키마 (RabbitMQ)
```json
{
  "job_id": "story-001",
  "project_id": "proj-001", 
  "document_id": "doc-001",
  "callback_url": "http://spring-backend:8080/api/ai-callback",
  "content": "전체 스토리 텍스트... (단일 문서)",
  "context": {
    "existing_characters": [{"id": "char-001", "name": "이안", "role": "protagonist"}],
    "existing_events": [{"id": "evt-001", "event_type": "ENCOUNTER", "summary": "..."}],
    "existing_relationships": [...],
    "existing_settings": [...]
  },
  "trace_id": "req-20260101-abc123"
}
```

---

## 2️⃣ LangGraph 파이프라인 구조

### Supervisor 패턴 (Main Graph)
```
┌─────────────────────────────────────────────────────────────────┐
│                      Main Analysis Graph                        │
│                                                                 │
│   START ──▶ Supervisor ──┬──▶ Extraction ──▶ Supervisor       │
│                          │                                      │
│                          ├──▶ Analysis ──▶ Supervisor          │
│                          │                                      │
│                          ├──▶ Validation ──▶ Supervisor        │
│                          │                                      │
│                          └──▶ END (또는 재시도 루프)             │
└─────────────────────────────────────────────────────────────────┘
```

### Extraction 노드 상세
```
┌─────────────────────────────────────────────────────────────────┐
│                     Extraction Node (2-Phase)                    │
│                                                                 │
│   Phase 1: Master Data (병렬)                                    │
│   ┌───────────────────┐    ┌───────────────────┐               │
│   │  Character Team   │    │   Setting Agent   │               │
│   │  (Hierarchical)   │    │                   │               │
│   └────────┬──────────┘    └────────┬──────────┘               │
│            │                         │                          │
│            └────────────┬────────────┘                          │
│                         ▼                                       │
│   Phase 2: Narrative Flow (순차)                                 │
│   ┌───────────────────────────────────────────┐                │
│   │              Event Agent                   │                │
│   │  (Character + Setting 결과 참조)           │                │
│   └───────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

### Character Team (Hierarchical Multi-Agent)
```
┌─────────────────────────────────────────────────────────────────┐
│                     Character Team Graph                         │
│                                                                 │
│   char_supervisor ──▶ identity ──▶ char_supervisor              │
│                                                                 │
│                  ──▶ parallel_batch ──▶ char_supervisor         │
│                        ┌────────────────────────────┐           │
│                        │ appearance   (병렬 실행)     │           │
│                        │ personality                │           │
│                        │ relations                  │           │
│                        │ dialogue_mood              │           │
│                        └────────────────────────────┘           │
│                                                                 │
│                  ──▶ aggregator ──▶ END                         │
└─────────────────────────────────────────────────────────────────┘
```

### Analysis 노드 (병렬)
```
┌─────────────────────────────────────────────────────────────────┐
│                      Analysis Node (병렬)                        │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │ Relationship │  │ Consistency  │  │    Plot      │         │
│   │   Analyzer   │  │   Checker    │  │  Integrator  │         │
│   └──────────────┘  └──────────────┘  └──────────────┘         │
│          │                 │                 │                  │
│          └─────────────────┴─────────────────┘                  │
│                            ▼                                    │
│                    asyncio.gather()                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3️⃣ 에이전트 목록 및 역할

### Extraction Agents (데이터 추출)

| 에이전트 | 파일 | 역할 |
|----------|------|------|
| **Character Team** | `extraction/character/supervisor.py` | 캐릭터 정보 추출 총괄 |
| ├─ Identity | `extraction/character/identity.py` | 이름, 역할, 별칭, 상태 |
| ├─ Appearance | `extraction/character/appearance.py` | 외모, 복장, 아트 스타일 |
| ├─ Personality | `extraction/character/personality.py` | 성격, 가치관, 결점 |
| ├─ Relations | `extraction/character/relations.py` | 캐릭터 간 관계 그래프 |
| ├─ Dialogue/Mood | `extraction/character/dialogue_mood.py` | 대화 패턴, 현재 감정 |
| └─ Aggregator | `extraction/character/aggregator.py` | 서브에이전트 결과 병합 |
| **Setting Agent** | `extraction/setting.py` | 배경, 장소, 분위기 |
| **Event Agent** | `extraction/event.py` | 사건, 타임라인, 참여자 |

### Analysis Agents (데이터 분석)

| 에이전트 | 파일 | 역할 |
|----------|------|------|
| **Relationship** | `analysis/relationship.py` | 관계 네트워크 분석 |
| **Consistency** | `analysis/consistency.py` | 모순점 감지 + RAG |
| **Plot** | `analysis/plot.py` | 플롯 구조 + Tension Curve |

### Validation Agent

| 에이전트 | 파일 | 역할 |
|----------|------|------|
| **Validator** | `validation/validator.py` | 스키마 검증 + 품질 점수 |

---

## 4️⃣ 상태 스키마 (AnalysisState)

```python
class AnalysisState(TypedDict, total=False):
    # === 입력 (불변) ===
    content: str              # 전체 스토리 텍스트
    project_id: str
    document_id: str
    job_id: str
    callback_url: str
    trace_id: str             # 분산 추적 ID
    
    # === 기존 데이터 (Spring Boot Context) ===
    existing_characters: list
    existing_events: list
    existing_relationships: list
    existing_settings: list
    
    # === 추출 결과 ===
    extracted_characters: list  # FullCharacter 스키마
    extracted_events: list      # EventExtraction 스키마
    extracted_settings: list    # SettingExtraction 스키마
    
    # === 분석 결과 ===
    relationship_graph: dict
    consistency_report: dict
    plot: dict
    
    # === 검증 ===
    validation_result: dict
    
    # === 제어 플래그 ===
    extraction_done: bool
    analysis_done: bool
    validation_done: bool
    retry_count: int           # 최대 3회 재시도
    
    # === 누적 필드 ===
    messages: list
    errors: list
```

---

## 5️⃣ 출력 스키마 (Callback Payload)

```json
{
  "job_id": "story-001",
  "status": "completed",
  "results": {
    "characters": [
      {
        "_id": "char-이안-001",
        "role": "protagonist",
        "profile": {
          "character_id": "char-이안-001",
          "name": "이안",
          "age": 28,
          "gender": "male",
          "backstory": "...",
          "faction": {"name": "아키비스트", "social": {...}}
        },
        "aliases": ["Ian"],
        "status": "alive",
        "appearance": {
          "physique": "athletic",
          "skin_tone": "fair",
          "eyes": "brown",
          "attire": ["망토", "가방"],
          "style_context": {"art_style": "Digital Illustration, Concept Art"}
        },
        "relations": {
          "graph": [
            {"target": "지아", "type": "FAMILY", "strength": 10, ...}
          ],
          "event_refs": ["E001", "E002"]
        },
        "current_mood": {"emotion": "결의", "intensity": 7, "trigger": "..."},
        "embedding": [0.123, -0.456, ...],  // 1536차원
        "meta": {"data_version": "2.0.0"}
      }
    ],
    "events": [...],
    "settings": [...],
    "relationship_graph": {...},
    "plot": {...},
    "consistency_report": {...},
    "validation_result": {...}
  },
  "processing_time_ms": 45000
}
```

---

## 6️⃣ 저장소 역할 분리 (Current)

```
┌───────────────────────────────────────────────────────┐
│                  현재 저장소 구조                       │
│                                                       │
│  ┌─────────────────┐    ┌─────────────────┐          │
│  │   PostgreSQL    │    │     Neo4j       │          │
│  │   (Spring Boot) │    │   (Spring Boot) │          │
│  └─────────────────┘    └─────────────────┘          │
│          ↑                      ↑                    │
│   - Project 메타데이터     - Character Node          │
│   - Job 상태               - Event Node              │
│   - 원본 텍스트 (S3 참조)   - Setting Node            │
│                           - Relationships           │
│                           - embedding (벡터 검색)    │
└───────────────────────────────────────────────────────┘

※ FastAPI는 쓰기 권한 없음 (Callback으로 Spring Boot에 전달)
※ FastAPI는 읽기 전용 DB 조회 가능 (db_query_service.py)
```

---

## 7️⃣ 현재 시스템의 특징 및 한계

### ✅ 강점

| 항목 | 설명 |
|------|------|
| **Multi-Agent** | 역할별 전문화된 에이전트 |
| **Supervisor 패턴** | 재시도 루프 + 품질 제어 |
| **Hierarchical** | Character Team 내부 2단계 병렬화 |
| **existing_* 지원** | 기존 캐릭터 ID 재사용 가능 |
| **Embedding 생성** | 캐릭터/이벤트 벡터 (Neo4j 벡터 검색용) |

### ⚠️ 한계

| 항목 | 설명 |
|------|------|
| **단일 문서 처리** | 전체 텍스트를 한 번에 분석 |
| **메모리 제한** | 대용량 소설 (100만자+) 처리 어려움 |
| **순차 처리** | 챕터별 분할 분석 미지원 |
| **실시간 피드백 없음** | 분석 완료까지 상태 알림 없음 |

6000자 기준 약 1분 20 ~ 40초 걸림

---

## 8️⃣ 주요 파일 구조

```
app/
├── agents/
│   ├── graph.py              # Main LangGraph 정의
│   ├── supervisor.py         # Supervisor 로직
│   ├── state.py              # AnalysisState 정의
│   ├── llm.py                # LLM 설정 (Gemini/AWS Bedrock)
│   │
│   ├── extraction/
│   │   ├── character/
│   │   │   ├── supervisor.py     # Character Team 그래프
│   │   │   ├── identity.py
│   │   │   ├── appearance.py
│   │   │   ├── personality.py
│   │   │   ├── relations.py
│   │   │   ├── dialogue_mood.py
│   │   │   ├── aggregator.py
│   │   │   └── state.py
│   │   ├── event.py
│   │   └── setting.py
│   │
│   ├── analysis/
│   │   ├── relationship.py
│   │   ├── consistency.py
│   │   └── plot.py
│   │
│   └── validation/
│       └── validator.py
│
├── schemas/
│   ├── messages.py           # RabbitMQ 메시지 스키마
│   ├── characters.py         # FullCharacter 스키마
│   ├── events.py             # EventExtraction 스키마
│   └── settings.py           # SettingExtraction 스키마
│
├── services/
│   ├── rabbitmq_consumer.py  # 메시지 수신
│   ├── analysis_service.py   # 파이프라인 실행
│   ├── callback_client.py    # Spring Boot 콜백
│   └── db_query_service.py   # 읽기 전용 DB 조회
│
└── config.py                 # 환경 설정
```

---

---

## 제안된 아키텍처 (Proposed Architecture)



## 1️⃣ 제안된 워크플로우 (Original Workflow)

### 시스템 아키텍처 (3단계)
1. **Ingestion (Spring)**: 원본 저장 및 1차 물리 분할 (초고속)
2. **Processing (Python)**: 2차 논리/의미 분할 및 AI 분석 (정밀)
3. **Serving (Client)**: 결과 시각화 (지연 로딩)

### Phase 1: 업로드 및 초고속 초기화 (Client → Spring) - **0.5초 목표**
| 단계 | 작업 | 설명 |
|------|------|------|
| 1 | 파일 수신 | `POST /api/projects/upload` |
| 2 | S3 저장 | `raw/{uuid}.txt` 즉시 업로드 (Safety First) |
| 3 | Project 생성 | DB `project` 테이블 레코드 생성 |
| 4 | Regex 분할 | Java 정규식으로 365개 챕터 분할 |
| 5 | Bulk Insert | `chapter` 테이블에 365개 레코드 한 번에 저장 |
| 6 | 메시지 발행 | RabbitMQ에 365개 메시지 Fan-out |
| 7 | 응답 리턴 | `200 OK + projectId` (사용자는 즉시 챕터 목록 확인 가능) |

### Phase 2: 비동기 정밀 분석 (RabbitMQ → Python)
| 단계 | 작업 | 설명 |
|------|------|------|
| 1 | 메시지 수신 | 워커(1~10)가 `chapterId` 가져감 |
| 2 | DB 조회 | `chapter` 테이블에서 content 조회 |
| 3 | Semantic Chunking | 문장 임베딩 → 의미 단위 분할 |
| 4 | AI 요약 | LLM으로 `nav_title` 생성 |
| 5 | 섹션 저장 | `section` 테이블에 Bulk Insert |
| 6 | 상태 갱신 | `chapter.status = COMPLETED` |

### Phase 3: 결과 조회 (Client ↔ Spring)
- SSE/폴링으로 챕터 상태 실시간 갱신
- 완료된 챕터 클릭 시 `GET /api/chapters/{id}/sections` 호출

---

## 2️⃣ 사용자 질문 및 시니어 개발자 응답

### Q1: RabbitMQ에 content를 담는 것 vs DB 조회?

**응답: DB 조회 방식 압도적 유리 (Claim Check Pattern)**

| 기준 | Content 포함 | ID만 전송 |
|------|-------------|-----------|
| RabbitMQ 부하 | 높음 (OOM 위험) | 낮음 |
| 재시도 비용 | 높음 | 낮음 (ID만 재전송) |
| 데이터 일관성 | 메시지 시점 고정 | 항상 최신 |

**권장 Flow:**
```
RabbitMQ: {"projectId": 1, "chapterId": 101}  (가벼움)
     ↓
Python: SELECT content FROM chapter WHERE id=101
```

### Q2: 문장 임베딩 vs Neo4j 활용?

**응답: 하이브리드 전략 추천**

1. **문장 임베딩 기반 Semantic Chunking** (Base)
   - 앞/뒷 문장 유사도 급락점 = 장면 전환점
   - 사람이 느끼는 "문단 전환"을 기계적으로 탐지

2. **Neo4j 메타데이터 태깅** (Enrichment)
   - 분할된 Section에 캐릭터/이벤트 키워드 매핑
   - `relates_to: ['철수', '영희']` 태그 추가
   - RAG 검색 시 메타데이터 필터 활용

---

## 3️⃣ 추가 고려사항 및 질문 (Antigravity 분석)

### A. 챕터 간 캐릭터 일관성 문제

**질문**: 1장에서 추출된 `char-이안-001`이 50장에서도 동일 인물로 인식되나?

**분석 결과**: ✅ **이미 지원됨**
```python
# aggregator.py (라인 546-580)
existing_char = existing_lookup.get(canonical_name)
if existing_char:
    char_id = existing_char.get("id", ...)  # ID 재사용
```

**조건**: `existing_characters`로 이전 챕터 캐릭터 전달 필요

### B. 순차 vs 병렬 처리

| 방식 | 장점 | 단점 |
|------|------|------|
| 순차 처리 | 맥락 정확 | 느림 (180분+) |
| 병렬 처리 | 빠름 | "그녀" 등 대명사 해석 불가 |

### C. 0.5초 목표 달성 가능성

**RabbitMQ 기본 설정**: 365개 메시지 개별 발행 → **불가능**
**Batch 모드 필요**: 네트워크 왕복 1회로 365개 발행 → **가능**

### D. 실시간 상태 폴링

**추천**: SSE + Redis Pub/Sub
- 폴링보다 DB 부하 감소
- WebSocket보다 구현 간단

### E. 챕터 분할 Fallback

**문제**: 모든 소설이 `제1장`, `Chapter 1` 패턴을 따르지 않음

### F. Section 임베딩 저장소

**질문**: 캐릭터/이벤트는 Neo4j, Section 임베딩은 어디에?

---

## 4️⃣ 사용자 후속 질문에 대한 답변

### Q1: 챕터별 분석 시 동일 캐릭터 인식 테스트?

**답변**: 현재 시스템 이미 `existing_characters` 기반 ID 재사용 지원

**워크플로우:**
```
챕터 N 분석 완료 → DB에 캐릭터 저장
     ↓
챕터 N+1 분석 요청 → DB에서 기존 캐릭터 조회 → context.existing_characters로 전달
     ↓
Python이 이름 매칭 + ID 재사용
```

### Q2: 캐릭터 ID 일관성 유지 전략?

**추천: 순차-증분 분석**
```json
POST /api/analysis/chapter/{chapterId}
{
  "content": "챕터 50 텍스트...",
  "context": {
    "existing_characters": [
      {"id": "char-이안-001", "name": "이안", "aliases": ["Ian"]}
    ]
  }
}
```

### Q3: 순차 vs 병렬?

**추천: 2-Pass 하이브리드 전략**

| Pass | 방식 | 목적 | 속도 |
|------|------|------|------|
| 1차 | 병렬 (10 워커) | 기본 추출 | 빠름 (~20분) |
| 2차 | 순차 + 병합 | ID 통합, 관계 연결 | 느림 (~5분) |

**총 25분** (순차만 할 경우 180분+)

### Q4: 0.5초 메시지 발행?

**RabbitMQ Batch 모드로 가능:**
```java
rabbitTemplate.invoke(operations -> {
    for (ChapterMessage msg : messages) {
        operations.convertAndSend(EXCHANGE, ROUTING_KEY, msg);
    }
    operations.waitForConfirms(5000);
    return true;
});
```

**다른 MQ 불필요** - RabbitMQ Batch로 충분

### Q5: SSE 추천 이유?

| 기준 | 폴링 | SSE | WebSocket |
|------|------|-----|-----------|
| 서버 부하 | 높음 | 낮음 | 낮음 |
| HTTP 호환 | ✅ | ✅ | ❌ |
| 양방향 | ❌ | ❌ | ✅ |
| 복잡도 | 쉬움 | 보통 | 어려움 |

**SSE 추천 이유:**
1. 상태 알림은 **서버→클라이언트 단방향**이면 충분
2. HTTP 기반으로 **프록시/로드밸런서 친화적**
3. WebSocket보다 **구현 간단**

### Q6: 챕터 분할 Fallback?

**Cascading Fallback 추천:**
```java
public List<Chapter> splitChapters(String rawText) {
    // 1차: 명시적 마커 (제1장, Chapter 1)
    List<Chapter> chapters = splitByExplicitMarkers(rawText);
    if (!chapters.isEmpty()) return chapters;
    
    // 2차: 빈 줄 + 제목 패턴 (### 또는 **굵은**)
    chapters = splitByParagraphHeaders(rawText);
    if (!chapters.isEmpty()) return chapters;
    
    // 3차: 빈 줄 기반
    chapters = splitByDoubleNewline(rawText);
    if (chapters.size() >= 10) return chapters;
    
    // 4차: 고정 글자 수 + 문장 경계 존중 (10,000자)
    return splitByCharacterCount(rawText, 10000, true);
}
```

### Q7: Section 임베딩 저장소?

**추천: PostgreSQL + pgvector**

| 옵션 | 장점 | 단점 |
|------|------|------|
| **PostgreSQL + pgvector** | 운영 단순, 기존 인프라 | 10M+ 시 성능 한계 |
| Neo4j Vector | 그래프 통합 | 느림 |
| Qdrant | 최고 성능 | 추가 인프라 |

**역할 분리:**
- **Neo4j**: 캐릭터/이벤트 관계 (그래프 쿼리)
- **PostgreSQL(pgvector)**: Section 임베딩 (의미 검색)

**Section 테이블 설계:**
```sql
CREATE TABLE section (
    id BIGSERIAL PRIMARY KEY,
    chapter_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL,
    nav_title VARCHAR(100),
    content TEXT NOT NULL,
    sequence_order INT NOT NULL,
    embedding vector(1536),              -- pgvector
    related_characters TEXT[],           -- Neo4j 메타데이터 태깅
    related_events TEXT[]
);

CREATE INDEX idx_section_embedding ON section 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
```

---

## 5️⃣ 최종 추천 요약

### 아키텍처 결정

| 항목 | 추천 |
|------|------|
| 메시지 전송 | **Claim Check Pattern** (ID만 전송, DB에서 content 조회) |
| 챕터 분할 | **Cascading Fallback** (명시적 마커 → 빈 줄 → 고정 글자수) |
| 처리 방식 | **2-Pass 하이브리드** (병렬 추출 → 글로벌 병합) |
| 메시지 큐 | **RabbitMQ Batch 모드** (변경 불필요) |
| 상태 폴링 | **SSE + Redis Pub/Sub** |
| 임베딩 저장 | **PostgreSQL + pgvector** (Section) / **Neo4j** (Character/Event) |

### 최종 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Ingestion (Spring) - 0.5초 목표                         │
│                                                                 │
│  Client → Spring → S3 (원본) + PostgreSQL (chapters) + RabbitMQ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: Processing (Python) - 비동기                            │
│                                                                 │
│  1차 Pass (병렬): 10 워커 × 365 챕터 → 기본 추출 (~20분)          │
│  2차 Pass (순차): ID 통합 + 관계 연결 + 모순 감지 (~5분)          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Serving (Client)                                       │
│                                                                 │
│  SSE로 상태 수신 → 완료된 챕터 클릭 → Section 텍스트 + 메타데이터 │
└─────────────────────────────────────────────────────────────────┘
```

### 저장소 역할 분리

```
┌───────────────────────────────────────────────────────┐
│                    저장소 역할 분리                     │
│                                                       │
│  ┌─────────────────┐    ┌─────────────────┐          │
│  │   PostgreSQL    │    │     Neo4j       │          │
│  │   + pgvector    │    │                 │          │
│  └─────────────────┘    └─────────────────┘          │
│          ↑                      ↑                    │
│   - project, chapter      - Character Node          │
│   - section + embedding   - Event Node              │
│   - 의미 검색 (RAG)        - Relationships          │
│                           - 그래프 쿼리              │
└───────────────────────────────────────────────────────┘
```

---

### 📁 관련 파일 (향후 구현 시)
- `app/agents/extraction/character/aggregator.py` - existing_characters 활용 로직
- `app/services/section_service.py` - 신규 (Section 저장 + 임베딩)
- `app/services/chunking_service.py` - 신규 (Semantic Chunking)
- Spring Boot: `ChapterSplitService.java`, `RabbitMQBatchPublisher.java`

---

---

## 6️⃣ 시니어 개발자 피드백 (Critical Success Factors)

### 📅 날짜
2026-01-01

---

### CSF 1: Ingestion 단계 트랜잭션 보장

**문제**: DB Insert와 RabbitMQ 발행의 원자성 미보장 시 챕터 분석 누락

**옵션 비교**:

| 방식 | 안정성 | 복잡도 | 0.5초 달성 |
|------|--------|--------|------------|
| **직접 발행 + Rollback** | 중간 | 낮음 | ✅ 가능 |
| **Transactional Outbox + Scheduler** | 높음 | 중간 | ✅ 가능 |
| **Debezium CDC** | 최고 | 높음 | ⚠️ 추가 지연 |

**추천**: 첫 버전은 **직접 발행 + 보상 트랜잭션**으로 시작

```java
// Spring Boot 예시
@Transactional
public void processUpload(MultipartFile file) {
    Project project = projectRepository.save(...);
    List<Chapter> chapters = splitAndSave(file);
    
    try {
        rabbitTemplate.invoke(ops -> {
            chapters.forEach(ch -> ops.convertAndSend(...));
            ops.waitForConfirms(3000);
            return null;
        });
    } catch (Exception e) {
        project.setStatus("UPLOAD_FAILED");  // 보상 트랜잭션
        throw e;
    }
}
```

**추가 제언**:
- S3 업로드 시 **InputStream Pass-through** (메모리 버퍼링 방지)
- MultipartFile 임시 디스크 저장 비활성화

---

### CSF 2: Entity Resolution (개체 식별) - 2차 Pass 핵심

**문제**: 워커1의 "이안" vs 워커10의 "Ian" 동일 인물 판별

**현재 코드 분석 (`aggregator.py`)**:
- ✅ 한글-영문 매핑 (하드코딩된 경우)
- ✅ 동적 aliases 활용
- ❌ Fuzzy Matching (미지원)
- ❌ Vector Similarity (미지원)

**추천 개선**:

```python
from rapidfuzz import fuzz

def is_same_character(name1: str, name2: str, threshold: int = 80) -> bool:
    # 1. 정확 일치
    if name1.lower() == name2.lower():
        return True
    
    # 2. 한글-영문 매핑 테이블
    if KOREAN_ENGLISH_MAPPING.get(name1) == name2:
        return True
    
    # 3. Fuzzy Matching (Levenshtein)
    if fuzz.ratio(name1, name2) >= threshold:
        return True
    
    return False
```

**Race Condition 방지**:
- 2차 Pass 큐는 **단일 워커(prefetch=1, consumers=1)** 필수
- Actor Model 적용 권장

---

### CSF 3: Dual Write → Eventual Consistency

**문제**: PostgreSQL/Neo4j 동시 쓰기 시 Partial Failure

**현재 구조**: Spring Boot가 PG + Neo4j 동시 저장

**추천: Event-Driven 비동기 동기화**

```
PostgreSQL (Master) ──▶ Domain Event ──▶ Neo4j (Eventually)
```

**이점**:
- Neo4j 장애 시에도 사용자는 텍스트 읽기 가능
- 그래프 시각화는 잠시 지연되어도 무방

---

### 🚀 다음 단계 (Action Items)

| 우선순위 | 작업 | 담당 |
|----------|------|------|
| **P0** | RabbitMQ Payload 확정: `{projectId, chapterId}` | Spring |
| **P0** | Fallback 테스트 케이스: 다양한 챕터 포맷 검증 | Spring |
| **P1** | Entity Resolution 임계값 결정 (유사도 80%?) | Python |
| **P1** | 2차 Pass 전용 큐 설계 (단일 워커) | 공동 |
| **P2** | Transactional Outbox 도입 검토 | Spring |
| **P2** | PG→Neo4j 이벤트 동기화 설계 | Spring |

---

---

## 7️⃣ 현재 vs 제안 아키텍처 비교

| 항목 | 현재 (Current) | 제안 (Proposed) |
|------|---------------|-----------------|
| **처리 단위** | 전체 문서 (단일) | 챕터별 (분할) |
| **병렬성** | 에이전트 내 병렬 | 챕터 간 + 에이전트 내 병렬 |
| **메시지 크기** | 전체 텍스트 포함 | ID만 (Claim Check) |
| **실시간 피드백** | 없음 | SSE + Redis |
| **임베딩 저장** | Neo4j | PostgreSQL(pgvector) + Neo4j |
| **처리 시간** | 6000자당 1분 20~40초 | 365챕터 약 25분 (예상) |
| **확장성** | 제한적 | 워커 수평 확장 가능 |

---

---

## 8️⃣ 20년차 시니어 피드백 - Production Level 디테일

### 📅 날짜
2026-01-01

---

### ⚠️ Pitfall 1: DB Connection Pool 고갈

**문제**: `@Transactional` 내에서 RabbitMQ 대기 시 DB Connection 점유

```java
// ❌ 위험한 코드
@Transactional
public void processUpload(MultipartFile file) {
    projectRepository.save(project);  // DB Connection 획득
    
    // [위험] RabbitMQ가 3초간 응답 없으면 DB Connection이 3초간 물림
    // 트래픽 폭주 시 Connection Pool 고갈 → 서버 다운
    rabbitTemplate.invoke(...).waitForConfirms(3000);
}
```

**해결: TransactionalEventListener (After Commit)**

```java
// ✅ 안전한 코드
@Transactional
public void processUpload(...) {
    // 1. DB 저장 (State: PENDING) - 빠르게 완료
    Project project = projectRepository.save(project);
    
    // 2. 메모리 이벤트 발행 (트랜잭션 내)
    applicationEventPublisher.publishEvent(new ProjectCreatedEvent(project));
}
// ← 여기서 DB Connection 반환됨

// 트랜잭션 완전 종료 후 실행됨 (DB Connection 이미 반환된 상태)
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
public void onProjectCreated(ProjectCreatedEvent event) {
    try {
        // 3. RabbitMQ 발행 (여기서 지연되어도 DB Connection은 안전)
        rabbitTemplate.invoke(...); 
    } catch (Exception e) {
        // 4. 실패 시 별도 트랜잭션으로 보상
        projectService.markAsFailed(event.getProjectId()); 
    }
}
```

**핵심**: DB Lock 점유 시간 최소화

---

### ⚠️ Pitfall 2: Fuzzy Matching Threshold (False Positives)

**문제**: 80점 threshold는 짧은 이름에서 위험

```
"김철" vs "김솔" → 편집 거리상 유사하게 나옴 (오탐!)
"이안" vs "이언" → 한글 자모(Jamo) 특성 미반영
```

**해결: 3단계 자동화 전략**

| 점수 | 처리 방식 |
|------|----------|
| **95점 이상** | 자동 병합 (확신) |
| **80~94점** | 후보 목록에 저장 + 관리자/사용자 검증 |
| **80점 미만** | 별개 캐릭터로 처리 |

```python
def classify_match(name1: str, name2: str) -> str:
    score = fuzz.ratio(name1, name2)
    
    if score >= 95:
        return "AUTO_MERGE"
    elif score >= 80:
        return "NEEDS_REVIEW"  # UI에서 "동일 인물인가요?" 확인
    else:
        return "DIFFERENT"
```

**추가 로그 테이블 (향후 UI 검증용)**:
```sql
CREATE TABLE character_merge_candidates (
    id SERIAL PRIMARY KEY,
    project_id BIGINT,
    name1 VARCHAR(100),
    name2 VARCHAR(100),
    similarity_score INT,
    status VARCHAR(20) DEFAULT 'PENDING',  -- PENDING, MERGED, REJECTED
    reviewed_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### ✅ Pitfall 3: 멱등성 (Idempotency) - GlobalMergerWorker

**문제**: 워커 재시작 시 메시지 재처리 → 중복 병합

**해결: 처리 완료 체크**

```python
class GlobalMergerWorker:
    async def merge_project(self, project_id: str):
        # 1. 이미 처리된 병합인지 확인
        project = await db.query("SELECT status FROM project WHERE id = %s", project_id)
        
        if project.status == "MERGE_COMPLETED":
            print(f"[IDEMPOTENCY] Project {project_id} already merged, skipping")
            return  # ACK 후 스킵
        
        if project.status == "MERGE_IN_PROGRESS":
            # 이전 처리가 실패했을 수 있음 - 재처리 허용
            print(f"[RECOVERY] Resuming merge for {project_id}")
        
        # 2. 상태를 IN_PROGRESS로 변경
        await db.execute(
            "UPDATE project SET status = 'MERGE_IN_PROGRESS' WHERE id = %s", 
            project_id
        )
        
        # 3. 병합 로직 실행...
        
        # 4. 완료 표시
        await db.execute(
            "UPDATE project SET status = 'MERGE_COMPLETED' WHERE id = %s", 
            project_id
        )
```

**RabbitMQ 설정 (필수)**:
```yaml
queues:
  chapter_analysis:
    prefetch: 10
    consumers: 10
  
  global_merge:      # 2차 Pass
    prefetch: 1      # 단일 처리
    consumers: 1     # 단일 워커만!
```

---

### ✅ Pitfall 4: Neo4j Decoupling - 별도 큐 분리

**문제**: Neo4j 장애 시 전체 시스템 중단

**해결: 별도 graph_sync_queue**

```
┌─────────────────────────────────────────────────────────────────┐
│                   Neo4j Decoupling Architecture                  │
│                                                                 │
│   Python Worker                                                 │
│        │                                                        │
│        ▼                                                        │
│   Callback to Spring                                            │
│        │                                                        │
│        ▼                                                        │
│   ┌──────────────────┐                                         │
│   │   PostgreSQL     │  ← SSOT (Single Source of Truth)        │
│   │   (즉시 저장)     │                                         │
│   └────────┬─────────┘                                         │
│            │                                                    │
│            ▼                                                    │
│   ┌──────────────────┐     ┌──────────────────┐                │
│   │ graph_sync_queue │────▶│     Neo4j        │                │
│   │   (RabbitMQ)     │     │  (Eventually)    │                │
│   └──────────────────┘     └──────────────────┘                │
│                                                                 │
│   ※ Neo4j 다운 시: 큐에 메시지 쌓임, 복구 후 자동 처리           │
│   ※ 사용자: PG 기반 텍스트 서비스는 정상 이용 가능                │
└─────────────────────────────────────────────────────────────────┘
```

**Spring Boot 구현**:
```java
@Service
public class AnalysisResultHandler {
    
    @Transactional
    public void handleCallback(AnalysisResult result) {
        // 1. PostgreSQL 즉시 저장 (Master)
        characterRepository.saveAll(result.getCharacters());
        eventRepository.saveAll(result.getEvents());
        
        // 2. Neo4j 동기화 이벤트 발행 (비동기)
        rabbitTemplate.convertAndSend(
            "graph_sync_queue", 
            new GraphSyncMessage(result.getProjectId(), result.getCharacters())
        );
    }
}

// 별도 Consumer (Neo4j 장애와 무관하게 PG 서비스 유지)
@RabbitListener(queues = "graph_sync_queue")
public void syncToNeo4j(GraphSyncMessage msg) {
    neo4jService.upsertCharacters(msg.getCharacters());
    neo4jService.upsertRelationships(msg.getRelationships());
}
```

---

### 🎯 Production Readiness Checklist

| 항목 | 상태 | 비고 |
|------|------|------|
| TransactionalEventListener 패턴 | 🔲 TODO | DB Connection 고갈 방지 |
| Fuzzy Matching 3단계 분류 | 🔲 TODO | 오탐 방지 |
| GlobalMergerWorker 멱등성 | 🔲 TODO | 중복 처리 방지 |
| graph_sync_queue 분리 | 🔲 TODO | Neo4j Decoupling |
| RabbitMQ prefetch=1 설정 | 🔲 TODO | 2차 Pass 단일 처리 |

---

---

## 📌 문서 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-01 | 현재 시스템 구조 문서화 |
| 1.1 | 2026-01-01 | 제안 아키텍처 추가 |
| 1.2 | 2026-01-01 | 시니어 피드백 (CSF 1~3) 반영 |
| 1.3 | 2026-01-01 | 20년차 시니어 피드백 (Production Level 디테일) 반영 |

---
