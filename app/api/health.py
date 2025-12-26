"""Health check API endpoint."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint.
    
    Returns:
        Health status and service information
    """
    return {
        "status": "healthy",
        "service": "stolink-ai-backend",
        "version": "0.1.0"
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint.
    
    Returns:
        Readiness status
    """
    # TODO: Add checks for RabbitMQ connection, etc.
    return {
        "status": "ready"
    }
