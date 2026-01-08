# Spring 팀 전달 사항: 맥락 유지 시스템 DB 테이블

## 개요

FastAPI AI Backend에서 구현한 맥락 유지 시스템(Context Maintenance System)을 위해 **2개의 새로운 PostgreSQL 테이블**이 필요합니다.

---

## 1. document_summaries (Phase 3: 챕터 요약)

### 용도
- 챕터별 요약 자동 생성 및 저장
- 계층적 요약 (전체/권/챕터)

### JPA Entity 정의

```java
@Entity
@Table(name = "document_summaries")
public class DocumentSummary {
    
    @Id
    @GeneratedValue(generator = "UUID")
    @GenericGenerator(name = "UUID", strategy = "org.hibernate.id.UUIDGenerator")
    private UUID id;
    
    @Column(nullable = false)
    private UUID documentId;
    
    @Column(nullable = false)
    private UUID projectId;
    
    /**
     * 요약 레벨
     * 1 = 전체 소설
     * 2 = 권/파트
     * 3 = 챕터 (기본값)
     */
    @Column(nullable = false)
    private Integer level = 3;
    
    @Column(nullable = false, columnDefinition = "TEXT")
    private String summary;
    
    @Type(type = "com.vladmihalcea.hibernate.type.array.StringArrayType")
    @Column(name = "key_characters", columnDefinition = "text[]")
    private String[] keyCharacters = new String[0];
    
    @Type(type = "com.vladmihalcea.hibernate.type.array.StringArrayType")
    @Column(name = "key_events", columnDefinition = "text[]")
    private String[] keyEvents = new String[0];
    
    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private Timestamp createdAt;
    
    // Unique constraint
    @Table(uniqueConstraints = {
        @UniqueConstraint(columnNames = {"documentId", "level"})
    })
}
```

### 인덱스

```java
@Table(
    name = "document_summaries",
    indexes = {
        @Index(name = "idx_summaries_project_level", columnList = "projectId, level")
    }
)
```

---

## 2. character_timeline (Phase 6: 캐릭터 타임라인)

### 용도
- 캐릭터의 상태 변화 추적 (챕터별)
- 캐릭터 일관성 검증

### JPA Entity 정의

```java
@Entity
@Table(name = "character_timeline")
public class CharacterTimeline {
    
    @Id
    @GeneratedValue(generator = "UUID")
    @GenericGenerator(name = "UUID", strategy = "org.hibernate.id.UUIDGenerator")
    private UUID id;
    
    @Column(nullable = false)
    private UUID projectId;
    
    @Column(nullable = false, length = 255)
    private String characterName;
    
    @Column(nullable = false)
    private Integer chapter;
    
    @Column
    private UUID documentId;
    
    // 상태 추적 필드
    @Column(length = 50)
    private String healthStatus;
    
    @Column(length = 50)
    private String emotionalState;
    
    @Column(length = 255)
    private String currentLocation;
    
    // 변화 기록 (JSONB)
    @Type(type = "com.vladmihalcea.hibernate.type.json.JsonBinaryType")
    @Column(columnDefinition = "jsonb")
    private Map<String, String> stateChanges = new HashMap<>();
    
    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private Timestamp createdAt;
    
    // Unique constraint
    @Table(uniqueConstraints = {
        @UniqueConstraint(columnNames = {"projectId", "characterName", "chapter"})
    })
}
```

### 인덱스

```java
@Table(
    name = "character_timeline",
    indexes = {
        @Index(name = "idx_timeline_character", columnList = "projectId, characterName"),
        @Index(name = "idx_timeline_chapter", columnList = "projectId, chapter")
    }
)
```

---

## 의존성 추가 (pom.xml)

```xml
<!-- JSONB 타입 지원 -->
<dependency>
    <groupId>com.vladmihalcea</groupId>
    <artifactId>hibernate-types-52</artifactId>
    <version>2.20.0</version>
</dependency>

<!-- PostgreSQL 배열 타입 지원 -->
<!-- (위 hibernate-types에 포함됨) -->
```

---

## SQL 마이그레이션 (선택적)

JPA가 자동으로 테이블을 생성하지만, 수동 마이그레이션을 원하시면:

### document_summaries

```sql
CREATE TABLE IF NOT EXISTS document_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    project_id UUID NOT NULL,
    level INT NOT NULL DEFAULT 3,
    summary TEXT NOT NULL,
    key_characters TEXT[] DEFAULT '{}',
    key_events TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(document_id, level)
);

CREATE INDEX idx_summaries_project_level 
ON document_summaries(project_id, level);
```

### character_timeline

```sql
CREATE TABLE IF NOT EXISTS character_timeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    character_name VARCHAR(255) NOT NULL,
    chapter INT NOT NULL,
    document_id UUID,
    health_status VARCHAR(50),
    emotional_state VARCHAR(50),
    current_location VARCHAR(255),
    state_changes JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(project_id, character_name, chapter)
);

CREATE INDEX idx_timeline_character 
ON character_timeline(project_id, character_name);

CREATE INDEX idx_timeline_chapter 
ON character_timeline(project_id, chapter);
```

---

## 주의사항

### 1. FastAPI에서만 Write
- 이 테이블들은 **FastAPI AI Backend에서만 데이터를 쓰기**합니다
- Spring에서는 **읽기 전용**으로 사용하세요 (향후 확장 가능)

### 2. 외래키
- `document_id`, `project_id`는 외래키이지만, 마이크로서비스 아키텍처를 고려하여 **외래키 제약조건은 선택사항**입니다

### 3. 테이블 생성 타이밍
- 현재 FastAPI는 이 테이블이 없어도 작동합니다 (에러 무시)
- 하지만 **전체 기능 사용을 위해서는 테이블 생성이 필요**합니다

---

## 질문/문의

궁금하신 사항이 있으시면 AI Backend 팀에 문의해주세요.
