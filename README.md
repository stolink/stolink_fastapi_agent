# StoLink AI Backend

![Python Version](https://img.shields.io/badge/python-%3E%3D3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)

---

## 1. Project Overview

> **Core Value:** 장편 소설의 캐릭터, 이벤트, 관계를 AI가 자동 추출하고 개연성을 검증하여 작가의 세계관 관리를 지원하는 분석 엔진

StoLink AI Backend는 LangGraph 기반 **멀티 에이전트 파이프라인**으로 소설 텍스트를 분석합니다. Spring Boot로부터 RabbitMQ 메시지를 수신하여 비동기로 처리하고, 결과를 콜백으로 전송합니다.

### 주요 링크

| 환경                | URL / 경로                                                  |
| ------------------- | ----------------------------------------------------------- |
| **Local**           | `http://localhost:8000`                                     |
| **RabbitMQ UI**     | `http://localhost:15672` (guest/guest)                      |
| **Neo4j Browser**   | `http://localhost:7474` (neo4j/stolink123)                  |
| **Architecture**    | [SYSTEM_FLOW.md](./SYSTEM_FLOW.md)                          |
| **Troubleshooting** | [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)                  |

---

## 2. Tech Stack & Decision Log

기술 선정 이유를 명시하여, 향후 레거시 파악 시 문맥을 제공합니다.

### 2.1 Core Framework

| Category       | Technology | Version | Decision Rationale                                      |
| -------------- | ---------- | ------- | ------------------------------------------------------- |
| **Runtime**    | Python     | 3.11+   | LangChain/LangGraph 생태계, 빠른 프로토타이핑           |
| **Web**        | FastAPI    | 0.115   | 비동기 지원, Pydantic 통합, 자동 API 문서               |
| **Agent**      | LangGraph  | 0.2     | 상태 기반 워크플로우, 조건부 라우팅, 재시도 지원        |
| **Packaging**  | uv         | -       | pip 대비 10배 빠른 설치, 의존성 잠금                    |

### 2.2 LLM Provider

| Category           | Technology      | Model             | Decision Rationale                     |
| ------------------ | --------------- | ----------------- | -------------------------------------- |
| **Primary**        | Google Gemini   | gemini-2.0-flash  | 한국어 성능, 무료 티어, 빠른 응답      |
| **Fallback**       | AWS Bedrock     | Claude 3.5 Haiku  | 엔터프라이즈 안정성, 멀티 리전         |
| **Embedding**      | Gemini          | text-embedding    | 768/1024차원, 시맨틱 청킹 및 RAG       |

### 2.3 Database

| Category      | Technology | Version | Decision Rationale                                 |
| ------------- | ---------- | ------- | -------------------------------------------------- |
| **Graph DB**  | Neo4j      | 5.x     | 캐릭터 관계 그래프, Cypher 쿼리, Vector Index      |
| **Vector DB** | pgvector   | -       | PostgreSQL 확장, 섹션 임베딩 저장                  |
| **Cache**     | Redis      | 7.x     | 임베딩 캐시, 프로젝트 락 (Sorted Set)              |

### 2.4 Message Queue

| Category       | Technology | Version | Decision Rationale                          |
| -------------- | ---------- | ------- | ------------------------------------------- |
| **Broker**     | RabbitMQ   | 3.13    | Spring AMQP 호환, 우선순위 큐, ACK/NACK     |
| **Client**     | aio_pika   | -       | asyncio 네이티브, Connection Pooling        |

### 2.5 Utilities

| Category           | Technology | Version | Decision Rationale                               |
| ------------------ | ---------- | ------- | ------------------------------------------------ |
| **Fuzzy Matching** | rapidfuzz  | -       | 캐릭터 이름 병합, Levenshtein 기반               |
| **Structured Out** | Pydantic   | 2.x     | LLM 출력 스키마 강제, 자동 검증                  |
| **Logging**        | structlog  | -       | 구조화 로깅, JSON 출력                           |

---

## 3. Getting Started (Development)

### 3.1 Prerequisites

본 프로젝트는 **Python 3.11+**을 요구합니다.

```bash
# Python 버전 확인
python --version  # Python 3.11.x

# uv 설치
pip install uv
```

### 3.2 Installation

```bash
# 저장소 클론
git clone https://github.com/your-org/sto-link-AI-backend.git
cd sto-link-AI-backend

# 의존성 설치
uv pip install -e .
```

### 3.3 Environment Variables

`.env.example`를 복사하여 `.env`를 생성하고 필요한 값을 채우십시오.

```bash
cp .env.example .env
```

| Variable              | Description                    | Required | Default                 |
| --------------------- | ------------------------------ | -------- | ----------------------- |
| `LLM_PROVIDER`        | LLM 제공자 (`gemini`/`bedrock`)| Yes      | `gemini`                |
| `GOOGLE_API_KEY`      | Gemini API 키                  | Yes*     | -                       |
| `AWS_ACCESS_KEY_ID`   | Bedrock용 AWS 키               | No       | -                       |
| `RABBITMQ_HOST`       | RabbitMQ 호스트                | Yes      | `localhost`             |
| `POSTGRES_HOST`       | PostgreSQL 호스트              | Yes      | `localhost`             |
| `NEO4J_URI`           | Neo4j Bolt URI                 | Yes      | `bolt://localhost:7687` |
| `REDIS_HOST`          | Redis 호스트                   | Yes      | `localhost`             |
| `SPRING_BASE_URL`     | Spring Backend URL             | Yes      | `http://localhost:8080` |

> ⚠️ `.env` 파일은 Git에 커밋되지 않습니다.

### 3.4 Running the App

```bash
# 인프라 실행 (RabbitMQ, PostgreSQL, Neo4j, Redis)
docker-compose -f docker-compose.local.yml up -d

# 개발 서버 실행 (localhost:8000)
uvicorn app.main:app --reload

# 또는 전체 스택 실행 (AI Backend 포함)
docker-compose -f docker-compose.standalone.yml up -d
```

### 3.5 Service Endpoints

| Service         | Port  | Description              |
| --------------- | ----- | ------------------------ |
| AI Backend      | 8000  | FastAPI + RabbitMQ 소비자 |
| RabbitMQ        | 5672  | AMQP 브로커              |
| RabbitMQ UI     | 15672 | 관리 콘솔                |
| PostgreSQL      | 5432  | 메인 DB + pgvector       |
| Neo4j           | 7687  | 그래프 DB (Bolt)         |
| Redis           | 6379  | 캐시 + 분산 락           |

---

## 4. Architecture

### 4.1 Pipeline Strategy

본 프로젝트는 **LangGraph 상태 기반 멀티 에이전트 파이프라인**을 채택합니다.

**선택 이유:**

- 각 에이전트가 독립적으로 전문화된 작업 수행
- 조건부 라우팅으로 재추출 루프 지원
- 상태 전파로 컨텍스트 유지

### 4.2 Directory Structure

```
app/
├── agents/                   # LangGraph 에이전트 (15개)
│   ├── extraction/           # 추출 에이전트
│   │   ├── character_team.py # 캐릭터 서브그래프 (4개 에이전트)
│   │   ├── event.py          # 이벤트 추출
│   │   └── setting.py        # 장소/배경 추출
│   ├── analysis/             # 분석 에이전트
│   │   ├── relationship.py   # 관계 분석
│   │   └── consistency.py    # 개연성 검사 (15가지 충돌 유형)
│   ├── validation/           # 검증 에이전트
│   │   └── validator.py      # 최종 검증
│   ├── graph.py              # 파이프라인 오케스트레이션
│   └── supervisor.py         # Supervisor 라우터
│
├── services/                 # 비즈니스 로직 (17개)
│   ├── document_analysis_consumer.py  # RabbitMQ Consumer (핵심)
│   ├── db_query_service.py            # PostgreSQL + Neo4j 쿼리
│   ├── hierarchical_context.py        # 계층적 맥락 관리
│   ├── summary_service.py             # 요약 생성 (소설/권/챕터)
│   ├── project_lock.py                # Redis Sorted Set 락
│   ├── chunking_service.py            # 시맨틱 청킹
│   └── embedding_service.py           # 임베딩 생성 + 캐싱
│
├── schemas/                  # Pydantic 스키마 (11개)
│   ├── messages.py           # RabbitMQ 메시지
│   ├── characters.py         # 캐릭터 (FullCharacter)
│   ├── events.py             # 이벤트
│   └── consistency.py        # 개연성 검사 결과
│
├── utils/                    # 유틸리티
│   └── entity_resolution.py  # Fuzzy Matching (rapidfuzz)
│
├── api/                      # FastAPI 엔드포인트
│   └── routes.py
│
├── config.py                 # 설정 (Pydantic Settings)
└── main.py                   # 애플리케이션 진입점
```

### 4.3 Pipeline Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                      LangGraph Pipeline                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   [RabbitMQ Message]                                             │
│        │                                                         │
│        ▼                                                         │
│   [Semantic Chunking] ──── 시맨틱 청킹 (4000자 단위)             │
│        │                                                         │
│        ▼                                                         │
│   [Extraction Phase] ─────────────────────────────────────────   │
│        ├── Character Team (Identity, Appearance, Personality)   │
│        ├── Setting Agent                                         │
│        └── Event Agent                                           │
│        │                                                         │
│        ▼                                                         │
│   [Global Resolution] ──── 중복 캐릭터 병합 (Fuzzy Matching)     │
│        │                                                         │
│        ▼                                                         │
│   [Analysis Phase] ───────────────────────────────────────────   │
│        ├── Relationship Agent                                    │
│        └── Consistency Agent (15가지 충돌 검사)                  │
│        │                                                         │
│        ▼                                                         │
│   [Validation] ──────── 재추출 필요 시 루프                      │
│        │                                                         │
│        ▼                                                         │
│   [Neo4j/PostgreSQL Save] + [Spring Callback]                    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.4 Project Lock (Sequential Processing)

| 상황                | 동작                                      |
| ------------------- | ----------------------------------------- |
| **같은 프로젝트**   | `document_order` 순서대로 순차 처리       |
| **다른 프로젝트**   | 병렬 처리 가능 (독립된 락 키)             |

**Redis Sorted Set 기반:**
```
ZADD queue:project:A {job1: 2}  # document_order=2
ZADD queue:project:A {job2: 1}  # document_order=1 → rank=0
ZRANK queue:project:A job2      # → 0 (내 차례!)
SET lock:project:A job2 NX EX 600  # 락 획득
```

---

## 5. Spring Backend Integration

### 5.1 Message Format (RabbitMQ)

**Queue:** `document_analysis_queue`

```json
{
  "job_id": "uuid",
  "project_id": "uuid",
  "document_id": "uuid",
  "document_order": 1,
  "content": "분석할 소설 텍스트...",
  "callback_url": "http://spring:8080/api/internal/ai/callback",
  "requires_deep_analysis": true,
  "analysis_type": "full_manuscript"
}
```

### 5.2 Callback Response (HTTP POST)

```json
{
  "document_id": "uuid",
  "status": "COMPLETED",
  "consistency_report": {
    "overall_score": 85,
    "requires_reextraction": false,
    "conflicts": [
      {
        "type": "CHARACTER_TRAIT_CONFLICT",
        "severity": "MEDIUM",
        "description": "리안의 성격이 갑자기 변함"
      }
    ]
  },
  "document_summary": {
    "summary": "리안이 마왕성에 도착하여...",
    "key_characters": ["리안", "마왕"],
    "key_events": ["마왕성 도착", "첫 대면"]
  },
  "processing_time_ms": 12500
}
```

---

## 6. Additional Documentation

| 문서                                                        | 설명                         |
| ----------------------------------------------------------- | ---------------------------- |
| [SYSTEM_FLOW.md](./SYSTEM_FLOW.md)                          | 전체 시스템 흐름 분석 (필독) |
| [MULTI-AGENT_ARCHITECTURE.md](./MULTI-AGENT_ARCHITECTURE.md)| 에이전트 아키텍처 상세       |
| [ACK_TIMEOUT_WALKTHROUGH.md](./ACK_TIMEOUT_WALKTHROUGH.md)  | ACK 타임아웃/재전송 흐름     |

---

## 7. Contributing

### 7.1 Commit Convention

```
feat: 새 기능 추가
fix: 버그 수정
docs: 문서 변경
refactor: 리팩토링
test: 테스트 추가
chore: 빌드, 설정 변경
```

### 7.2 Code Style

- **Black** 포매터 사용
- **isort** import 정렬
- **Type Hints** 필수
