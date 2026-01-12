# StoLink AI Backend - 디테일한 엣지 케이스 테스트 시나리오

> **작성 기준**: 실제 코드 구현 분석 완료  
> **커버리지**: 데이터 무결성, 중복 방지, 증분 업데이트, 캐시 일관성, 동시성

---

## 📑 목차

1. [중복 생성 방지 (Deduplication)](#1-중복-생성-방지-deduplication)
2. [증분 업데이트 (Incremental Updates)](#2-증분-업데이트-incremental-updates)
3. [임베딩 캐시 시나리오](#3-임베딩-캐시-시나리오)
4. [Neo4j 엔티티 저장 및 병합](#4-neo4j-엔티티-저장-및-병합)
5. [PostgreSQL 섹션 저장](#5-postgresql-섹션-저장)
6. [동시성 및 경쟁 상태](#6-동시성-및-경쟁-상태)
7. [엔티티 해소 (Entity Resolution)](#7-엔티티-해소-entity-resolution)
8. [상태 전이 및 롤백](#8-상태-전이-및-롤백)
9. [데이터 일관성](#9-데이터-일관성)
10. [성능 및 리소스 관리](#10-성능-및-리소스-관리)

---

## 1. 중복 생성 방지 (Deduplication)

### 1.1 임베딩 캐시 중복 방지

#### TC-CACHE-001: 같은 텍스트 임베딩 재요청
**시나리오**:
```python
# 동일 프로젝트 내에서 동일 텍스트 분석
request_1 = {"content": "아린은 검을 받아들었다"}
request_2 = {"content": "아린은 검을 받아들었다"}  # 완전 동일
```

**예상 동작**:
1. request_1: Redis cache miss → Gemini API 호출 → 임베딩 생성 → Redis에 저장 (키: `emb:hash(text)`, TTL: 24시간)
2. request_2: Redis cache hit → 즉시 반환 (Gemini API 호출 없음)

**검증**:
- [ ] Gemini API 호출이 1회만 발생
- [ ] request_2의 응답 시간 < 100ms
- [ ] 두 임베딩 벡터가 완전히 동일
- [ ] Redis에 키 `emb:hash(...)` 존재 확인
- [ ] 로그에 "Embedding cache hit" 기록

**관련 코드**: `app/services/embedding_service.py:124-131`

---

#### TC-CACHE-002: 공백/대소문자만 다른 텍스트
**시나리오**:
```python
request_1 = {"content": "아린은 검을 받아들었다"}
request_2 = {"content": "아린은 검을   받아들었다  "}  # 여러 공백
request_3 = {"content": "Arin picked up the sword"}
request_4 = {"content": "arin picked up the sword"}  # 소문자
```

**예상 동작**:
- request_1, request_2: **다른 해시** → 별도 캐싱 (현재 구현: `hash(text)` 그대로 사용)
- request_3, request_4: **다른 해시** → 별도 캐싱

**개선 제안**:
- 임베딩 전 텍스트 정규화: `text.strip().lower()`
- 연속 공백 제거: `re.sub(r'\s+', ' ', text)`

**검증**:
- [ ] 현재: 4개 모두 별도 API 호출
- [ ] 개선 후: 2개 API 호출 (한글 1, 영문 1)

---

#### TC-CACHE-003: 24시간 후 TTL 만료
**시나리오**:
```python
# Day 1
embed("아린은 검을 받아들었다")  # Cache miss → API 호출

# Day 2 (23시간 후)
embed("아린은 검을 받아들었다")  # Cache hit

# Day 3 (25시간 후)
embed("아린은 검을 받아들었다")  # TTL 만료 → API 호출
```

**검증**:
- [ ] 24시간 이내: cache hit
- [ ] 24시간 이후: cache miss, 새로운 TTL 설정
- [ ] Redis `TTL emb:...` 명령으로 확인

---

### 1.2 Neo4j 캐릭터 중복 방지

#### TC-NEO4J-001: 같은 프로젝트 내 동일 이름 캐릭터
**시나리오**:
```python
# 문서 1 분석
doc_1_characters = [{"name": "아린", "role": "protagonist"}]

# 문서 2 분석 (같은 프로젝트)
doc_2_characters = [{"name": "아린", "role": "protagonist"}]
```

**예상 동작** (`db_query_service.py:1680`):
- `MERGE (c:Character {project_id: $pid, name: $name})` 사용
- 같은 `project_id + name`이면 **업데이트**, 없으면 생성
- `source_documents` 배열에 doc_id 추가 (중복 없이)

**검증**:
- [ ] Neo4j에 "아린" 노드 **1개만** 존재
- [ ] `source_documents` = [doc_1_id, doc_2_id]
- [ ] `profileJson`은 더 긴 쪽으로 유지 (size 비교)
- [ ] Cypher 쿼리: `MATCH (c:Character {project_id: $pid}) RETURN count(c)`

**관련 코드**: `app/services/db_query_service.py:1678-1742`

---

#### TC-NEO4J-002: 임베딩 기반 중복 감지
**시나리오**:
```python
# 문서 1
doc_1_characters = [
    {"name": "아린", "role": "protagonist", "embedding": [0.1, 0.2, ...]}
]

# 문서 2 (약간 다른 이름, 같은 캐릭터)
doc_2_characters = [
    {"name": "Arin", "role": "protagonist", "embedding": [0.1, 0.2, ...]}  # 유사 임베딩
]
```

**예상 동작** (`db_query_service.py:1663-1676`):
- `_find_similar_character()` 호출
- 임베딩 코사인 유사도 > 0.9 → 같은 캐릭터로 판단
- "Arin"을 "아린"의 **별칭(aliases)**으로 추가
- 실제 저장은 "아린" 이름으로 MERGE

**검증**:
- [ ] Neo4j에 1개 캐릭터만 존재
- [ ] `name = "아린"`
- [ ] `aliases = ["Arin"]`
- [ ] 로그: `[DEDUP] Merging 'Arin' with existing '아린'`

---

#### TC-NEO4J-003: 서로 다른 프로젝트의 같은 이름
**시나리오**:
```python
# Project A
project_a_characters = [{"name": "아린", "role": "protagonist"}]

# Project B (완전 다른 프로젝트)
project_b_characters = [{"name": "아린", "role": "villain"}]
```

**예상 동작**:
- Neo4j MERGE 조건: `{project_id: $pid, name: $name}`
- **다른 project_id** → 별개 노드 2개 생성

**검증**:
- [ ] Neo4j에 "아린" 노드 **2개** 존재
- [ ] 각각 다른 `project_id` 속성
- [ ] 각각 다른 `role` (protagonist vs villain)

---

### 1.3 PostgreSQL 섹션 중복 방지

#### TC-SECTION-001: 같은 문서 재분석 시 섹션 삭제/재생성
**시나리오**:
```python
# 1차 분석
analyze(document_id="doc-123", content="원본 텍스트")
# → sections 테이블에 5개 섹션 저장

# 2차 분석 (같은 document_id)
analyze(document_id="doc-123", content="수정된 텍스트")
# → 섹션 재생성
```

**예상 동작** (`db_query_service.py:794-810`):
1. 기존 섹션 삭제: `DELETE FROM sections WHERE document_id = $1`
2. 새 섹션 삽입 (트랜잭션 내)

**검증**:
- [ ] 1차 분석 후: sections 테이블에 5개 행
- [ ] 2차 분석 후: **여전히 5개 행** (중복 없음)
- [ ] 모든 섹션의 `document_id = "doc-123"`
- [ ] 섹션 ID는 새로 생성됨 (UUID 변경)

**주의**: 트랜잭션 실패 시 rollback → 섹션 없는 상태

---

#### TC-SECTION-002: 동시 분석 요청 시 섹션 경쟁
**시나리오**:
```python
# 동시 요청 (race condition)
Thread 1: analyze(document_id="doc-123", content="v1")
Thread 2: analyze(document_id="doc-123", content="v2")
```

**예상 동작**:
- PostgreSQL 트랜잭션 격리 수준에 따라:
  - **READ COMMITTED** (기본): 마지막 커밋이 승리
  - 두 트랜잭션 모두 `DELETE` 실행 → 경쟁
  - 최종: Thread 2의 섹션만 남음

**검증**:
- [ ] 섹션 중복 없음 (5개 또는 7개, 총합 아님)
- [ ] `sequence_order`가 연속적
- [ ] DB 로그에 lock wait 흔적

**개선 제안**:
- Document-level lock: `SELECT ... FOR UPDATE`
- 또는 분석 job 큐에서 중복 제거

---

## 2. 증분 업데이트 (Incremental Updates)

### 2.1 Content Hash 기반 변경 감지

#### TC-INCR-001: v1 → v2 업데이트 시 변경된 섹션만 재분석
**시나리오**:
```python
# v1: 3개 섹션
doc_v1 = """
Section 1: 아린은 검을 받아들었다.
Section 2: 카엘이 그녀를 바라보았다.
Section 3: 전투가 시작되었다.
"""

# v2: Section 3만 수정, Section 1-2는 동일
doc_v2 = """
Section 1: 아린은 검을 받아들었다.
Section 2: 카엘이 그녀를 바라보았다.
Section 3: 치열한 전투가 벌어졌다. 용이 나타났다.  # 수정됨
"""
```

**예상 동작** (`db_query_service.py:1272-1338`):
1. 기존 섹션 해시 조회: `get_previous_section_hashes(doc_id)`
2. 새 섹션 청킹 및 해시 계산: `SHA256(content)[:16]`
3. 해시 비교:
   - Section 1: 해시 일치 → **스킵**
   - Section 2: 해시 일치 → **스킵**
   - Section 3: 해시 불일치 → **재분석**
4. Section 3부터 LLM 파이프라인 실행

**검증**:
- [ ] Section 1-2: 캐릭터 재추출 없음
- [ ] Section 3: "용" 엔티티 새로 추출
- [ ] 로그: `[INCREMENTAL] Change detected at section 3`
- [ ] 로그: `[INCREMENTAL] Section 1 match`, `Section 2 match`
- [ ] LLM API 호출 횟수: Section 3만 처리 (1/3)

**관련 코드**: 
- `app/services/db_query_service.py:1294-1338` (detect_change_point)
- `app/services/document_analysis_consumer.py`

---

#### TC-INCR-002: 앞부분 수정 시 전체 재분석
**시나리오**:
```python
# v1
doc_v1 = """
Section 1: 아린은 검을 받아들었다.
Section 2: 카엘이 그녀를 바라보았다.
"""

# v2: Section 1 수정
doc_v2 = """
Section 1: 아린은 마법 지팡이를 받아들었다.  # 검 → 지팡이
Section 2: 카엘이 그녀를 바라보았다.
"""
```

**예상 동작**:
- `detect_change_point()` → 0 (첫 번째 섹션부터 변경)
- **전체 재분석** (Section 1, 2 모두)

**이유**: 
- 이야기는 앞에서 뒤로 흐름
- 앞부분 변경 시 뒷부분 해석도 달라질 수 있음

**검증**:
- [ ] 로그: `[INCREMENTAL] Change detected at section 1`
- [ ] Section 1, 2 모두 재분석
- [ ] "검" → "마법 지팡이"로 아이템 변경 감지

---

#### TC-INCR-003: 섹션 추가 (append)
**시나리오**:
```python
# v1: 2개 섹션
doc_v1 = """
Section 1: ...
Section 2: ...
"""

# v2: 1개 섹션 추가
doc_v2 = """
Section 1: ...
Section 2: ...
Section 3: (새로운 내용)
"""
```

**예상 동작** (`db_query_service.py:1319-1322`):
- 기존 섹션 해시 길이: 2
- 새 섹션 인덱스: 2 (0-based) >= 2
- → `return i` (index 2부터 분석)

**검증**:
- [ ] Section 1-2: 스킵
- [ ] Section 3만 분석
- [ ] 로그: `[INCREMENTAL] New section detected at index 2`

---

#### TC-INCR-004: 섹션 삭제 시 전체 재분석
**시나리오**:
```python
# v1: 3개 섹션
# v2: 2개 섹션 (Section 3 삭제)
```

**예상 동작** (`db_query_service.py:1333-1335`):
- `len(new_sections) < len(previous_hashes)`
- → `return 0` (전체 재분석)

**이유**: 
- 섹션 삭제는 문맥 파괴 가능성 높음
- 전체 재검증 필요

**검증**:
- [ ] 로그: `[INCREMENTAL] Sections were removed, full re-analysis needed`
- [ ] 모든 섹션 재분석

---

### 2.2 무변경 시나리오

#### TC-INCR-005: 완전 동일한 재분석 요청
**시나리오**:
```python
# 1차 분석
analyze(doc_id, content_v1)

# 2차 분석 (완전 동일)
analyze(doc_id, content_v1)  # 변경 없음
```

**예상 동작** (`db_query_service.py:1337-1338`):
- 모든 섹션 해시 일치
- `detect_change_point()` → `-1`
- LLM 파이프라인 **스킵**

**검증**:
- [ ] LLM API 호출 0회
- [ ] 로그: `[INCREMENTAL] No changes detected, skipping analysis`
- [ ] Callback: 기존 결과 재전송 또는 SKIPPED 상태

---

## 3. 임베딩 캐시 시나리오

### 3.1 Redis 장애 대응

#### TC-CACHE-REDIS-001: Redis 연결 실패 시 폴백
**시나리오**:
```bash
# Redis 중단
docker stop stolink-redis

# 임베딩 요청
embed("아린은 검을 받아들었다")
```

**예상 동작** (`embedding_service.py:59-74, 125-133`):
- Redis 초기화 실패 → `self._redis = None`
- 캐시 조회 스킵 → Gemini API 직접 호출
- 캐시 저장 스킵
- 서비스 계속 동작

**검증**:
- [ ] 로그: `Redis cache init failed: ... Caching disabled.`
- [ ] 임베딩은 정상 생성 (Gemini API 호출)
- [ ] 캐시 miss 로그 없음 (Redis 사용 안 함)

---

#### TC-CACHE-REDIS-002: Redis 캐시 손상 (JSON 파싱 실패)
**시나리오**:
```python
# Redis에 잘못된 데이터 삽입
redis.set("emb:1234567", "invalid json {[")

# 임베딩 요청
embed("테스트")  # hash → 1234567
```

**예상 동작** (`embedding_service.py:127-133`):
- `json.loads(cached)` → JSONDecodeError
- catch Exception → 로그 경고
- Gemini API 호출 (폴백)

**검증**:
- [ ] 로그: `Redis get failed: ...`
- [ ] 임베딩 정상 생성
- [ ] 에러로 인한 서비스 중단 없음

---

### 3.2 캐시 일관성

#### TC-CACHE-CONS-001: 같은 텍스트, 다른 프로젝트
**시나리오**:
```python
 # Project A
embed("아린은 검을 받아들었다", project_id="proj-A")

# Project B (같은 텍스트)
embed("아린은 검을 받아들었다", project_id="proj-B")
```

**현재 동작**:
- 캐시 키: `emb:hash(text)` (project_id 포함 안 됨)
- → **같은 캐시 재사용**

**예상 영향**:
- 임베딩은 텍스트 자체에 의존 (프로젝트 무관)
- → **문제 없음** (의도된 동작)

**검증**:
- [ ] 두 요청 모두 같은 임베딩 벡터
- [ ] API 호출 1회

---

## 4. Neo4j 엔티티 저장 및 병합

### 4.1 캐릭터 속성 병합 전략

#### TC-NEO4J-CHAR-001: 같은 캐릭터, 다른 속성
**시나리오**:
```python
# 문서 1
char_v1 = {
    "name": "아린",
    "role": "protagonist",
    "description": "용감한 전사",  # 짧음
    "backstory": None
}

# 문서 2
char_v2 = {
    "name": "아린",
    "role": "protagonist",
    "description": "용감하고 정의로운 전사로, 왕국을 지킨다.",  # 더 길고 상세
    "backstory": "어린 시절 부모를 잃고..."
}
```

**예상 동작** (`db_query_service.py:1694-1705`):
- **description**: size 비교 → char_v2 선택 (더 긴 쪽)
- **backstory**: `coalesce` → char_v2 선택 (NULL이 아닌 쪽)

**검증**:
- [ ] 최종 `description`: "용감하고 정의로운 전사로, 왕국을 지킨다."
- [ ] 최종 `backstory`: "어린 시절 부모를 잃고..."
- [ ] 로그: 속성 업데이트 기록

---

#### TC-NEO4J-CHAR-002: 충돌하는 role
**시나리오**:
```python
# 문서 1
char_v1 = {"name": "카엘", "role": "protagonist"}

# 문서 2 (같은 캐릭터, 다른 role)
char_v2 = {"name": "카엘", "role": "antagonist"}
```

**예상 동작** (`db_query_service.py:1683-1688`):
- `size($role) > size(coalesce(c.role, ''))`
- "antagonist" (10자) vs "protagonist" (11자)
- → "protagonist" 유지

**문제점**: 
- 길이 기반 선택은 의미론적 정확도 보장 안 함
- antagonist가 더 정확할 수 있음

**검증**:
- [ ] 최종 `role`: "protagonist" (더 긴 쪽)
- [ ] **개선 필요**: 충돌 감지 및 사용자 확인

---

#### TC-NEO4J-CHAR-003: 별칭(aliases) 누적
**시나리오**:
```python
# 문서 1
char_v1 = {"name": "아린", "aliases": ["Arin"]}

# 문서 2
char_v2 = {"name": "아린", "aliases": ["공주", "전사"]}

# 문서 3
char_v3 = {"name": "아린", "aliases": ["Arin"]}  # 중복
```

**예상 동작** (`db_query_service.py:1712-1716`):
- 별칭 중복 제거: `[a IN $aliases WHERE NOT a IN c.aliases]`
- 최종 `aliases`: ["Arin", "공주", "전사"] (순서 보장 안 됨)

**검증**:
- [ ] 중복 없이 병합
- [ ] `"Arin"`이 2번 추가되지 않음

---

### 4.2 임베딩 기반 중복 감지 정확도

#### TC-NEO4J-DED-001: 유사 임베딩, 다른 캐릭터 (False Positive)
**시나리오**:
```python
# 두 전사 캐릭터, 매우 유사한 설명
char_1 = {
    "name": "아린",
    "role": "warrior",
    "description": "용감한 전사",
    "embedding": [0.1, 0.2, 0.3, ...]
}

char_2 = {
    "name": "바린",
    "role": "warrior",
    "description": "용감한 기사",  # 유사
    "embedding": [0.1, 0.21, 0.29, ...]  # 코사인 유사도 0.95
}
```

**잠재적 문제**:
- 임베딩 유사도 > 0.9 → 같은 캐릭터로 오판
- "바린"이 "아린"의 별칭으로 추가

**검증**:
- [ ] `_find_similar_character()` 임계값 조정 필요
- [ ] 이름 유사도 추가 검증 (Levenshtein distance)

**개선 제안**:
```python
if embedding_similarity > 0.9 AND name_similarity > 0.8:
    # 같은 캐릭터로 판단
```

---

#### TC-NEO4J-DED-002: 임베딩 없는 캐릭터
**시나리오**:
```python
char = {"name": "새 캐릭터", "embedding": None}
```

**예상 동작**:
- `_find_similar_character()` 스킵
- 임베딩 없으면 중복 감지 불가
- 이름 기반만으로 MERGE

**검증**:
- [ ] 중복 감지 안 됨
- [ ] Neo4j에 별도 노드 생성

---

### 4.3 이벤트 저장

#### TC-NEO4J-EVENT-001: 같은 이벤트 ID 재저장
**시나리오**:
```python
# 문서 1
event_v1 = {
    "event_id": "evt-123",
    "description": "전투 발생",
    "participants": ["아린"]
}

# 문서 2 (같은 event_id, 추가 정보)
event_v2 = {
    "event_id": "evt-123",
    "description": "치열한 전투 발생",  # 더 상세
    "participants": ["아린", "카엘"]  # 참가자 추가
}
```

**예상 동작** (`db_query_service.py:1238-1246`):
- `ON CONFLICT (id) DO UPDATE`
- description, participants 덮어쓰기

**검증**:
- [ ] 최종 description: "치열한 전투 발생"
- [ ] 최종 participants: ["아린", "카엘"]
- [ ] Neo4j 노드 1개

**주의**: 참가자가 줄어들면 (v1→v2에서 삭제) 이전 정보 손실

---

## 5. PostgreSQL 섹션 저장

### 5.1 섹션 임베딩 저장

#### TC-SECTION-EMB-001: 임베딩 벡터 형식
**시나리오**:
```python
section = {
    "content": "...",
    "embedding": [0.1, 0.2, ..., 0.3]  # 3072 차원
}
save_sections(document_id, [section])
```

**예상 동작** (`db_query_service.py:817-823`):
- `embedding_vector = str(sec["embedding"])`
- pgvector 형식: `"[0.1, 0.2, ..., 0.3]"` (문자열)

**검증**:
- [ ] PostgreSQL 저장: `embedding::vector(3072)`
- [ ] 코사인 검색 가능: `embedding <=> query_vec`

---

#### TC-SECTION-EMB-002: 임베딩 없는 섹션
**시나리오**:
```python
section = {"content": "...", "embedding": None}
```

**예상 동작**:
- `embedding_vector = None`
- PostgreSQL에 NULL 저장

**검증**:
- [ ] 벡터 검색에서 제외됨
- [ ] 에러 없이 저장

---

### 5.2 트랜잭션 롤백

#### TC-SECTION-TX-001: 섹션 삽입 중 실패
**시나리오**:
```python
sections = [
    {"content": "Section 1", "embedding": valid_vec},
    {"content": "Section 2", "embedding": invalid_vec},  # 잘못된 차원
    {"content": "Section 3", "embedding": valid_vec}
]
```

**예상 동작**:
- trx 시작
- DELETE sections
- INSERT Section 1 (성공)
- INSERT Section 2 (실패: 차원 불일치)
- → **트랜잭션 롤백**

**검증**:
- [ ] 기존 섹션도 복구 안 됨 (DELETE 롤백)
- [ ] document_id에 섹션 0개
- [ ] 로그: `Failed to save sections`

---

## 6. 동시성 및 경쟁 상태

### 6.1 같은 문서 동시 분석

#### TC-CONCUR-001: 2개 워커가 같은 문서 분석
**시나리오**:
```bash
# RabbitMQ에 같은 document_id 메시지 2개 발행
Worker 1: process(document_id="doc-123")
Worker 2: process(document_id="doc-123")
```

**예상 동작**:
- 두 워커 모두 독립 실행
- PostgreSQL: 마지막 커밋이 섹션 덮어씀
- Neo4j: MERGE로 충돌 방지, 속성은 마지막 설정값

**검증**:
- [ ] 섹션 중복 없음
- [ ] Neo4j 캐릭터 중복 없음
- [ ] Callback 2번 전송 가능 (중복)

**개선 제안**:
- RabbitMQ 메시지 deduplication (message ID)
- Document-level distributed lock (Redis)

---

#### TC-CONCUR-002: 다른 문서, 같은 캐릭터
**시나리오**:
```python
# Worker 1
doc_1 = {"characters": [{"name": "아린", "role": "protagonist"}]}

# Worker 2 (동시)
doc_2 = {"characters": [{"name": "아린", "role": "protagonist"}]}
```

**예상 동작**:
- Neo4j MERGE: 자동 동시성 제어
- 최종: 1개 캐릭터 노드
- `source_documents` 배열에 둘 다 추가

**검증**:
- [ ] 캐릭터 1개
- [ ] `source_documents` 길이 = 2

---

### 6.2 캐시 경쟁

#### TC-CONCUR-CACHE-001: 같은 텍스트 임베딩 동시 요청
**시나리오**:
```python
# Thread 1, 2 동시에 캐시 miss
embed("아린은 검을 받아들었다")  # x2
```

**예상 동작**:
- 둘 다 Redis cache miss
- 둘 다 Gemini API 호출
- 둘 다 Redis SET 시도
- → **마지막 SET이 승리**

**검증**:
- [ ] Gemini API 호출 2회 (낭비)
- [ ] Redis에 1개 키만 존재 (같은 결과)

**개선 제안**:
- Redis `SETNX` 또는 lock 사용

---

## 7. 엔티티 해소 (Entity Resolution)

### 7.1 Global Merge 시나리오

#### TC-ER-001: 동일 캐릭터 3개 변형
**시나리오**:
```python
# 프로젝트 내 캐릭터들
characters = [
    {"id": "c1", "name": "아린", "role": "protagonist", "aliases": []},
    {"id": "c2", "name": "Arin", "role": "protagonist", "aliases": []},
    {"id": "c3", "name": "아린 공주", "role": "protagonist", "aliases": []}
]

# Global Merge 실행
```

**예상 동작** (`entity_resolution.py:293-430`):
1. Union-Find로 클러스터링
2. 퍼지 매칭:
   - "아린" ↔ "Arin": 한영 매핑 → score 100
   - "아린" ↔ "아린 공주": partial_ratio 90+
3. 같은 클러스터로 병합
4. Primary 선택: completeness 점수 최고 (c3: "아린 공주")
5. 별칭: ["아린", "Arin"]

**검증**:
- [ ] 병합 결과 1개
- [ ] `primary_id`: "c3"
- [ ] `merged_ids`: ["c1", "c2"]
- [ ] `canonical_name`: "아린 공주"
- [ ] `merged_aliases`: ["아린", "Arin"]

**관련 코드**: `app/utils/entity_resolution.py`

---

#### TC-ER-002: 충돌하는 속성
**시나리오**:
```python
characters = [
    {"id": "c1", "name": "카엘", "role": "protagonist", "status": "alive"},
    {"id": "c2", "name": "Kael", "role": "antagonist", "status": "dead"}  # 충돌!
]
```

**예상 동작** (`entity_resolution.py:398-404`):
- 일치 판정: 이름 유사도 높음
- 충돌 감지:
  - `role`: protagonist ≠ antagonist
  - `status`: alive ≠ dead
- `conflicts` 배열에 추가

**검증**:
- [ ] 병합됨 (같은 캐릭터로 판단)
- [ ] `conflicts`: ["Role conflict: 'protagonist' vs 'antagonist'", "Status conflict: 'alive' vs 'dead'"]
- [ ] Callback에 충돌 포함 → Spring에서 사용자 확인 요청

---

#### TC-ER-003: 신뢰도 점수
**시나리오**:
```python
# 퍼지 매칭으로 병합
characters = [
    {"id": "c1", "name": "아린"},
    {"id": "c2", "name": "아인"}  # 유사도 85점
]
```

**예상 동작** (`entity_resolution.py:412-419`):
- 매칭 점수: 85/100
- `confidence = 0.85`
- `classification = NEEDS_REVIEW`

**검증**:
- [ ] `confidence`: 0.85
- [ ] Spring에서 "검토 필요" 플래그

---

### 7.2 별칭 처리

#### TC-ER-ALIAS-001: 순환 별칭
**시나리오**:
```python
char_1 = {"name": "A", "aliases": ["B"]}
char_2 = {"name": "B", "aliases": ["A"]}
```

**예상 동작**:
- 별칭 교차 매칭 → 같은 캐릭터로 판단
- 병합 후:
  - `canonical_name`: "A" 또는 "B" (completeness에 따라)
  - `aliases`: ["A", "B"] 중 하나 제거

---

## 8. 상태 전이 및 롤백

### 8.1 분석 상태 관리

#### TC-STATE-001: 분석 실패 후 재시도
**시나리오**:
```python
# 1차 시도: Gemini API 타임아웃
analyze(doc_id) → FAILED

# 2차 시도: 성공
analyze(doc_id) → COMPLETED
```

**예상 동작**:
- Document 상태: PROCESSING → FAILED → PROCESSING → COMPLETED
- 섹션: 실패 시 삭제됨 (트랜잭션 롤백)
- 재시도 시 처음부터 재분석

**검증**:
- [ ] 최종 상태: COMPLETED
- [ ] 섹션 정상 저장
- [ ] Callback URL로 COMPLETED 전송

---

### 8.2 부분 실패 복구

#### TC-STATE-002: Neo4j 저장 실패, PostgreSQL 성공
**시나리오**:
```python
# Sections → PostgreSQL 저장 성공
# Characters → Neo4j 저장 실패 (connection timeout)
```

**현재 문제**:
- **데이터 불일치**: 섹션은 저장됨, 엔티티는 없음
- 재시도 시 섹션 중복 삭제/재생성

**검증**:
- [ ] 불일치 상태 확인
- [ ] 재시도 시 일관성 복구

**개선 제안**:
- Saga pattern 또는 2-phase commit
- 실패 시 PostgreSQL도 롤백

---

## 9. 데이터 일관성

### 9.1 캐릭터-이벤트 참조 무결성

#### TC-CONS-001: 존재하지 않는 캐릭터 참조
**시나리오**:
```python
event = {
    "description": "전투 발생",
    "participants": ["존재하지않는캐릭터"]
}
```

**현재 동작**:
- 이벤트는 저장됨
- 참조 무결성 검증 없음

**검증**:
- [ ] Neo4j 쿼리: 캐릭터 노드 없음
- [ ] 이벤트 노드의 `participantsJson`에 이름만 존재

**개선 제안**:
- 저장 전 캐릭터 존재 여부 확인
- 또는 Neo4j 관계로 연결: `(event)-[:INVOLVES]->(character)`

---

### 9.2 섹션-문서 일관성

#### TC-CONS-002: 문서 삭제 후 섹션 잔존
**시나리오**:
```python
# Document 삭제 (Spring에서)
DELETE FROM documents WHERE id = 'doc-123'

# Sections는?
SELECT * FROM sections WHERE document_id = 'doc-123'
```

**예상 동작**:
- Foreign Key Cascade 설정에 따라:
  - `ON DELETE CASCADE`: 섹션도 자동 삭제
  - 미설정: **고아 섹션** 발생

**검증**:
- [ ] 스키마 확인: `ALTER TABLE sections ADD CONSTRAINT ... ON DELETE CASCADE`

---

## 10. 성능 및 리소스 관리

### 10.1 메모리 사용

#### TC-PERF-MEM-001: 대용량 임베딩 배치
**시나리오**:
```python
# 1000개 섹션 동시 임베딩
texts = ["Section " + str(i) for i in range(1000)]
embeddings = await generate_embeddings_batch(texts, max_concurrent=10)
```

**예상 동작**:
- Semaphore로 동시성 제한 (10)
- 메모리: ~10 요청 × 3072 dimension × 4 bytes = 120KB

**검증**:
- [ ] 메모리 증가 < 200MB
- [ ] OOM 에러 없음

---

### 10.2 Neo4j 연결 풀

#### TC-PERF-NEO4J-001: 100개 동시 쿼리
**시나리오**:
```python
for i in range(100):
    save_character_to_neo4j(char)
```

**예상 동작**:
- Neo4j 드라이버 세션 풀 사용
- 기본 max pool size: 100

**검증**:
- [ ] 연결 고갈 없음
- [ ] 로그: "No available connections" 없음

---

## 11. 테스트 실행 가이드

### 11.1 중복 방지 테스트

```python
# test_deduplication.py
async def test_embedding_cache_dedup():
    """TC-CACHE-001"""
    service = EmbeddingService()
    
    # 1차 요청
    start = time.time()
    emb1 = await service.generate_embedding_async("테스트")
    time1 = time.time() - start
    
    # 2차 요청 (캐시됨)
    start = time.time()
    emb2 = await service.generate_embedding_async("테스트")
    time2 = time.time() - start
    
    assert emb1 == emb2
    assert time2 < 0.1  # 100ms 이내
    assert time1 > time2  # 캐시가 더 빠름
```

### 11.2 증분 업데이트 테스트

```python
async def test_incremental_update():
    """TC-INCR-001"""
    db = DatabaseQueryService()
    
    # v1 분석
    doc_v1 = "Section 1\n\nSection 2\n\nSection 3"
    await analyze(doc_id, doc_v1)
    
    # 기존 해시 저장
    hashes_v1 = await db.get_previous_section_hashes(doc_id)
    
    # v2: Section 3만 수정
    doc_v2 =  "Section 1\n\nSection 2\n\nSection 3 MODIFIED"
    change_point = db.detect_change_point(hashes_v1, new_sections)
    
    assert change_point == 2  # 3번째 섹션부터
```

---

## 12. 우선순위 매트릭스

| 카테고리 | 중요도 | 구현 난이도 | 우선순위 |
|---------|-------|-----------|---------|
| 증분 업데이트 (TC-INCR-*) | 높음 | 중간 | P0 |
| Neo4j 중복 방지 (TC-NEO4J-*) | 높음 | 낮음 | P0 |
| 임베딩 캐시 (TC-CACHE-*) | 중간 | 낮음 | P1 |
| 엔티티 해소 (TC-ER-*) | 높음 | 높음 | P1 |
| 동시성 (TC-CONCUR-*) | 중간 | 높음 | P2 |
| 데이터 일관성 (TC-CONS-*) | 높음 | 중간 | P1 |
| 성능 (TC-PERF-*) | 중간 | 낮음 | P2 |

---

## 13. 자동화 체크리스트

### 단위 테스트
- [ ] `test_embedding_cache.py` - TC-CACHE-001~005
- [ ] `test_section_dedup.py` - TC-SECTION-001~002
- [ ] `test_incremental_update.py` - TC-INCR-001~005
- [ ] `test_entity_resolution.py` - TC-ER-001~003

### 통합 테스트
- [ ] `test_e2e_dedup.py` - 전체 중복 방지 플로우
- [ ] `test_concurrent_analysis.py` - TC-CONCUR-001~002

### 수동 검증
- [ ] Neo4j Browser로 MERGE 결과 확인
- [ ] Redis CLI로 캐시 키 확인
- [ ] PostgreSQL로 섹션 해시 확인
