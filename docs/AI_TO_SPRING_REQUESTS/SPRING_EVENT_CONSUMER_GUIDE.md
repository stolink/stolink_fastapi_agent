# Spring Boot Event Consumer 구현 가이드

> **AI Backend → Spring Backend 연동을 위한 Event Sourcing 아키텍처 가이드**  
> **작성일**: 2026-01-07 | **업데이트**: 2026-01-07 (명확화 사항 추가)

---

## 목차
1. [아키텍처 변경 요약](#1-아키텍처-변경-요약)
2. [RabbitMQ 설정](#2-rabbitmq-설정)
3. [이벤트 스키마](#3-이벤트-스키마)
4. [Spring Boot Consumer 구현](#4-spring-boot-consumer-구현-예시)
5. [마이그레이션 전략](#5-마이그레이션-전략)
6. [FAQ (명확화 사항)](#6-faq-명확화-사항)

---

## 1. 아키텍처 변경 요약

### 기존 (Dual Write)
```
FastAPI → PostgreSQL 저장 + Neo4j + HTTP Callback → Spring → RDB 저장 (중복!)
```

### 변경 후 (Event Sourcing)
```
FastAPI → Neo4j만 저장 + RabbitMQ Event 발행 → Spring Consumer → RDB 저장 (Single Source of Truth)
```

### 저장 책임 분리

| 데이터 | 저장 위치 | 책임자 | 용도 |
|--------|-----------|--------|------|
| **sections (embedding 포함)** | FastAPI PostgreSQL (pgvector) | AI Backend | 벡터 검색 (RAG) |
| **sections (embedding 제외)** | Spring RDB | Spring | UI 렌더링 |
| **characters, events, settings** | Spring RDB | Spring | **Single Source of Truth** |
| **relationships** | Spring RDB + Neo4j | 양쪽 | Spring: FK 기반 저장, Neo4j: 그래프 쿼리 |

---

## 2. RabbitMQ 설정

### Exchange 및 Queue

| 구성요소 | 이름 | 설명 |
|----------|------|------|
| **Exchange** | `stolink.analysis.events` | Direct Exchange |
| **Queue** | `analysis.completed` | 분석 완료/실패 이벤트 |
| **DLQ** | `analysis.dlq` | 처리 실패 시 재시도용 |

### Virtual Host 설정

> [!IMPORTANT]
> **`stolink` virtual host는 Docker Compose에서 자동 생성됩니다.**
> 
> `docker-compose.yml`의 RabbitMQ 서비스에 환경변수로 설정되어 있습니다:
> ```yaml
> rabbitmq:
>   environment:
>     RABBITMQ_DEFAULT_VHOST: stolink
> ```
> 
> 수동 생성이 필요한 경우:
> ```bash
> rabbitmqctl add_vhost stolink
> rabbitmqctl set_permissions -p stolink guest ".*" ".*" ".*"
> ```

---

## 3. 이벤트 스키마

### 3.1 AnalysisCompletedEvent (분석 성공)

```json
{
  "event_type": "ANALYSIS_COMPLETED",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-01-07T12:00:00Z",
  
  "project_id": "project-uuid",
  "document_id": "document-uuid",
  "job_id": "analysis-job-uuid",
  "parent_folder_id": "folder-uuid",
  "trace_id": "trace-uuid",
  
  "sections": [
    {
      "sequence_order": 1,
      "nav_title": "Section 1",
      "content": "...",
      "embedding": [0.1, 0.2, ...],
      "related_characters": ["서진", "지원"],
      "related_events": ["story-evt-001"]
    }
  ],
  "characters": [
    {"name": "서진", "role": "PROTAGONIST", ...}
  ],
  "events": [
    {"story_event_id": "story-evt-001", "event_type": "BATTLE", ...}
  ],
  "settings": [
    {"name": "어둠의 숲", "location_type": "FOREST", ...}
  ],
  "relationships": [
    {"source": "서진", "target": "지원", "type": "ALLY", "strength": 8}
  ],
  
  "plot_integration": {...},
  "consistency_report": {...},
  "validation": {...},
  
  "processing_time_ms": 5000
}
```

### 3.2 AnalysisFailedEvent (분석 실패)

```json
{
  "event_type": "ANALYSIS_FAILED",
  "event_id": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2026-01-07T12:00:00Z",
  
  "project_id": "project-uuid",
  "document_id": "document-uuid",
  "job_id": "job-uuid",
  "trace_id": "trace-uuid",
  
  "error_code": "PROCESSING_ERROR",
  "error_message": "Failed to extract characters",
  "error_details": {...},
  
  "processing_time_ms": 1000
}
```

---

## 4. Spring Boot Consumer 구현 예시

### 4.1 의존성 추가

```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-amqp</artifactId>
</dependency>
```

### 4.2 RabbitMQ 설정

```yaml
# application.yml
spring:
  rabbitmq:
    host: ${RABBITMQ_HOST:localhost}
    port: ${RABBITMQ_PORT:5672}
    username: ${RABBITMQ_USER:guest}
    password: ${RABBITMQ_PASSWORD:guest}
    virtual-host: stolink
```

### 4.3 Event DTO

```java
@Data
public class AnalysisCompletedEvent {
    // === 이벤트 메타데이터 ===
    private String eventType;           // "ANALYSIS_COMPLETED" or "ANALYSIS_FAILED"
    private String eventId;             // 표준 UUID (Idempotency key)
    private Instant timestamp;
    
    // === 분석 대상 식별자 ===
    private String projectId;
    private String documentId;
    private String jobId;               // Document와 연결된 상위 폴더
    private String parentFolderId;      // (아래 FAQ 참조)
    private String traceId;             // 분산 추적용 (MDC 로깅)
    
    // === 분석 결과 ===
    private List<SectionDto> sections;
    private List<CharacterDto> characters;
    private List<StoryEventDto> events;  // events[].story_event_id 로 구분
    private List<SettingDto> settings;
    private List<RelationshipDto> relationships;
    
    // === Level 2 분석 (JSON 컬럼 저장 권장) ===
    private Map<String, Object> plotIntegration;
    private Map<String, Object> consistencyReport;
    private Map<String, Object> validation;
    
    private Integer processingTimeMs;
    
    // === 에러 정보 (ANALYSIS_FAILED인 경우만) ===
    private String errorCode;
    private String errorMessage;
    private Map<String, Object> errorDetails;
}
```

### 4.4 Event Consumer

```java
@Component
@Slf4j
public class AnalysisEventConsumer {
    
    private final ProcessedEventRepository processedEventRepository;
    private final AICallbackService aiCallbackService;  // 기존 로직 재사용
    
    @RabbitListener(queues = "analysis.completed")
    public void handleAnalysisEvent(AnalysisCompletedEvent event) {
        // trace_id를 MDC에 설정 (로깅)
        MDC.put("traceId", event.getTraceId());
        
        try {
            log.info("Received analysis event: {}, type: {}", 
                     event.getEventId(), event.getEventType());
            
            // 1. Idempotency 체크
            if (processedEventRepository.existsByEventId(event.getEventId())) {
                log.info("Event already processed, skipping: {}", event.getEventId());
                return;
            }
            
            // 2. 기존 AICallbackService 로직 재사용
            if ("ANALYSIS_COMPLETED".equals(event.getEventType())) {
                aiCallbackService.processAnalysisResult(event);
            } else if ("ANALYSIS_FAILED".equals(event.getEventType())) {
                aiCallbackService.processAnalysisFailure(event);
            }
            
            // 3. 처리 완료 기록
            processedEventRepository.save(new ProcessedEvent(event.getEventId()));
            
        } catch (Exception e) {
            log.error("Failed to process event: {}", event.getEventId(), e);
            throw new AmqpRejectAndDontRequeueException("Processing failed", e);
        } finally {
            MDC.remove("traceId");
        }
    }
}
```

### 4.5 Sections 저장 (embedding 제외)

```java
// SectionDto - embedding 필드는 저장하지 않음
@Data
public class SectionDto {
    private Integer sequenceOrder;
    private String navTitle;
    private String content;
    // private List<Float> embedding;  // 저장 안 함! FastAPI에서 관리
    private List<String> relatedCharacters;
    private List<String> relatedEvents;
}

// Repository
public void saveSections(UUID documentId, List<SectionDto> sections) {
    for (SectionDto dto : sections) {
        // embedding 제외하고 저장
        sectionRepository.save(Section.builder()
            .documentId(documentId)
            .sequenceOrder(dto.getSequenceOrder())
            .navTitle(dto.getNavTitle())
            .content(dto.getContent())
            .relatedCharacters(dto.getRelatedCharacters())  // VARCHAR[] 또는 JSON
            .relatedEvents(dto.getRelatedEvents())
            .build());
    }
}
```

### 4.6 Relationships 저장 (이름→FK 변환)

```java
public void saveRelationships(UUID projectId, List<RelationshipDto> relationships) {
    for (RelationshipDto dto : relationships) {
        // 이름으로 Character 조회하여 FK 획득
        Character source = characterRepository
            .findByProjectIdAndName(projectId, dto.getSource())
            .orElseThrow(() -> new NotFoundException("Source not found: " + dto.getSource()));
        
        Character target = characterRepository
            .findByProjectIdAndName(projectId, dto.getTarget())
            .orElseThrow(() -> new NotFoundException("Target not found: " + dto.getTarget()));
        
        // FK 기반으로 저장
        relationshipRepository.upsert(Relationship.builder()
            .projectId(projectId)
            .sourceCharacterId(source.getId())
            .targetCharacterId(target.getId())
            .type(dto.getType())
            .strength(dto.getStrength())
            .description(dto.getDescription())
            .build());
    }
}
```

### 4.7 Level 2 분석 결과 저장

```java
// AnalysisJob 테이블에 JSON 컬럼으로 저장
@Entity
@Table(name = "analysis_jobs")
public class AnalysisJob {
    @Id
    private UUID id;
    
    // ... 기존 필드 ...
    
    @Column(columnDefinition = "jsonb")
    @Type(JsonBinaryType.class)
    private Map<String, Object> plotIntegration;
    
    @Column(columnDefinition = "jsonb")
    @Type(JsonBinaryType.class)
    private Map<String, Object> consistencyReport;
    
    @Column(columnDefinition = "jsonb")
    @Type(JsonBinaryType.class)
    private Map<String, Object> validation;
}
```

### 4.8 ProcessedEvent 엔티티 (Idempotency)

```java
@Entity
@Table(name = "processed_events")
public class ProcessedEvent {
    @Id
    private String eventId;  // 표준 UUID 문자열
    
    @Column(nullable = false)
    private Instant processedAt = Instant.now();
    
    public ProcessedEvent(String eventId) {
        this.eventId = eventId;
    }
}
```

---

## 5. 마이그레이션 전략

### Phase 1: 병행 운영 (현재)
- FastAPI: Event 발행 + 기존 HTTP Callback 유지
- Spring: 기존 Callback 처리 + 새 Event Consumer 구현

### Phase 2: 검증
- 두 경로로 데이터 수신되는지 확인
- 데이터 정합성 검증

### Phase 3: 완전 전환
- FastAPI: `enable_legacy_callback: false`로 변경
- Spring: Callback 엔드포인트 제거

---

## 6. FAQ (명확화 사항)

### Q1. sections 데이터 저장 범위

| 필드 | Spring 저장 | 비고 |
|------|-------------|------|
| `sequence_order` | ✅ 저장 | |
| `nav_title` | ✅ 저장 | |
| `content` | ✅ 저장 | |
| `embedding` | ❌ **저장 안 함** | FastAPI pgvector에서 관리 |
| `related_characters` | ✅ 저장 | VARCHAR[] 또는 JSON |
| `related_events` | ✅ 저장 | VARCHAR[] 또는 JSON |

---

### Q2. event_id 형식

```
표준 UUID v4 형식입니다.
예: "550e8400-e29b-41d4-a716-446655440000"

Python 코드:
event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
```

별도 prefix 없이 **순수 UUID 문자열**입니다.

---

### Q3. relationships 저장 방식

**네, 이름으로 조회 후 FK 연결합니다.**

```java
// 1. source/target 이름으로 Character 조회
Character source = characterRepository.findByProjectIdAndName(projectId, dto.getSource());
Character target = characterRepository.findByProjectIdAndName(projectId, dto.getTarget());

// 2. FK로 저장
Relationship rel = Relationship.builder()
    .sourceCharacterId(source.getId())
    .targetCharacterId(target.getId())
    .build();
```

> [!NOTE]
> Characters가 먼저 저장되어야 Relationships 저장이 가능합니다.
> 저장 순서: Characters → Settings → Events → Relationships

---

### Q4. Level 2 분석 결과 저장

| 필드 | 권장 방식 |
|------|-----------|
| `plotIntegration` | `analysis_jobs.plot_integration` (JSONB 컬럼) |
| `consistencyReport` | `analysis_jobs.consistency_report` (JSONB 컬럼) |
| `validation` | `analysis_jobs.validation` (JSONB 컬럼) |

별도 테이블보다 **JSON 컬럼**이 간단합니다. 스키마가 자주 변경될 수 있어서 유연성이 필요합니다.

---

### Q5. DLQ 처리 정책

**현재: FastAPI에서 자동 저장, Spring에서 수동 재처리 권장**

```
이벤트 발행 실패 → FastAPI가 analysis.dlq에 저장
                    ↓
            Spring 관리자가 RabbitMQ 콘솔에서 확인
                    ↓
            수동으로 메인 큐에 재발행
```

자동 재시도 구현 시:
```java
@RabbitListener(queues = "analysis.dlq")
public void handleDLQ(DLQMessage dlq) {
    if (dlq.getRetryCount() < 3) {
        dlq.setRetryCount(dlq.getRetryCount() + 1);
        rabbitTemplate.convertAndSend("analysis.completed", dlq.getOriginalEvent());
    } else {
        log.error("Max retries exceeded: {}", dlq.getOriginalEventId());
        // 알림 발송 또는 별도 테이블 저장
    }
}
```

---

### Q6. parent_folder_id 용도

**Document의 상위 폴더(FOLDER) ID입니다.**

```
Project
└── Folder1 (parent_folder_id)
    └── Document (document_id)
```

- 용도: 챕터/폴더 단위로 분석 결과를 그룹화할 때 사용
- 현재 필수 아님: `null`일 수 있음 (Document가 최상위에 있는 경우)

---

### Q7. trace_id 활용

**MDC(Mapped Diagnostic Context) 로깅에 사용합니다.**

```java
@RabbitListener(queues = "analysis.completed")
public void handleEvent(AnalysisCompletedEvent event) {
    MDC.put("traceId", event.getTraceId());
    try {
        log.info("Processing event...");  // 로그에 traceId 자동 포함
    } finally {
        MDC.remove("traceId");
    }
}
```

logback.xml:
```xml
<pattern>%d{HH:mm:ss} [%X{traceId}] %-5level %logger - %msg%n</pattern>
```

---

### Q8. events[].event_id vs 메시지 event_id 구분

| 필드 | 용도 | 형식 |
|------|------|------|
| 메시지 `event_id` | Idempotency key (RabbitMQ 중복 방지) | UUID |
| `events[].story_event_id` | 스토리 내 이벤트 식별자 | String (예: "BATTLE-001") |

> [!IMPORTANT]
> **혼란 방지를 위해 `events[].event_id`를 `story_event_id`로 네이밍 변경을 권장합니다.**
> AI Backend에서 수정 예정입니다.

---

### Q9. 기존 AICallbackService와의 관계

**기존 로직 재사용을 권장합니다.**

```java
// EventConsumer에서 AICallbackService 호출
@Component
public class AnalysisEventConsumer {
    private final AICallbackService aiCallbackService;
    
    public void handleEvent(AnalysisCompletedEvent event) {
        // 기존 저장 로직 재사용
        aiCallbackService.processAnalysisResult(event);
    }
}
```

기존 `AICallbackService`의 저장 로직을 추출하거나, Event 기반으로 호출하면 됩니다.

---

### Q10. stolink virtual host 생성

**Docker Compose에서 자동 생성됩니다.**

```yaml
# docker-compose.yml
rabbitmq:
  image: rabbitmq:3-management
  environment:
    RABBITMQ_DEFAULT_VHOST: stolink
```

수동 생성이 필요한 경우:
```bash
docker exec stolink-rabbitmq rabbitmqctl add_vhost stolink
docker exec stolink-rabbitmq rabbitmqctl set_permissions -p stolink guest ".*" ".*" ".*"
```

---

## 7. 확인 방법

### RabbitMQ 관리 콘솔
```
http://localhost:15672
Username: guest
Password: guest
```

- `stolink.analysis.events` Exchange 확인
- `analysis.completed` Queue에 메시지 도착 확인

---

## 8. 연락처

질문 사항은 AI Backend 팀에 문의해주세요.
