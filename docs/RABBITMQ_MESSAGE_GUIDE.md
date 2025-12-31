# RabbitMQ 메시지 발행 가이드 (Spring Boot → AI Backend)

> **Last Updated**: 2024-12-31
> **대상**: Spring Boot Backend Team
> **목적**: 스토리 분석 요청 메시지 발행 및 결과 수신 가이드

---

## 📋 목차

1. [RabbitMQ 설정](#1-rabbitmq-설정)
2. [입력 메시지 형식](#2-입력-메시지-형식)
3. [출력 결과 형식](#3-출력-결과-형식)
4. [Spring Boot 필수 구현 사항](#4-spring-boot-필수-구현-사항)
5. [테스트 방법](#5-테스트-방법)

---

## 1. RabbitMQ 설정

| 항목 | 값 |
|------|-----|
| **Exchange** | `stolink.exchange` (direct) |
| **Queue** | `stolink.analysis.queue` |
| **Routing Key** | `analysis` |

---

## 2. 입력 메시지 형식

### 전체 스키마

```json
{
  "job_id": "string (required)",
  "project_id": "string (required)", 
  "document_id": "string (required)",
  "content": "string (required)",
  "context": {
    "chapter_number": "integer (optional)",
    "total_chapters": "integer (optional)",
    "existing_characters": [
      {
        "id": "string",
        "name": "string",
        "role": "string"
      }
    ],
    "existing_events": [],
    "existing_relationships": [],
    "existing_settings": [],
    "world_rules_summary": "string (optional)"
  },
  "callback_url": "string (required)",
  "trace_id": "string (optional)"
}
```

### 필드 설명

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `job_id` | string | ✅ | 고유 작업 식별자 (UUID 권장) |
| `project_id` | string | ✅ | 프로젝트 UUID |
| `document_id` | string | ✅ | 분석할 문서 UUID |
| `content` | string | ✅ | **분석할 스토리 텍스트** (최대 권장: 5,000자) |
| `context` | object | ❌ | 기존 데이터 컨텍스트 |
| `context.chapter_number` | integer | ❌ | 현재 챕터 번호 |
| `context.total_chapters` | integer | ❌ | 전체 챕터 수 |
| `context.existing_characters` | array | ❌ | 기존 캐릭터 참조 목록 |
| `context.existing_characters[].id` | string | ✅ | 캐릭터 UUID |
| `context.existing_characters[].name` | string | ✅ | 캐릭터 이름 |
| `context.existing_characters[].role` | string | ❌ | protagonist / antagonist / supporting |
| `context.existing_events` | array | ❌ | 기존 이벤트 참조 |
| `context.existing_relationships` | array | ❌ | 기존 관계 참조 |
| `context.existing_settings` | array | ❌ | 기존 배경 참조 |
| `context.world_rules_summary` | string | ❌ | 세계관 규칙 요약 |
| `callback_url` | string | ✅ | 결과 수신 URL |
| `trace_id` | string | ❌ | 분산 추적용 ID |

### 예시 입력

```json
{
    "job_id": "test-story-cyberpunk-01",
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "document_id": "doc-neon-memories",
    "content": "2087년 네오서울, 하층 거주구. 비가 내렸다. 정확히는 산성비였다. 진하(Jin-ha)는 낡은 트렌치코트 깃을 세우며 뒷골목 입구에서 발걸음을 멈췄다...(생략)",
    "context": {
        "chapter_number": 1,
        "total_chapters": 8,
        "existing_characters": [
            {
                "id": "char-jinha-001",
                "name": "진하",
                "role": "protagonist"
            }
        ],
        "existing_events": [],
        "existing_relationships": [],
        "existing_settings": [],
        "world_rules_summary": "2087년 네오서울. 계층이 분리된 디스토피아 사회에서 불법 기억 거래와 의식 디지털화 기술이 암시장에서 거래되고 있다."
    },
    "callback_url": "http://spring-server:8080/api/internal/ai/analysis/callback",
    "trace_id": "trace-cyberpunk-test-01"
}
```

---

## 3. 출력 결과 형식

AI Backend가 `callback_url`로 **HTTP POST** 요청을 보냅니다.

### 최상위 구조

```json
{
  "jobId": "string",
  "status": "COMPLETED | FAILED | WARNING",
  "result": { ... },
  "error": "string | null"
}
```

### `result` 객체 구조

| 필드 | 타입 | 설명 |
|------|------|------|
| `characters` | `FullCharacter[]` | 추출된 캐릭터 목록 |
| `events` | `Event[]` | 추출된 이벤트 목록 |
| `settings` | `Setting[]` | 추출된 배경/장소 목록 |
| `relationships` | `Relationship[]` | 캐릭터 간 관계 |
| `dialogues` | `DialogueAnalysis` | 대화 분석 결과 |
| `emotions` | `EmotionTracking` | 감정 추적 결과 |
| `plot_integration` | `PlotIntegration` | 플롯 통합 결과 |
| `consistency_report` | `ConsistencyReport` | 일관성 검증 결과 |
| `validation` | `Validation` | 최종 검증 결과 |
| `metadata` | `Metadata` | 처리 메타데이터 |

### 예시 출력 (축약)

```json
{
  "jobId": "test-story-cyberpunk-01",
  "status": "COMPLETED",
  "result": {
    "characters": [
      {
        "_id": "char-jinha-001",
        "name": "진하",
        "role": "protagonist",
        "level": 1,
        "faction": "독립 탐정사무소",
        "profile": {
          "character_id": "char-jinha-001",
          "name": "진하",
          "age": 30,
          "gender": "male",
          "personality": ["대담함", "용기", "직업적 성실"],
          "backstory": "네오서울 하층 거주구 출신 탐정..."
        },
        "appearance": {
          "physique": "athletic",
          "attire": ["낡은 트렌치코트"],
          "cyberware": ["뇌 임플란트", "왼손목 홀로그램 인터페이스"],
          "full_visual_prompt": "athletic, fair skin, 결연한 표정..."
        },
        "personality": {
          "core_traits": ["대담함", "용기"],
          "flaws": ["충동적", "빚에 취약"],
          "values": ["정의", "진실"]
        },
        "stats": { "strength": 10, "dexterity": 10, "intelligence": 10 },
        "inventory": {
          "equipped_items": [
            { "name": "트렌치코트", "item_type": "ARMOR", "slot": "BODY" },
            { "name": "홀로그램 방패", "item_type": "ACCESSORY" }
          ]
        }
      }
    ],
    "events": [
      {
        "event_id": "E001",
        "event_type": "action",
        "narrative_summary": "진하, 네오서울 하층 거주구에서 의뢰 수행",
        "description": "2087년 네오서울의 산성비가 내리는...",
        "participants": ["진하", "ARIA"],
        "visual_scene": "A lone detective in a worn trench coat...",
        "importance": 8
      }
    ],
    "settings": [
      {
        "setting_id": "loc_neo_seoul_lower_01",
        "name": "네오서울 하층 거주구",
        "location_type": "city",
        "visual_background": "Dark cyberpunk alleyways with neon signs...",
        "atmosphere": "gritty, dangerous, lawless",
        "time_of_day": "night",
        "weather": "acid rain"
      }
    ],
    "relationships": [
      {
        "source": "진하",
        "target": "ARIA",
        "relation_type": "FRIENDLY",
        "strength": 7,
        "description": "뇌 임플란트 AI 어시스턴트로서 진하의 신뢰할 수 있는 동료"
      }
    ],
    "validation": {
      "is_valid": true,
      "quality_score": 90,
      "action": "approve",
      "action_description": "Ready for callback to Spring Boot"
    },
    "metadata": {
      "processing_time_ms": 87706,
      "trace_id": "trace-cyberpunk-test-01",
      "agents_executed": ["character", "event", "setting", "dialogue", "emotion", "relationship", "consistency", "plot", "validator"]
    }
  },
  "error": null
}
```

---

## 4. Spring Boot 필수 구현 사항

### 4.1 콜백 수신 API

```
POST {callback_url}
Content-Type: application/json
```

**요청 바디**: 위의 출력 결과 형식 참조

### 4.2 Job 상태 업데이트 API (실시간)

```
POST /api/internal/ai/jobs/{job_id}/status
Content-Type: application/json
```

**요청 바디**:
```json
{
  "status": "ANALYZING | VALIDATING | FAILED",
  "message": "상태 설명 메시지"
}
```

### 4.3 Spring Boot 코드 예시

#### 메시지 발행

```java
@Service
public class AIAnalysisService {
    
    private final RabbitTemplate rabbitTemplate;
    
    public void requestAnalysis(String projectId, String documentId, String content) {
        Map<String, Object> message = new HashMap<>();
        message.put("job_id", UUID.randomUUID().toString());
        message.put("project_id", projectId);
        message.put("document_id", documentId);
        message.put("content", content);
        message.put("context", buildContext(projectId));
        message.put("callback_url", "https://your-server.com/api/ai-callback");
        message.put("trace_id", "trace-" + System.currentTimeMillis());
        
        rabbitTemplate.convertAndSend(
            "stolink.exchange", 
            "analysis", 
            message
        );
    }
}
```

#### 콜백 수신

```java
@RestController
@RequestMapping("/api")
public class AICallbackController {
    
    @PostMapping("/ai-callback")
    public ResponseEntity<String> handleAICallback(@RequestBody AIResult result) {
        if ("COMPLETED".equals(result.getStatus())) {
            processCharacters(result.getResult().getCharacters());
            processEvents(result.getResult().getEvents());
            processSettings(result.getResult().getSettings());
            processRelationships(result.getResult().getRelationships());
        } else if ("FAILED".equals(result.getStatus())) {
            logError(result.getError());
        }
        
        return ResponseEntity.ok("Received");
    }
}
```

---

## 5. 테스트 방법

### 5.1 HTTP API 테스트 (docker 실행 중일 때)

```bash
curl -X POST "http://localhost:8000/api/analysis/trigger" \
  -H "Content-Type: application/json" \
  -d @test_payload.json > result.json
```

### 5.2 RabbitMQ Web UI 테스트

1. `http://localhost:15672` 접속 (guest/guest)
2. `Queues` → `stolink.analysis.queue` 선택
3. `Publish message` 클릭
4. Properties에 `content_type: application/json` 설정
5. Payload에 JSON 메시지 입력 후 발행

---

## 📋 주의사항

| 항목 | 설명 |
|------|------|
| **캐릭터 ID 재사용** | `context.existing_characters`에 제공된 ID는 결과에서 재사용됩니다 |
| **처리 시간** | 평균 30~60초, 최대 5분 (스토리 길이에 따라 다름) |
| **Callback URL** | Docker 내부에서 `localhost`는 접근 불가. 외부 접근 가능한 URL 필요 |
| **content 최대 길이** | 5,000자 권장. 그 이상은 챕터 단위로 분할 권장 |

---

## 📎 관련 문서

- `docs/SPRING_INTEGRATION.md` - 상세 통합 가이드
- `docs/FASTAPI_RESPONSE_SCHEMA.md` - 출력 스키마 상세
- `app/schemas/messages.py` - Pydantic 스키마 정의
