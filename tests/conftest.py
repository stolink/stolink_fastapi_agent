"""Pytest configuration and fixtures for StoLink AI Backend tests."""
import pytest
import asyncio
from typing import AsyncGenerator
import structlog

# Configure logging for tests
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer()
    ]
)

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_redis():
    """Mock Redis client for testing."""
    from unittest.mock import MagicMock
    
    mock = MagicMock()
    mock.get.return_value = None
    mock.ping.return_value = True
    
    return mock


@pytest.fixture
async def mock_gemini_client():
    """Mock Gemini API client."""
    from unittest.mock import AsyncMock, MagicMock
    
    mock = MagicMock()
    mock_embedding = MagicMock()
    mock_embedding.values = [0.1] * 3072  # 3072 dimension
    
    mock_response = MagicMock()
    mock_response.embeddings = [mock_embedding]
    
    mock.models.embed_content = MagicMock(return_value=mock_response)
    
    return mock


@pytest.fixture
async def db_query_service():
    """DatabaseQueryService instance for testing."""
    from app.services.db_query_service import DatabaseQueryService
    
    service = DatabaseQueryService()
    # Note: Tests should mock DB connections
    yield service
    
    # Cleanup
    if service._pg_pool:
        await service.disconnect()


@pytest.fixture
def sample_character():
    """Sample character data."""
    return {
        "name": "아린",
        "role": "protagonist",
        "description": "용감한 전사",
        "profile": {
            "age": "25",
            "gender": "여성"
        },
        "aliases": [],
        "embedding": [0.1] * 3072
    }


@pytest.fixture
def sample_event():
    """Sample event data."""
    return {
        "event_id": "evt-test-001",
        "event_type": "combat",
        "description": "전투가 벌어졌다",
        "participants": ["아린"],
        "location_ref": "동굴"
    }


@pytest.fixture
def sample_sections():
    """Sample sections for content hash testing."""
    return [
        {
            "content": "아린은 검을 받아들었다. 그녀는 용감했다.",
            "title": "Section 1",
            "embedding": [0.1] * 3072
        },
        {
            "content": "카엘이 그녀를 바라보았다. 그는 마법사였다.",
            "title": "Section 2",
            "embedding": [0.2] * 3072
        },
        {
            "content": "전투가 시작되었다. 적들이 몰려왔다.",
            "title": "Section 3",
            "embedding": [0.3] * 3072
        }
    ]
