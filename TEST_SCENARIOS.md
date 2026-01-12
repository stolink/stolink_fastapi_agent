# StoLink AI Backend - 종합 테스트 시나리오 문서

## 📋 목차

1. [현재 구현된 테스트 시나리오](#1-현재-구현된-테스트-시나리오)
2. [기능별 테스트 시나리오](#2-기능별-테스트-시나리오)
3. [예외 시나리오](#3-예외-시나리오)
4. [통합 테스트 시나리오](#4-통합-테스트-시나리오)
5. [성능 테스트 시나리오](#5-성능-테스트-시나리오)
6. [추가 필요 테스트 시나리오](#6-추가-필요-테스트-시나리오)

---

## 1. 현재 구현된 테스트 시나리오

### 1.1 기존 테스트 파일 현황

현재 프로젝트에는 **공식적인 테스트 코드가 없습니다**:
- `tests/` 디렉토리는 존재하지만 실제 테스트 파일이 없음
- `tests/test_services/` 디렉토리에도 `__init__.py`만 존재

### 1.2 현재 사용 가능한 테스트 방법

#### 수동 테스트 API 엔드포인트

1. **헬스체크**
   ```bash
   GET http://localhost:8000/health
   ```

2. **수동 분석 트리거** (RabbitMQ 없이 테스트)
   ```bash
   POST http://localhost:8000/api/analysis/trigger
   Content-Type: application/json
   
   {
     "project_id": "test-project-uuid",
     "document_id": "test-doc-uuid",
     "content": "아린은 검을 받아들었다. 카엘이 그녀를 바라보았다.",
     "requires_deep_analysis": true
   }
   ```

3. **LLM 디버그 엔드포인트**
   ```bash
   POST http://localhost:8000/api/analysis/debug
   ```

4. **벡터 검색 테스트**
   ```bash
   POST http://localhost:8000/api/search/similar
   Content-Type: application/json
   
   {
     "query": "검을 받아들인다",
     "project_id": "test-project-uuid",
     "limit": 5,
     "threshold": 0.7
   }
   ```

5. **일관성 컨텍스트 조회**
   ```bash
   POST http://localhost:8000/api/search/context
   Content-Type: application/json
   
   {
     "document_id": "test-doc-uuid",
     "limit": 10
   }
   ```

#### 테스트용 샘플 파일
- `test_novel_300.txt` - 짧은 텍스트 (300자)
- `test_novel_1000.txt` - 중간 텍스트 (1000자)
- `test_story_v1_initial.txt` - 초기 버전
- `test_story_v2_updated.txt` - 업데이트 버전
- `test_story_part1.txt`, `test_story_part2.txt` - 연속 분석용

---

## 2. 기능별 테스트 시나리오

### 2.1 인프라 테스트

#### 2.1.1 Docker Compose 스택 테스트

**목적**: 모든 인프라가 정상적으로 시작되고 서로 통신하는지 확인

**시나리오**:
```bash
# ✅ 정상 시나리오
docker-compose -f docker-compose.standalone.yml up -d
docker-compose -f docker-compose.standalone.yml ps

# 예상 결과:
# - postgres: healthy
# - neo4j: healthy
# - rabbitmq: healthy
# - redis: healthy
# - ai-backend: healthy
```

**검증 항목**:
- [ ] PostgreSQL 포트 5432 접근 가능
- [ ] Neo4j 브라우저 http://localhost:7474 접근 가능
- [ ] RabbitMQ 관리 UI http://localhost:15672 접근 가능
- [ ] Redis 포트 6379 접근 가능
- [ ] AI Backend http://localhost:8000 접근 가능

#### 2.1.2 데이터베이스 연결 테스트

**PostgreSQL 연결**:
```python
# 테스트 코드 예시
from app.services.db_query_service import DatabaseQueryService

async def test_postgres_connection():
    db = DatabaseQueryService()
    await db.connect()
    # pgvector extension 확인
    # 스키마 존재 확인
    await db.disconnect()
```

**Neo4j 연결**:
```python
async def test_neo4j_connection():
    db = DatabaseQueryService()
    await db.connect()
    # 인덱스 존재 확인
    # 테스트 노드 생성/조회/삭제
    await db.disconnect()
```

**Redis 연결**:
```python
async def test_redis_connection():
    from app.services.embedding_service import EmbeddingService
    
    service = EmbeddingService()
    # 캐시 저장/조회 테스트
```

#### 2.1.3 RabbitMQ Consumer 테스트

**Document Analysis Queue**:
```bash
# Spring에서 발행하는 메시지 형식
{
  "message_type": "DOCUMENT_ANALYSIS",
  "job_id": "test-job-uuid",
  "document_id": "test-doc-uuid",
  "project_id": "test-project-uuid",
  "content": "테스트 컨텐츠...",
  "callback_url": "http://spring:8080/api/internal/ai/analysis/callback",
  "requires_deep_analysis": true,
  "analysis_type": "full_manuscript"
}
```

**검증 항목**:
- [ ] Consumer 시작 로그 확인
- [ ] 메시지 수신 및 ACK
- [ ] 처리 중 상태 업데이트
- [ ] 완료 후 Callback 전송

---

### 2.2 에이전트 파이프라인 테스트

#### 2.2.1 Level 1: Extraction Agents

**Character Extraction (캐릭터 추출)**

**정상 시나리오**:
```json
// Input
{
  "content": "아린은 용감한 전사였다. 그녀는 붉은 머리와 녹색 눈을 가지고 있었다. 카엘은 마법사로, 아린의 오랜 친구였다."
}

// Expected Output
{
  "characters": [
    {
      "name": "아린",
      "role": "protagonist",
      "appearance": {
        "hair_color": "붉은색",
        "eye_color": "녹색"
      },
      "personality": {
        "traits": ["용감한", "전사"]
      }
    },
    {
      "name": "카엘",
      "role": "supporting",
      "occupation": "마법사"
    }
  ]
}
```

**검증 항목**:
- [ ] 캐릭터 이름 정확 추출
- [ ] Role 분류 (주인공/조연/악당)
- [ ] 외모 정보 추출
- [ ] 성격 특성 추출
- [ ] Neo4j에 노드 저장 확인
- [ ] 임베딩 벡터 생성 확인

**Event Extraction (이벤트 추출)**

**정상 시나리오**:
```json
// Input
{
  "content": "아린은 검을 뽑았다. 갑자기 용이 나타났고, 치열한 전투가 벌어졌다. 아린은 결국 용을 물리쳤다."
}

// Expected Output
{
  "events": [
    {
      "event_type": "combat",
      "summary": "아린이 용과 전투하여 승리",
      "involved_characters": ["아린"],
      "involved_entities": ["용"],
      "location": null,
      "significance": "high"
    }
  ]
}
```

**검증 항목**:
- [ ] 이벤트 타입 분류
- [ ] 관련 캐릭터 매칭
- [ ] 인과 관계 파악
- [ ] Neo4j에 이벤트 노드 및 관계 저장

**Setting Extraction (배경 추출)**

**정상 시나리오**:
```json
// Input
{
  "content": "어둡고 축축한 동굴 안. 벽면에는 이상한 문자가 새겨져 있었다."
}

// Expected Output
{
  "settings": [
    {
      "name": "동굴",
      "location_type": "indoor",
      "attributes": {
        "atmosphere": "어둡고 축축한",
        "features": ["이상한 문자"]
      }
    }
  ]
}
```

**검증 항목**:
- [ ] 장소 이름 추출
- [ ] 장소 타입 분류
- [ ] 분위기/특징 파악
- [ ] Neo4j에 저장

#### 2.2.2 Level 2: Analysis Agents

**Relationship Analysis (관계 분석)**

**정상 시나리오**:
```json
// Input
{
  "characters": [
    {"name": "아린"},
    {"name": "카엘"}
  ],
  "content": "아린은 카엘을 신뢰했다. 그들은 10년 지기 친구였다."
}

// Expected Output
{
  "relationships": [
    {
      "source": "아린",
      "target": "카엘",
      "relation_type": "TRUST",
      "strength": 9,
      "description": "10년 지기 친구"
    }
  ]
}
```

**검증 항목**:
- [ ] 관계 타입 분류 (ALLY, ENEMY, MENTOR, FAMILY 등)
- [ ] 관계 강도 추정 (1-10)
- [ ] Neo4j 관계 엣지 생성
- [ ] 양방향 관계 처리

**Consistency Check (일관성 검증)**

**정상 시나리오**:
```json
// 이전 문서: "아린의 눈은 녹색이다"
// 현재 문서: "아린의 파란 눈이 빛났다"

// Expected Output
{
  "consistency_report": {
    "conflicts": [
      {
        "type": "appearance_conflict",
        "entity": "아린",
        "field": "eye_color",
        "previous_value": "녹색",
        "current_value": "파란색",
        "severity": "high"
      }
    ],
    "overall_score": 60,
    "requires_reextraction": false
  }
}
```

**검증 항목**:
- [ ] 캐릭터 속성 충돌 감지
- [ ] 설정 충돌 감지
- [ ] 타임라인 충돌 감지
- [ ] 충돌 심각도 평가
- [ ] 재추출 필요 여부 판단

#### 2.2.3 Level 3: Validation

**Validator Agent**

**정상 시나리오**:
```json
// Expected Output
{
  "validation": {
    "is_valid": true,
    "quality_score": 95,
    "action": "approve",
    "issues": []
  }
}
```

**검증 항목**:
- [ ] 필수 필드 존재 여부
- [ ] 데이터 형식 정확성
- [ ] 품질 점수 계산
- [ ] 승인/재처리/거부 판단

---

### 2.3 Document Analysis Consumer 테스트

#### 2.3.1 Semantic Chunking (의미 기반 분할)

**정상 시나리오**:
```python
# Input: 4000자 이상의 긴 텍스트
content = """
[챕터 내용...]
"""

# Expected Behavior:
# 1. 단락 단위 분리 (\n\n 기준)
# 2. 각 단락의 임베딩 생성
# 3. 유사도 기반 병합 (threshold=0.6)
# 4. 최소/최대 길이 제약
```

**검증 항목**:
- [ ] 적절한 섹션 수 생성 (너무 많거나 적지 않음)
- [ ] 각 섹션의 의미적 일관성
- [ ] 섹션별 임베딩 생성
- [ ] PostgreSQL sections 테이블에 저장

#### 2.3.2 Context Building (컨텍스트 구축)

**정상 시나리오**:
```python
# 프로젝트의 기존 데이터:
# - 캐릭터 10명
# - 이벤트 50개
# - 설정 5개

# 새 문서 분석 시:
# 1. 기존 캐릭터 임베딩 검색 (RAG)
# 2. 최근 이벤트 조회
# 3. 챕터 내 다른 문서 요약
# 4. Hierarchical Context 생성
```

**검증 항목**:
- [ ] RAG 기반 유사 캐릭터 검색
- [ ] 최근 이벤트 시계열 조회
- [ ] 부모 폴더(챕터) 요약 포함
- [ ] 컨텍스트 크기 제한 (토큰 제약)

#### 2.3.3 Callback 전송

**정상 시나리오**:
```json
// Callback to Spring
POST http://spring:8080/api/internal/ai/analysis/callback

{
  "message_type": "DOCUMENT_ANALYSIS_RESULT",
  "document_id": "doc-uuid",
  "status": "COMPLETED",
  "consistency_report": {...},
  "validation": {...},
  "document_summary": {
    "summary": "챕터 요약...",
    "key_characters": ["아린", "카엘"],
    "key_events": ["전투", "만남"],
    "level": 3
  },
  "character_timelines": [...],
  "processing_time_ms": 5000
}
```

**검증 항목**:
- [ ] Callback URL 접근 가능
- [ ] 올바른 JSON 형식
- [ ] Spring에서 정상 수신 (200 OK)
- [ ] 재시도 로직 (실패 시)

---

### 2.4 임베딩 및 벡터 검색 테스트

#### 2.4.1 Gemini Embedding 생성

**정상 시나리오**:
```python
from app.services.embedding_service import generate_embedding_async

text = "아린은 용감한 전사다"
embedding = await generate_embedding_async(text)

# Expected:
assert len(embedding) == 3072  # Gemini embedding dimension
assert all(isinstance(x, float) for x in embedding)
```

**검증 항목**:
- [ ] 임베딩 차원 정확성 (3072)
- [ ] 재시도 로직 (Rate Limit)
- [ ] Redis 캐싱 동작
- [ ] 배치 처리 성능

#### 2.4.2 Neo4j Vector Search

**정상 시나리오**:
```python
# 유사 캐릭터 검색
query_embedding = [...]  # 3072 dimension
results = await db.search_similar_characters(
    project_id="test-project",
    query_embedding=query_embedding,
    top_k=5
)

# Expected:
# - 유사도 높은 순 정렬
# - 같은 프로젝트 내 캐릭터만
# - 임베딩 벡터 포함
```

**검증 항목**:
- [ ] 벡터 인덱스 사용 (성능)
- [ ] 유사도 점수 정확성
- [ ] 프로젝트 필터링
- [ ] Top-K 제한

#### 2.4.3 PostgreSQL pgvector 검색

**정상 시나리오**:
```python
# 유사 섹션 검색
results = await db.search_similar_sections(
    embedding=[...],
    project_id="test-project",
    limit=10,
    threshold=0.7
)

# Expected:
# - 유사도 >= 0.7인 섹션만
# - 최대 10개
# - 코사인 유사도 포함
```

**검증 항목**:
- [ ] pgvector extension 설치
- [ ] 인덱스 사용 (IVFFlat/HNSW)
- [ ] 거리 함수 (cosine)
- [ ] 성능 (대량 데이터)

---

### 2.5 Global Merge Consumer 테스트

#### 2.5.1 Entity Resolution (엔티티 해소)

**정상 시나리오**:
```python
# 프로젝트 내 캐릭터:
# - "아린" (문서 1)
# - "Arin" (문서 2)
# - "아린 공주" (문서 3)

# Global Merge 실행 시:
# -> 같은 캐릭터로 병합
# -> 표준 이름: "아린"
# -> 별칭: ["Arin", "아린 공주"]
```

**검증 항목**:
- [ ] 임베딩 유사도 기반 매칭
- [ ] 이름 유사도 매칭 (편집 거리)
- [ ] 속성 충돌 감지
- [ ] 병합 신뢰도 점수
- [ ] Spring Callback 전송

---

## 3. 예외 시나리오

### 3.1 인프라 장애

#### 3.1.1 PostgreSQL 연결 끊김

**시나리오**:
```bash
# PostgreSQL 중단
docker stop stolink-postgres

# AI Backend 동작 확인
# - 연결 재시도 로직
# - 에러 핸들링
# - 로그 기록
```

**예상 동작**:
- [ ] 재연결 시도 (최대 5회)
- [ ] 백오프 지연 (2^n seconds)
- [ ] 사용자 친화적 에러 메시지
- [ ] Callback에 FAILED 상태 전송

#### 3.1.2 Neo4j 연결 끊김

**시나리오**:
```bash
docker stop stolink-neo4j
```

**예상 동작**:
- [ ] Session expired 예외 처리
- [ ] 드라이버 재초기화
- [ ] 쿼리 재시도
- [ ] 폴백 동작 정의

#### 3.1.3 RabbitMQ 다운

**시나리오**:
```bash
docker stop stolink-rabbitmq
```

**예상 동작**:
- [ ] Consumer 재연결 루프
- [ ] 메시지 손실 방지 (Persistent Queue)
- [ ] Dead Letter Queue 설정
- [ ] 알림/모니터링

#### 3.1.4 Redis 캐시 장애

**시나리오**:
```bash
docker stop stolink-redis
```

**예상 동작**:
- [ ] 캐싱 비활성화 모드로 전환
- [ ] 직접 임베딩 생성
- [ ] 성능 저하 로그 기록
- [ ] 서비스 계속 가능

---

### 3.2 데이터 예외

#### 3.2.1 빈 컨텐츠

**시나리오**:
```json
{
  "content": ""
}
```

**예상 동작**:
- [ ] 조기 검증 실패
- [ ] 적절한 에러 메시지
- [ ] Callback에 에러 전송

#### 3.2.2 너무 긴 컨텐츠

**시나리오**:
```python
# 100,000자 이상의 텍스트
content = "..." * 100000
```

**예상 동작**:
- [ ] Chunking으로 분할 처리
- [ ] 메모리 제한 모니터링
- [ ] 타임아웃 설정
- [ ] 진행률 업데이트

#### 3.2.3 특수문자/인코딩 이슈

**시나리오**:
```python
content = "\x00\xff\xfe"  # 깨진 인코딩
```

**예상 동작**:
- [ ] UTF-8 변환 시도
- [ ] 비정상 문자 제거
- [ ] 에러 로그 기록
- [ ] 가능한 범위 내 처리

#### 3.2.4 JSON 파싱 실패

**시나리오**:
```python
# LLM이 잘못된 JSON 반환
response = "```json\n{invalid json}```"
```

**예상 동작**:
- [ ] JSON 추출 시도 (마크다운 코드블록)
- [ ] 재시도 (다른 프롬프트)
- [ ] 폴백: 텍스트 파싱
- [ ] Validation 단계에서 거부

---

### 3.3 LLM 에러

#### 3.3.1 Gemini API Rate Limit

**시나리오**:
```
429 Too Many Requests
```

**예상 동작**:
- [ ] Exponential backoff (2, 4, 8, 16, 32초)
- [ ] 최대 재시도 5회
- [ ] 로그 기록
- [ ] 실패 시 FAILED 콜백

#### 3.3.2 Gemini API 키 없음/잘못됨

**시나리오**:
```
401 Unauthorized
```

**예상 동작**:
- [ ] 즉시 실패 (재시도 없음)
- [ ] 명확한 에러 메시지
- [ ] 설정 가이드 출력
- [ ] 서비스 시작 차단

#### 3.3.3 타임아웃

**시나리오**:
```
LLM 응답 30초 이상 소요
```

**예상 동작**:
- [ ] 타임아웃 설정 (기본 30초)
- [ ] 재시도 1회
- [ ] 실패 시 에러 처리

---

### 3.4 비즈니스 로직 예외

#### 3.4.1 캐릭터가 추출되지 않음

**시나리오**:
```python
# 풍경 묘사만 있는 텍스트
content = "아름다운 산맥이 펼쳐져 있다. 하늘은 푸르다."
```

**예상 동작**:
- [ ] 빈 캐릭터 배열 반환
- [ ] Validation 경고 (캐릭터 없음)
- [ ] 계속 진행 (에러 아님)

#### 3.4.2 일관성 충돌 과다

**시나리오**:
```python
# 10개 이상의 심각한 충돌
conflicts = [...]  # 10+ high severity conflicts
```

**예상 동작**:
- [ ] `requires_reextraction: true` 반환
- [ ] Supervisor에서 재추출 트리거
- [ ] 최대 재시도 3회
- [ ] 3회 실패 시 WARNING 상태로 완료

#### 3.4.3 Entity Resolution 충돌

**시나리오**:
```python
# "아린"과 "Arin"이 속성이 완전히 다름
# - 아린: 전사, 붉은 머리
# - Arin: 마법사, 검은 머리
```

**예상 동작**:
- [ ] 낮은 신뢰도 점수
- [ ] 충돌 필드 리스트 반환
- [ ] 수동 병합 필요 플래그
- [ ] Spring에서 사용자 확인 요청

---

## 4. 통합 테스트 시나리오

### 4.1 E2E: 단일 문서 분석

**시나리오**:
1. Spring에서 RabbitMQ로 메시지 발행
2. AI Backend Consumer 수신
3. 전체 파이프라인 실행
4. Spring Callback 전송
5. Spring에서 DB 저장 확인

**검증 항목**:
- [ ] 전체 처리 시간 < 30초 (1000자 기준)
- [ ] PostgreSQL, Neo4j 모두 저장
- [ ] Callback 정상 수신
- [ ] 로그 추적 가능 (trace_id)

### 4.2 E2E: 다중 문서 분석

**시나리오**:
1. 챕터 내 문서 5개 순차 분석
2. 각 문서는 이전 문서 컨텍스트 참조
3. 마지막 문서는 전체 챕터 요약 포함

**검증 항목**:
- [ ] 문서 순서 보장
- [ ] 컨텍스트 누적 확인
- [ ] 캐릭터 중복 제거
- [ ] Global Merge 트리거

### 4.3 E2E: Global Merge

**시나리오**:
1. 프로젝트 내 모든 문서 1차 분석 완료
2. Spring에서 Global Merge 메시지 발행
3. AI Backend에서 Entity Resolution
4. 병합 결과 Callback

**검증 항목**:
- [ ] 중복 엔티티 감지
- [ ] 병합 실행
- [ ] Neo4j 그래프 업데이트
- [ ] Spring RDB 동기화

---

## 5. 성능 테스트 시나리오

### 5.1 처리 속도 테스트

| 문서 크기 | 목표 처리 시간 |
|----------|--------------|
| 300자 (짧은 단편) | < 10초 |
| 1,000자 (일반 챕터) | < 30초 |
| 5,000자 (긴 챕터) | < 2분 |
| 10,000자 (매우 긴 챕터) | < 5분 |

### 5.2 동시성 테스트

**시나리오**:
```python
# 10개 문서 동시 분석 요청
for i in range(10):
    publish_message(f"doc-{i}")

# 예상:
# - Consumer prefetch_count=20
# - 동시 처리
# - 리소스 사용량 모니터링
```

**검증 항목**:
- [ ] CPU 사용률 < 80%
- [ ] 메모리 < 2GB
- [ ] DB 연결 풀 고갈 없음
- [ ] 타임아웃 없음

### 5.3 대용량 프로젝트 테스트

**시나리오**:
```
프로젝트:
- 캐릭터 100명
- 이벤트 1,000개
- 설정 50개
- 문서 200개
```

**검증 항목**:
- [ ] RAG 검색 성능 (< 1초)
- [ ] 벡터 인덱스 효율성
- [ ] Global Merge 시간 (< 10분)
- [ ] 메모리 누수 없음

---

## 6. 추가 필요 테스트 시나리오

### 6.1 Unit Tests (단위 테스트)

#### 6.1.1 필요한 서비스별 테스트

```python
# tests/test_services/test_embedding_service.py
class TestEmbeddingService:
    def test_generate_embedding_success(self):
        """정상적인 임베딩 생성"""
        pass
    
    def test_generate_embedding_empty_text(self):
        """빈 텍스트 처리"""
        pass
    
    def test_generate_embedding_rate_limit(self):
        """Rate Limit 재시도"""
        pass
    
    def test_batch_embedding(self):
        """배치 처리"""
        pass

# tests/test_services/test_chunking_service.py
class TestChunkingService:
    def test_semantic_chunking(self):
        """의미 기반 분할"""
        pass
    
    def test_fallback_chunking(self):
        """임베딩 실패 시 폴백"""
        pass

# tests/test_services/test_db_query_service.py
class TestDatabaseQueryService:
    def test_postgres_connection(self):
        """PostgreSQL 연결"""
        pass
    
    def test_neo4j_connection(self):
        """Neo4j 연결"""
        pass
    
    def test_vector_search(self):
        """벡터 검색"""
        pass

# tests/test_services/test_rag_service.py
class TestRAGService:
    def test_retrieve_relevant_events(self):
        """관련 이벤트 검색"""
        pass
```

#### 6.1.2 필요한 에이전트별 테스트

```python
# tests/test_agents/test_character_extraction.py
class TestCharacterExtraction:
    def test_extract_single_character(self):
        """단일 캐릭터 추출"""
        pass
    
    def test_extract_multiple_characters(self):
        """다중 캐릭터 추출"""
        pass
    
    def test_extract_no_characters(self):
        """캐릭터 없는 텍스트"""
        pass

# tests/test_agents/test_event_extraction.py
# tests/test_agents/test_setting_extraction.py
# tests/test_agents/test_relationship_analysis.py
# tests/test_agents/test_consistency_check.py
# tests/test_agents/test_validator.py
```

---

### 6.2 Integration Tests (통합 테스트)

```python
# tests/integration/test_full_pipeline.py
class TestFullPipeline:
    def test_short_text_analysis(self):
        """짧은 텍스트 전체 파이프라인"""
        pass
    
    def test_long_text_with_chunking(self):
        """긴 텍스트 + Chunking"""
        pass
    
    def test_incremental_analysis(self):
        """점진적 분석 (컨텍스트 누적)"""
        pass

# tests/integration/test_rabbitmq_consumer.py
class TestRabbitMQConsumer:
    def test_message_consumption(self):
        """메시지 수신 및 처리"""
        pass
    
    def test_callback_sending(self):
        """Callback 전송"""
        pass
```

---

### 6.3 Regression Tests (회귀 테스트)

**목적**: 이전 버전과 결과 비교

```python
# tests/regression/test_extraction_quality.py
class TestExtractionQuality:
    def test_character_extraction_baseline(self):
        """기준 데이터셋으로 캐릭터 추출 품질 측정"""
        # Golden dataset 준비
        # 현재 모델로 추출
        # F1 Score 계산
        # 기준치(90%) 이상 확인
        pass
```

**데이터셋**:
- [ ] 표준 테스트 세트 생성 (50개 문서)
- [ ] 수동 라벨링 (ground truth)
- [ ] 정기 실행 (CI/CD)

---

### 6.4 Stress Tests (부하 테스트)

```python
# tests/stress/test_concurrent_load.py
class TestConcurrentLoad:
    def test_100_concurrent_requests(self):
        """100개 동시 요청 처리"""
        pass
    
    def test_memory_leak(self):
        """1000개 요청 후 메모리 증가 확인"""
        pass

# tests/stress/test_large_document.py
class TestLargeDocument:
    def test_50000_char_document(self):
        """50,000자 문서 처리"""
        pass
```

---

### 6.5 Security Tests (보안 테스트)

```python
# tests/security/test_input_validation.py
class TestInputValidation:
    def test_sql_injection_attempt(self):
        """SQL Injection 시도"""
        # content에 SQL 구문 포함
        # 정상적으로 escaping 되는지 확인
        pass
    
    def test_xss_attempt(self):
        """XSS 시도"""
        # HTML/JS 태그 포함
        # sanitization 확인
        pass
    
    def test_excessive_payload(self):
        """과도한 페이로드"""
        # 10MB 이상 요청
        # 거부되는지 확인
        pass
```

---

### 6.6 Monitoring & Logging Tests

```python
# tests/monitoring/test_logging.py
class TestLogging:
    def test_structured_logging(self):
        """구조화된 로그 형식"""
        pass
    
    def test_trace_id_propagation(self):
        """Trace ID 전파"""
        # 전체 파이프라인에서 동일 trace_id 사용
        pass

# tests/monitoring/test_metrics.py
class TestMetrics:
    def test_processing_time_metric(self):
        """처리 시간 메트릭"""
        pass
    
    def test_error_rate_metric(self):
        """에러율 메트릭"""
        pass
```

---

## 7. 테스트 자동화 로드맵

### Phase 1: 기초 인프라 (Week 1-2)
- [ ] pytest 설정
- [ ] 테스트 DB 환경 구축 (Docker Compose for Tests)
- [ ] Mock 서비스 구현 (Gemini API 등)
- [ ] CI/CD 파이프라인 연동

### Phase 2: Unit Tests (Week 3-4)
- [ ] 모든 서비스 단위 테스트
- [ ] 모든 에이전트 단위 테스트
- [ ] 테스트 커버리지 80% 목표

### Phase 3: Integration Tests (Week 5-6)
- [ ] E2E 파이프라인 테스트
- [ ] RabbitMQ 통합 테스트
- [ ] DB 통합 테스트

### Phase 4: 성능 & 부하 테스트 (Week 7-8)
- [ ] Locust/JMeter 설정
- [ ] 벤치마크 기준 설정
- [ ] 모니터링 대시보드

---

## 8. 테스트 실행 가이드

### 8.1 로컬 환경 테스트

```bash
# 전체 테스트 실행
pytest

# 특정 모듈 테스트
pytest tests/test_services/test_embedding_service.py

# 커버리지 포함
pytest --cov=app --cov-report=html

# 통합 테스트만
pytest tests/integration/

# 마크된 테스트만
pytest -m "slow"  # 느린 테스트
pytest -m "not slow"  # 빠른 테스트만
```

### 8.2 Docker 환경 테스트

```bash
# 테스트용 스택 시작
docker-compose -f docker-compose.test.yml up -d

# 테스트 실행
docker exec stolink-fastapi-agent pytest

# 스택 종료 및 정리
docker-compose -f docker-compose.test.yml down -v
```

### 8.3 CI/CD 파이프라인

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start services
        run: docker-compose -f docker-compose.test.yml up -d
      - name: Run tests
        run: docker exec stolink-fastapi-agent pytest --cov
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## 9. 테스트 데이터 준비

### 9.1 Fixtures

```python
# tests/fixtures/sample_texts.py

SAMPLE_SHORT_TEXT = """
아린은 검을 받아들었다. 카엘이 그녀를 바라보았다.
"""

SAMPLE_LONG_TEXT = """
[5000자 샘플 텍스트]
"""

SAMPLE_CHARACTERS = [
    {
        "name": "아린",
        "role": "protagonist",
        "traits": ["brave", "skilled"]
    }
]

# tests/conftest.py
import pytest

@pytest.fixture
def mock_db():
    """Mock database service"""
    pass

@pytest.fixture
def mock_llm():
    """Mock LLM responses"""
    pass
```

---

## 10. 결론 및 우선순위

### 즉시 구현 필요 (P0)
1. **Health Check 개선**: `/health` 엔드포인트에 DB 연결 상태 포함
2. **Unit Tests**: 핵심 서비스 (embedding, chunking, db_query)
3. **E2E Test**: 단일 문서 전체 파이프라인
4. **에러 핸들링**: 모든 예외 시나리오 대응

### 단기 목표 (P1 - 1개월)
1. **통합 테스트**: RabbitMQ Consumer, Callback
2. **Regression Tests**: 품질 기준선 설정
3. **성능 벤치마크**: 처리 시간 기준 설정

### 중기 목표 (P2 - 3개월)
1. **부하 테스트**: 동시성, 대용량
2. **보안 테스트**: Input validation
3. **모니터링**: Metrics, Logging

### 장기 목표 (P3 - 6개월)
1. **자동화된 품질 게이트**: CI/CD 완전 통합
2. **A/B Testing**: 모델 버전 비교
3. **사용자 피드백 루프**: 실제 사용 데이터 기반 개선

---

## 부록: 테스트 체크리스트

### 새 기능 추가 시 필수 사항
- [ ] Unit Test 작성
- [ ] Integration Test 업데이트
- [ ] 문서 업데이트
- [ ] 에러 핸들링 추가
- [ ] 로그 추가
- [ ] 성능 영향 평가

### PR 머지 전 체크리스트
- [ ] 모든 테스트 통과
- [ ] 커버리지 80% 이상
- [ ] 린트 검사 통과
- [ ] 문서 동기화
- [ ] 수동 테스트 완료
