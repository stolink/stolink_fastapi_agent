"""Embedding service using Amazon Bedrock Titan.

Amazon Titan Text Embeddings V2를 사용하여 텍스트 임베딩을 생성합니다.
- 모델: amazon.titan-embed-text-v2:0
- 출력 차원: 1024 (기본값, 저장 효율성과 정확도 균형)
- Rate Limit 대응: 지수 백오프 재시도
"""
import json
import asyncio
from typing import Optional
from functools import lru_cache

import boto3
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from botocore.exceptions import ClientError, ReadTimeoutError

from app.config import settings

logger = structlog.get_logger()


class EmbeddingService:
    """Amazon Bedrock Titan 임베딩 서비스.
    
    사용 모델: amazon.titan-embed-text-v2:0
    - 입력: 최대 8,192 토큰
    - 출력: 1024차원 (256, 512, 1024 선택 가능)
    """
    
    # 모델 ID
    MODEL_ID = "amazon.titan-embed-text-v2:0"
    
    # 출력 차원 (1024 권장: 정확도와 저장 효율 균형)
    EMBEDDING_DIMENSION = 1024
    
    # 입력 토큰 제한
    MAX_INPUT_TOKENS = 8192
    
    def __init__(self):
        self._client = None
        self._initialized = False
    
    def _get_client(self):
        """Bedrock 클라이언트 반환 (lazy initialization)"""
        if self._client is None:
            self._client = boto3.client(
                'bedrock-runtime',
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
            self._initialized = True
            logger.info("Bedrock client initialized", region=settings.aws_region, model=self.MODEL_ID)
        return self._client
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ClientError, ReadTimeoutError)),
        before_sleep=lambda retry_state: logger.warning(
            "Embedding retry", attempt=retry_state.attempt_number
        )
    )
    def generate_embedding(self, text: str, dimension: int = None) -> list[float]:
        """동기 방식으로 텍스트 임베딩 생성.
        
        Args:
            text: 임베딩할 텍스트 (최대 8,192 토큰)
            dimension: 출력 차원 (256, 512, 1024 중 선택, 기본값 1024)
        
        Returns:
            임베딩 벡터 (float 리스트)
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return []
        
        # 텍스트 길이 제한 (대략적인 토큰 추정: 한글 1자 ≈ 2토큰)
        max_chars = self.MAX_INPUT_TOKENS * 2
        if len(text) > max_chars:
            text = text[:max_chars]
            logger.warning("Text truncated for embedding", original_length=len(text))
        
        dim = dimension or self.EMBEDDING_DIMENSION
        
        body = json.dumps({
            "inputText": text,
            "dimensions": dim,
            "normalize": True  # 코사인 유사도 검색에 최적화
        })
        
        try:
            client = self._get_client()
            response = client.invoke_model(
                modelId=self.MODEL_ID,
                body=body,
                contentType="application/json",
                accept="application/json"
            )
            
            result = json.loads(response['body'].read())
            embedding = result.get('embedding', [])
            
            logger.debug(
                "Embedding generated",
                text_length=len(text),
                embedding_dim=len(embedding)
            )
            
            return embedding
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(
                "Bedrock API error",
                error_code=error_code,
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise
    
    async def generate_embedding_async(self, text: str, dimension: int = None) -> list[float]:
        """비동기 방식으로 텍스트 임베딩 생성.
        
        동기 메서드를 asyncio executor에서 실행합니다.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.generate_embedding(text, dimension)
        )
    
    async def generate_embeddings_batch(
        self,
        texts: list[str],
        dimension: int = None,
        max_concurrent: int = 5
    ) -> list[list[float]]:
        """여러 텍스트에 대해 배치로 임베딩 생성.
        
        동시 요청 수를 제한하여 Rate Limit 방지.
        
        Args:
            texts: 임베딩할 텍스트 리스트
            dimension: 출력 차원
            max_concurrent: 최대 동시 요청 수
        
        Returns:
            임베딩 벡터 리스트
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_embed(text: str) -> list[float]:
            async with semaphore:
                try:
                    return await self.generate_embedding_async(text, dimension)
                except Exception as e:
                    logger.error("Batch embedding failed for text", error=str(e))
                    return []
        
        tasks = [limited_embed(text) for text in texts]
        results = await asyncio.gather(*tasks)
        
        logger.info(
            "Batch embedding completed",
            total=len(texts),
            successful=sum(1 for r in results if r)
        )
        
        return results


# ===== Singleton Instance =====

_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """임베딩 서비스 싱글톤 반환"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


# ===== 편의 함수 =====

def generate_embedding(text: str) -> list[float]:
    """텍스트 임베딩 생성 (동기)"""
    return get_embedding_service().generate_embedding(text)


async def generate_embedding_async(text: str) -> list[float]:
    """텍스트 임베딩 생성 (비동기)"""
    return await get_embedding_service().generate_embedding_async(text)


async def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """배치 임베딩 생성"""
    return await get_embedding_service().generate_embeddings_batch(texts)
