from typing import List
import re
import numpy as np
import structlog
from app.services.embedding_service import EmbeddingService

logger = structlog.get_logger()

class ChunkingService:
    """Semantic Chunking Service.
    
    임베딩 유사도를 기반으로 문맥이 이어지는 단락들을 병합하여 섹션을 생성합니다.
    """
    
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.similarity_threshold = 0.6  # 유사도 임계값 (이보다 높으면 병합 시도)
        self.max_tokens_per_chunk = 2000 # 대략적인 문자 수 제한 (한글 2000자 ~= 1000-1500 토큰)
        self.min_chunk_length = 500      # 너무 짧은 섹션 방지

    async def create_semantic_sections(self, content: str) -> List[dict]:
        """컨텐츠를 의미 기반 섹션으로 분할합니다."""
        
        # 1. 단락 단위 분리 (빈 줄 기준)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        
        if not paragraphs:
            return []
            
        logger.info(f"Starting semantic chunking for {len(paragraphs)} paragraphs")
        
        # 2. 모든 단락의 임베딩 배포 생성
        # (Titan V2는 비용이 좀 들지만, 챕터당 50~100개 단락이면 호출 1~2회로 가능)
        try:
            embeddings = await self.embedding_service.generate_embeddings_batch(paragraphs)
        except Exception as e:
            logger.error("Failed to generate embeddings for chunks, falling back to simple split", error=str(e))
            return self._fallback_simple_chunking(paragraphs)

        if len(embeddings) != len(paragraphs):
            logger.error("Embedding count mismatch")
            return self._fallback_simple_chunking(paragraphs)

        # 3. 유사도 기반 병합
        sections = []
        current_chunk = paragraphs[0]
        current_embedding = embeddings[0] # 현재 청크의 대표 임베딩 (또는 평균)
        
        # 누적된 텍스트
        chunk_buffer = [paragraphs[0]]
        chunk_embeddings = [embeddings[0]]
        
        for i in range(1, len(paragraphs)):
            next_para = paragraphs[i]
            next_emb = embeddings[i]
            
            # 현재 버퍼의 마지막 단락과 다음 단락의 유사도 계산
            # (Context flow는 인접 문장 간 연결성이 중요)
            sim = self._cosine_similarity(chunk_embeddings[-1], next_emb)
            
            current_len = sum(len(p) for p in chunk_buffer)
            
            # 병합 조건:
            # 1. 유사도가 높음 OR
            # 2. 현재 청크가 너무 짧음 (최소 길이 보장)
            # AND
            # 3. 최대 길이 초과하지 않음
            
            should_merge = (sim >= self.similarity_threshold or current_len < self.min_chunk_length)
            can_merge = (current_len + len(next_para)) < self.max_tokens_per_chunk
            
            if should_merge and can_merge:
                chunk_buffer.append(next_para)
                chunk_embeddings.append(next_emb)
            else:
                # 섹션 완료 (Flush)
                sections.append(self._finalize_section(chunk_buffer, chunk_embeddings))
                
                # 새로운 버퍼 시작
                chunk_buffer = [next_para]
                chunk_embeddings = [next_emb]
        
        # 마지막 버퍼 처리
        if chunk_buffer:
            sections.append(self._finalize_section(chunk_buffer, chunk_embeddings))
            
        logger.info(f"Created {len(sections)} semantic sections from {len(paragraphs)} paragraphs")
        return sections

    def _finalize_section(self, buffer: List[str], embeddings_list: List[List[float]]) -> dict:
        """버퍼 내용으로 섹션 객체 생성"""
        content = "\n\n".join(buffer)
        
        # 섹션의 대표 임베딩 생성 (모든 단락 임베딩의 평균)
        # axis=0 (수직 방향 평균)
        if embeddings_list and len(embeddings_list) > 0:
            avg_embedding = np.mean(embeddings_list, axis=0).tolist()
        else:
            avg_embedding = []
            
        # 네비게이션 제목 (첫 줄 요약)
        first_line = buffer[0].split('\n')[0]
        nav_title = first_line[:50] + "..." if len(first_line) > 50 else first_line
        
        return {
            "title": nav_title, # 임시
            "content": content,
            "embedding": avg_embedding
        }

    def _cosine_similarity(self, vec_a, vec_b) -> float:
        """코사인 유사도 계산"""
        a = np.array(vec_a)
        b = np.array(vec_b)
        
        if np.all(a == 0) or np.all(b == 0):
            return 0.0
            
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def _fallback_simple_chunking(self, paragraphs: List[str]) -> List[dict]:
        """임베딩 실패 시 단순 길이 기반 병합"""
        sections = []
        current_chunk = []
        current_len = 0
        
        for p in paragraphs:
            if current_len + len(p) > self.max_tokens_per_chunk:
                sections.append({
                    "content": "\n\n".join(current_chunk),
                    "embedding": None
                })
                current_chunk = [p]
                current_len = len(p)
            else:
                current_chunk.append(p)
                current_len += len(p)
                
        if current_chunk:
            sections.append({
                "content": "\n\n".join(current_chunk),
                "embedding": None
            })
            
        return sections
