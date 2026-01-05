"""HTTP Callback client for Spring Boot integration."""
import httpx
import structlog
from typing import Any, Optional

from app.config import settings
from app.schemas.callback import AnalysisCallbackPayload

logger = structlog.get_logger()


class CallbackClient:
    """HTTP client for sending analysis results to Spring Boot."""
    
    def __init__(self, timeout: float = 30.0):
        """Initialize callback client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
    
    async def _send_request_with_retry(
        self,
        method: str,
        url: str,
        job_id: str,
        **kwargs
    ) -> httpx.Response:
        """Execute request with exponential backoff retry.
        
        Retries on:
        - Connection errors
        - Timeouts
        - 5xx Server errors
        """
        import asyncio
        import random
        
        max_retries = 3
        base_delay = 1.0
        last_exception = None
        
        # Docker environment compatibility
        if "localhost" in url or "127.0.0.1" in url:
            url = url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
            logger.info("Modified request URL for Docker", new_url=url)
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method.upper() == "POST":
                        response = await client.post(url, **kwargs)
                    else:
                        response = await client.request(method, url, **kwargs)
                        
                    # Retry on server errors
                    if response.status_code >= 500:
                        response.raise_for_status()
                        
                    return response
                    
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_exception = e
                # Don't retry on 4xx errors (client error)
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code < 500:
                    raise e
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        "Callback request failed, retrying",
                        job_id=job_id,
                        attempt=attempt + 1,
                        error=str(e),
                        delay=delay
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("Callback max retries reached", job_id=job_id, error=str(e))
        
        raise last_exception if last_exception else Exception("Unknown error")

    async def send_analysis_callback(
        self,
        job_id: str,
        status: str,
        result: dict[str, Any] = None,
        error: str = None,
        callback_url: Optional[str] = None,
        processing_time_ms: int = None,  # 🆕 추가
        trace_id: str = None  # 🆕 추가
    ) -> bool:
        """Send analysis result callback to Spring Boot.
        
        Args:
            job_id: Job identifier
            status: Analysis status (COMPLETED, WARNING, FAILED)
            result: Analysis results dictionary
            error: Error message if failed
            callback_url: Override callback URL (from message)
            processing_time_ms: Total processing time in milliseconds
            trace_id: Distributed tracing ID
            
        Returns:
            True if callback was successful
        """
        # OVERRIDE: Always use the correct callback endpoint
        # RabbitMQ messages may contain legacy /api/ai-callback URLs
        # Force the new correct endpoint regardless of message content
        url = f"{settings.spring_callback_url}/api/internal/ai/analysis/callback"
        
        # Log if a different callback_url was provided (for debugging)
        if callback_url and "/api/internal/ai/analysis/callback" not in callback_url:
            logger.warning("Ignoring legacy callback_url from message", 
                          provided_url=callback_url, 
                          using_url=url)
        
        # Flattened Payload: Spring DTO deserialization 에러 방지
        # "result" 객체 내의 필드들을 최상위 레벨로 올리거나, 
        # Spring DTO 구조에 맞춰야 함.
        # 일단 Pydantic 모델 대신 딕셔너리로 직접 구성
        
        payload_dict = {
            "jobId": job_id, # "job_id" -> "jobId" (Spring Convention)
            "status": status,
            "error": error
        }
        
        # 🆕 processing_time_ms와 trace_id를 최상위 레벨에 추가
        if processing_time_ms is not None:
            payload_dict["processing_time_ms"] = processing_time_ms
        if trace_id:
            payload_dict["trace_id"] = trace_id
        
        if result:
            # result 딕셔너리의 내용을 최상위에 병합 (Flatten)
            # 만약 Spring DTO가 이를 필드로 가지고 있다면 매핑됨
            # 예: sections, characters, events 등
            payload_dict.update(result)
        
        logger.info("Sending callback", job_id=job_id, url=url, status=status)
        
        try:
            response = await self._send_request_with_retry(
                "POST",
                url,
                job_id,
                json=payload_dict,  # Flattened dict 전송
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in (200, 201, 202):
                logger.info(
                    "Callback sent successfully",
                    job_id=job_id,
                    status=status,
                    response_code=response.status_code
                )
                return True
            else:
                logger.error(
                    "Callback failed",
                    job_id=job_id,
                    status_code=response.status_code,
                    response=response.text
                )
                return False
                    
        except Exception as e:
            logger.error("Callback failed after retries", job_id=job_id, error=str(e))
            return False
    
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        message: str = None
    ) -> bool:
        """Update job status in Spring Boot.
        
        Args:
            job_id: Job identifier
            status: New status (ANALYZING, VALIDATING, FAILED, etc.)
            message: Optional status message
            
        Returns:
            True if update was successful
        """
        url = f"{settings.spring_callback_url}/api/internal/ai/jobs/{job_id}/status"
        
        payload = {"status": status}
        if message:
            payload["message"] = message
        
        logger.info("Updating job status", job_id=job_id, status=status, message=message)
        
        try:
            response = await self._send_request_with_retry(
                "POST",
                url,
                job_id,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(
                    "Job status updated",
                    job_id=job_id,
                    status=status
                )
                return True
            elif response.status_code == 404:
                # 404 means Job Not Found. This is expected if we only have a Document ID.
                # The consumer will fallback to update_document_status.
                logger.info(
                    "Job not found for status update (will try fallback)", 
                    job_id=job_id, 
                    status_code=404
                )
                return False
            else:
                logger.warning(
                    "Job status update failed",
                    job_id=job_id,
                    status_code=response.status_code,
                    response=response.text
                )
                return False
                    
        except Exception as e:
            logger.warning("Job status update failed after retries", job_id=job_id, error=str(e))
            return False

    async def update_document_status(
        self,
        document_id: str,
        status: str,
        trace_id: str = None
    ) -> bool:
        """Update document status in Spring Boot (Legacy/Fallback).
        
        Args:
            document_id: Document UUID
            status: New status
            trace_id: Optional trace ID
        """
        # Note: Document API might be under spring_backend_url or spring_callback_url.
        # Assuming they point to the same host/port.
        url = f"{settings.spring_callback_url}/api/documents/{document_id}/analysis-status"
        
        payload = {"status": status}
        if trace_id:
            payload["traceId"] = trace_id
            
        logger.info("Updating document status (fallback)", document_id=document_id, status=status)
        
        try:
            # Use PATCH for document status
            response = await self._send_request_with_retry(
                "PATCH",
                url,
                document_id,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info("Document status updated", document_id=document_id, status=status)
                return True
            else:
                logger.warning(
                    "Document status update failed", 
                    document_id=document_id, 
                    status_code=response.status_code,
                    response=response.text
                )
                return False
        except Exception as e:
            logger.warning("Document status update failed after retries", document_id=document_id, error=str(e))
            return False


# Global callback client instance
_callback_client = None


def get_callback_client() -> CallbackClient:
    """Get or create callback client singleton."""
    global _callback_client
    if _callback_client is None:
        _callback_client = CallbackClient()
    return _callback_client
