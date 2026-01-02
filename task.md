### Phase 5: 고도화 (진행 중)
- [x] **Semantic Chunking 고도화**
  - [x] `ChunkingService` 클래스 설계 (Cosine Similarity 기반)
  - [x] 장면 전환 탐지 알고리즘 구현
  - [x] `DocumentAnalysisConsumer` 연동

- [ ] **pgvector 적용**
  - [x] 로컬 Postgres Docker 이미지 교체 (`ankane/pgvector`)
  - [ ] `sections` 테이블 스키마 변경 (vector 타입)
  - [ ] 임베딩 저장 포맷 수정

- [ ] **Global Merge 심화**
  - [ ] 병합 충돌 해결 로직 구현 (Message Payload 구체화)
  - [ ] 테스트 케이스 검증
