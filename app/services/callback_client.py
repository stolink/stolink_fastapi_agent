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
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
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
                    
        except httpx.TimeoutException:
            logger.error("Callback timeout", job_id=job_id, url=url)
            return False
        except httpx.RequestError as e:
            logger.error("Callback request error", job_id=job_id, error=str(e))
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
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
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
                    
        except httpx.TimeoutException:
            logger.warning("Job status update timeout", job_id=job_id)
            return False
        except httpx.RequestError as e:
            logger.warning("Job status update error", job_id=job_id, error=str(e))
            return False


# Global callback client instance
_callback_client = None


def get_callback_client() -> CallbackClient:
    """Get or create callback client singleton."""
    global _callback_client
    if _callback_client is None:
        _callback_client = CallbackClient()
    return _callback_client
