"""HTTP Callback client for Spring Boot integration."""
import httpx
import structlog
from typing import Any

from app.config import settings
from app.schemas.callback import AnalysisCallbackPayload

logger = structlog.get_logger()


class CallbackClient:
    """HTTP client for sending analysis results to Spring Boot."""
    
    def __init__(self, base_url: str = None, timeout: float = 30.0):
        """Initialize callback client.
        
        Args:
            base_url: Spring Boot server base URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or settings.spring_callback_url
        self.timeout = timeout
    
    async def send_analysis_callback(
        self,
        job_id: str,
        status: str,
        result: dict[str, Any] = None,
        error: str = None
    ) -> bool:
        """Send analysis result callback to Spring Boot.
        
        Args:
            job_id: Job identifier
            status: Analysis status (COMPLETED, WARNING, FAILED)
            result: Analysis results dictionary
            error: Error message if failed
            
        Returns:
            True if callback was successful
        """
        callback_url = f"{self.base_url}/api/internal/ai/analysis/callback"
        
        payload = AnalysisCallbackPayload(
            job_id=job_id,
            status=status,
            result=result,
            error=error
        )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    callback_url,
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
            logger.error("Callback timeout", job_id=job_id, url=callback_url)
            return False
        except httpx.RequestError as e:
            logger.error("Callback request error", job_id=job_id, error=str(e))
            return False


# Global callback client instance
_callback_client = None


def get_callback_client() -> CallbackClient:
    """Get or create callback client singleton."""
    global _callback_client
    if _callback_client is None:
        _callback_client = CallbackClient()
    return _callback_client
