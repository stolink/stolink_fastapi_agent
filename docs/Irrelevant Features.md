# AI 분석에 불필요한 필드 목록

> **판단 기준**
> - ✅ **AI 분석에 필요**: 새 챕터 분석 시 이전 맥락으로 참조
> - ❌ **AI 분석에 불필요**: UI 렌더링/메타데이터 용도

---

## 1. Top-level (최상위)

| 필드 | AI 필요 | 용도 |
|------|---------|------|
| `message_type` | ❌ | 콜백 타입 구분 |
| `document_id` | ❌ | 문서 식별 |
| `status` | ❌ | 처리 상태 |
| `processing_time_ms` | ❌ | 성능 모니터링 |
| `trace_id` | ❌ | 분산 추적 |

---

## 2. sections (섹션)

| 필드 | AI 필요 | 용도 |
|------|---------|------|
| `sequence_order` | ❌ | UI 정렬 |
| `nav_title` | ❌ | 네비게이션 제목 |
| `content` | ✅ | RAG 검색 |
| `embedding` | ✅ | 벡터 검색 (FastAPI pgvector) |
| `related_characters` | ❌ | UI 렌더링 |
| `related_events` | ❌ | UI 렌더링 |

---

## 3. characters (캐릭터)

| 필드 | AI 필요 | 용도 |
|------|---------|------|
| `_id` | ❌ | 내부 식별자 |
| `role` | ✅ | 캐릭터 역할 |
| `profile.character_id` | ❌ | Spring UUID |
| `profile.name` | ✅ | 이름 |
| `profile.age` | ⚠️ | 선택 |
| `profile.gender` | ⚠️ | 선택 |
| `profile.race` | ⚠️ | 선택 |
| `profile.mbti` | ❌ | UI용 |
| `profile.personality` | ✅ | 성격 분석 |
| `profile.backstory` | ✅ | 맥락 파악 |
| `profile.faction` | ⚠️ | 선택 |
| `aliases` | ✅ | 동일인 식별 |
| `status` | ✅ | 생사 여부 |
| **appearance (전체)** | ❌ | 이미지 생성용 |
| `relations.graph` | ✅ | 관계 분석 (Neo4j) |
| `relations.event_refs` | ⚠️ | 이벤트 연결 |
| `relations.location_context` | ❌ | UI용 |
| **current_mood (전체)** | ❌ | 변동성 높음 |
| **meta (전체)** | ❌ | 메타데이터 |
| `embedding` | ✅ | 벡터 검색 (Neo4j) |

---

## 4. events (이벤트)

| 필드 | AI 필요 | 용도 |
|------|---------|------|
| `event_id` | ⚠️ | 참조용 |
| `event_type` | ✅ | 이벤트 유형 |
| `narrative_summary` | ✅ | 서사 요약 |
| `description` | ✅ | 상세 설명 |
| `participants` | ✅ | 참여자 |
| `location_ref` | ⚠️ | 장소 참조 |
| `prev_event_id` | ⚠️ | 시퀀스 |
| `timestamp` | ❌ | 스토리 내 시간 |
| `importance` | ⚠️ | 중요도 |
| `changes_made` | ❌ | 변경 추적 |
| `embedding` | ✅ | 벡터 검색 (Neo4j) |
| `chapter` | ❌ | UI 정렬 |
| `sequence_order` | ❌ | UI 정렬 |
| `document_id` | ❌ | 문서 식별 |

---

## 5. settings (배경/장소)

| 필드 | AI 필요 | 용도 |
|------|---------|------|
| `setting_id` | ❌ | 식별자 |
| `name` | ✅ | 장소 이름 |
| `location_name` | ⚠️ | 중복 |
| `location_type` | ✅ | 장소 유형 |
| `parent_location` | ⚠️ | 계층 구조 |
| `visual_background` | ❌ | 이미지 생성 |
| `atmosphere` | ⚠️ | 분위기 |
| `time_of_day` | ❌ | 이미지 생성 |
| `lighting` | ❌ | 이미지 생성 |
| `weather` | ❌ | 이미지 생성 |
| `art_style` | ❌ | 이미지 생성 |
| `description` | ✅ | 설명 |
| `notable_features` | ⚠️ | 특징 |
| `significance` | ⚠️ | 중요성 |
| `first_mentioned` | ❌ | 메타 |
| `is_primary` | ❌ | 플래그 |

---

## 6. relationships (관계)

모든 필드 **필요** (Neo4j 저장용)

---

## 요약: 불필요한 필드

```
# Top-level
- message_type
- document_id
- status
- processing_time_ms
- trace_id

# sections
- sequence_order
- nav_title
- related_characters
- related_events

# characters
- _id
- profile.character_id
- profile.mbti
- appearance (전체)
- relations.location_context
- current_mood (전체)
- meta (전체)

# events
- timestamp
- changes_made
- chapter
- sequence_order
- document_id

# settings
- setting_id
- visual_background
- time_of_day
- lighting
- weather
- art_style
- first_mentioned
- is_primary
```

> 이 필드들을 제거하면 AI 분석 컨텍스트 크기를 **30~40%** 줄일 수 있습니다.