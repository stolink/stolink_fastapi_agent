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
        callback_url: Optional[str] = None
    ) -> bool:
        """Send analysis result callback to Spring Boot.
        
        Args:
            job_id: Job identifier
            status: Analysis status (COMPLETED, WARNING, FAILED)
            result: Analysis results dictionary
            error: Error message if failed
            callback_url: Override callback URL (from message)
            
        Returns:
            True if callback was successful
        """
        # Use provided callback_url or fall back to settings
        if callback_url:
            # If callback_url is a full URL, use it directly
            if callback_url.startswith("http"):
                url = callback_url
            else:
                url = f"{settings.spring_callback_url}{callback_url}"
        else:
            url = f"{settings.spring_callback_url}/api/internal/ai/analysis/callback"
        
        payload = AnalysisCallbackPayload(
            job_id=job_id,
            status=status,
            result=result,
            error=error
        )
        
        logger.info("Sending callback", job_id=job_id, url=url, status=status)
        
        try:
            response = await self._send_request_with_retry(
                "POST",
                url,
                job_id,
                json=payload.model_dump(by_alias=True),
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


# Global callback client instance
_callback_client = None


def get_callback_client() -> CallbackClient:
    """Get or create callback client singleton."""
    global _callback_client
    if _callback_client is None:
        _callback_client = CallbackClient()
    return _callback_client
