"""StoLink AI Backend - FastAPI Application.

Multi-agent story analysis system using LangGraph and AWS Bedrock.
"""
import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.health import router as health_router
from app.api.analysis import router as analysis_router
from app.services.rabbitmq_consumer import get_consumer
from app.services.analysis_service import handle_analysis_message

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if not settings.debug else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.
    
    Starts RabbitMQ consumer on startup and disconnects on shutdown.
    """
    logger.info("Starting StoLink AI Backend")
    
    # Start RabbitMQ consumer
    consumer = get_consumer()
    consumer.set_message_handler(handle_analysis_message)
    
    # Start consuming in background task
    consumer_task = asyncio.create_task(consumer.consume_forever())
    
    logger.info("RabbitMQ consumer started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down StoLink AI Backend")
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await consumer.disconnect()


# Create FastAPI app
app = FastAPI(
    title="StoLink AI Backend",
    description="Multi-agent story analysis system using LangGraph and AWS Bedrock",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(analysis_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "StoLink AI Backend",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        reload=settings.debug,
    )
