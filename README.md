# StoLink AI Backend

LangGraph 기반 멀티 에이전트 스토리 분석 시스템입니다.

## 주요 기능

- **10개 에이전트 파이프라인**: Character, Event, Setting, Dialogue, Emotion, Relationship, Consistency, Plot, Supervisor, Validator
- **AWS Bedrock 통합**: Nova Micro/Lite, Claude 3.5 Haiku
- **RabbitMQ 메시지 큐**: Spring Boot 백엔드와 비동기 통신
- **개연성 검증**: 설정 충돌 감지 및 경고

## 빠른 시작

### 1. 의존성 설치

```bash
pip install uv
uv pip install -e .
```

### 2. 환경변수 설정

`.env` 파일에 AWS 자격 증명 설정:
```
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

### 3. Docker로 실행

```bash
docker-compose up -d
```

서비스 접속:
- AI Backend: http://localhost:8000
- RabbitMQ UI: http://localhost:15672 (guest/guest)
- Neo4j Browser: http://localhost:7474 (neo4j/stolink123)

## API 엔드포인트

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /health` | 헬스체크 |
| `POST /api/analysis/trigger` | 수동 분석 트리거 (테스트용) |

## 프로젝트 구조

```
app/
├── agents/           # LangGraph 에이전트
│   ├── extraction/   # Level 1: Character, Event, Setting, Dialogue, Emotion
│   ├── analysis/     # Level 2: Relationship, Consistency, Plot
│   └── validation/   # Level 3: Validator
├── api/              # FastAPI 엔드포인트
├── schemas/          # Pydantic 스키마
└── services/         # RabbitMQ, HTTP Callback
```

## Spring 백엔드 연동

Spring Boot에서 RabbitMQ `stolink.analysis.queue`로 메시지 발행:
```json
{
  "job_id": "uuid",
  "project_id": "uuid",
  "document_id": "uuid",
  "content": "분석할 스토리 텍스트",
  "callback_url": "http://spring:8080/api/internal/ai/analysis/callback"
}
```

분석 완료 시 `callback_url`로 결과 전송됩니다.
