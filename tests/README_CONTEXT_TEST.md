# 맥락 유지 시스템 테스트 가이드

## 사전 준비

### 1. DB 마이그레이션 (Phase 3, 4용)
```sql
-- PostgreSQL에서 실행
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

CREATE INDEX IF NOT EXISTS idx_summaries_project_level 
ON document_summaries(project_id, level);
```

### 2. 테스트 데이터 준비
- Neo4j에 캐릭터, 이벤트, 장소가 있는 프로젝트 필요
- 프로젝트 ID 준비

---

## 테스트 실행

### 빠른 시작
```bash
cd c:\jungle\weapon\sto-link-AI-backend
python tests/test_context_maintenance.py
```

### 단계별 테스트

#### Phase 1: 적응형 RAG
```
선택: 1
입력: 프로젝트 ID
```
**확인 사항**:
- ✅ 프로젝트 통계 조회 성공
- ✅ top_k가 분량에 따라 동적으로 계산됨 (10-40)

#### Phase 2: 엔티티 중심 검색
```
선택: 2
입력: 프로젝트 ID, 캐릭터 이름들
```
**확인 사항**:
- ✅ 캐릭터 히스토리 조회 성공
- ✅ 관계 조회 성공
- ✅ LLM 프롬프트 포맷팅 성공

#### Phase 3: 챕터 요약
```
선택: 3
입력: 프로젝트 ID, 문서 ID
```
**확인 사항**:
- ✅ 요약 생성 성공
- ✅ DB 저장 성공
- ✅ 조회 성공

#### Phase 4: 계층적 컨텍스트
```
선택: 4
입력: 프로젝트 ID, 텍스트 샘플
```
**확인 사항**:
- ✅ 통합 컨텍스트 구축 성공
- ✅ 포맷된 텍스트 생성

---

## 트러블슈팅

### "테이블이 없습니다" 에러
→ DB 마이그레이션 먼저 실행

### "Neo4j 연결 실패"
→ `.env`에서 `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` 확인

### "캐릭터를 찾을 수 없음"
→ Neo4j에 해당 프로젝트의 데이터가 있는지 확인

---

## 실전 통합 (분석 파이프라인)

테스트 성공 후, 실제 분석에 통합:

```python
# document_analysis_consumer.py 예시
from app.services.hierarchical_context import get_hierarchical_context_manager

async def _run_analysis(...):
    # 1. 계층적 컨텍스트 가져오기
    manager = await get_hierarchical_context_manager()
    context = await manager.get_context_for_analysis(
        project_id=project_id,
        current_text=content[:1000]
    )
    
    # 2. LLM 프롬프트에 컨텍스트 주입
    prompt = f"""
{context}

현재 분석할 내용:
{content}
"""
    
    # 3. 분석 실행
    result = await llm.analyze(prompt)
    
    # 4. 분석 완료 후 요약 생성
    from app.services.summary_service import get_summary_service
    summary_service = await get_summary_service()
    
    summary = await summary_service.generate_chapter_summary(
        content, extracted_entities
    )
    await summary_service.save_summary(
        document_id, project_id, summary
    )
```
