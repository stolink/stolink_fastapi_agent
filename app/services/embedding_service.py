"""Embedding service using Google Gemini.

Google Gemini Text Embeddings를 사용하여 텍스트 임베딩을 생성합니다.
- 모델: gemini-embedding-001
- 출력 차원: 3072
- Rate Limit 대응: 지수 백오프 재시도
- 네트워크 오류 복구: 자동 재연결
"""
import asyncio
from typing import Optional

import structlog
import httpx
import httpcore
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from google import genai
from google.genai import types

from app.config import settings

logger = structlog.get_logger()

# 재시도 가능한 네트워크 에러 타입
RETRYABLE_ERRORS = (
    httpx.ConnectError,
    httpx.ReadError,
    httpx.TimeoutException,
    httpcore.ConnectError,
    httpcore.ReadError,
    ConnectionError,
    TimeoutError,
)


class EmbeddingService:
    """Google Gemini 임베딩 서비스.

    사용 모델: gemini-embedding-001
    - 입력: 최대 2,048 토큰
    - 출력: 3072차원
    """

    # 모델 ID
    MODEL_ID = "gemini-embedding-001"

    # 출력 차원
    EMBEDDING_DIMENSION = 3072

    # 입력 토큰 제한
    MAX_INPUT_TOKENS = 2048


    def __init__(self):
        self._client = None
        self._initialized = False
        self._redis = None
        try:
             import redis
             # redis.from_url()로 연결 (rediss:// TLS 자동 지원)
             self._redis = redis.from_url(
                 settings.redis_url,
                 decode_responses=False  # We store bytes/json
             )
             self._redis.ping()
             logger.info("Redis cache initialized for embeddings", url=settings.redis_url.split("@")[-1])  # 비밀번호 제외 로깅
        except Exception as e:
             logger.warning(f"Redis cache init failed: {e}. Caching disabled.")
             self._redis = None

    def _get_client(self, force_refresh: bool = False):
        """Gemini 클라이언트 반환 (lazy initialization)"""
        if self._client is None or force_refresh:
            if not settings.gemini_api_key:
                logger.error("GEMINI_API_KEY is not set. Embedding service will fail.")
                raise ValueError("GEMINI_API_KEY is required for Gemini embedding service.")

            self._client = genai.Client(api_key=settings.gemini_api_key)
            self._initialized = True
            logger.info("Gemini embedding client initialized", model=self.MODEL_ID, refresh=force_refresh)
        return self._client

    def _reset_client(self):
        """클라이언트 재초기화 (네트워크 오류 복구용)"""
        self._client = None
        self._initialized = False
        logger.warning("Gemini embedding client reset for reconnection")

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type(RETRYABLE_ERRORS + (Exception,)),
        before_sleep=lambda retry_state: logger.warning(
            "Embedding retry",
            attempt=retry_state.attempt_number,
            error=str(retry_state.outcome.exception()) if retry_state.outcome else "unknown"
        )
    )
    def generate_embedding(self, text: str) -> list[float]:
        """동기 방식으로 텍스트 임베딩 생성.

        Args:
            text: 임베딩할 텍스트 (최대 2,048 토큰)

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

        # Cache Check
        cache_key = f"emb:{hash(text)}"
        if self._redis:
            try:
                cached = self._redis.get(cache_key)
                if cached:
                    import json
                    logger.debug("Embedding cache hit")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")

        try:
            client = self._get_client()
            response = client.models.embed_content(
                model=self.MODEL_ID,
                contents=text,
            )

            embedding = response.embeddings[0].values

            # Cache Set
            if self._redis:
                try:
                    import json
                    self._redis.setex(
                        cache_key,
                        24*60*60, # 24 hours TTL
                        json.dumps(list(embedding))
                    )
                except Exception as e:
                    logger.warning(f"Redis set failed: {e}")

            logger.debug(
                "Embedding generated",
                text_length=len(text),
                embedding_dim=len(embedding)
            )

            return list(embedding)

        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise

    async def generate_embedding_async(self, text: str) -> list[float]:
        """비동기 방식으로 텍스트 임베딩 생성.

        동기 메서드를 asyncio executor에서 실행합니다.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.generate_embedding(text)
        )

    async def generate_embeddings_batch(
        self,
        texts: list[str],
        max_concurrent: int = 10  # Increased for better throughput
    ) -> list[list[float]]:
        """여러 텍스트에 대해 배치로 임베딩 생성.

        동시 요청 수를 제한하여 Rate Limit 방지.

        Args:
            texts: 임베딩할 텍스트 리스트
            max_concurrent: 최대 동시 요청 수

        Returns:
            임베딩 벡터 리스트
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def limited_embed(text: str) -> list[float]:
            async with semaphore:
                try:
                    return await self.generate_embedding_async(text)
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
