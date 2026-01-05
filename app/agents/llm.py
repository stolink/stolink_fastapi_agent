"""Google Gemini LLM configuration with Structured Output support.

Uses ChatGoogleGenerativeAI for:
- Tool Calling based structured output
- Pydantic v2 schema binding
- Guaranteed JSON format compliance
- Exponential backoff retry for throttling and network errors
"""
import asyncio
import random
from typing import Type, TypeVar
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings

T = TypeVar('T', bound=BaseModel)

# Retry configuration
MAX_RETRIES = 5
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 60.0  # seconds

# Retryable error patterns
RETRYABLE_PATTERNS = [
    "429", "Too many requests", "RESOURCE_EXHAUSTED",  # Rate limiting
    "ConnectError", "ReadError", "TimeoutError",       # Network errors
    "Server disconnected", "Connection reset",         # Connection errors
    "UNAVAILABLE", "DEADLINE_EXCEEDED",                # gRPC errors
]


async def retry_with_backoff(func, *args, **kwargs):
    """Execute function with exponential backoff retry.
    
    Handles rate limiting and network errors from Google Gemini API.
    """
    last_exception = None
    
    for attempt in range(MAX_RETRIES):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_str = str(e)
            is_retryable = any(pattern in error_str for pattern in RETRYABLE_PATTERNS)
            
            if is_retryable:
                last_exception = e
                delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
                print(f"[LLM] Retrying in {delay:.1f}s (attempt {attempt + 1}/{MAX_RETRIES}): {error_str[:80]}")
                await asyncio.sleep(delay)
            else:
                raise e
    
    raise last_exception


def get_gemini_llm(
    tier: str = "standard",
    temperature: float = 0.0,
    max_tokens: int = 4096
) -> ChatGoogleGenerativeAI:
    """Get Gemini LLM instance by tier.
    
    Args:
        tier: Model tier - "basic", "standard", or "advanced"
        temperature: Sampling temperature (0.0 = deterministic)
        max_tokens: Maximum tokens to generate
        
    Returns:
        ChatGoogleGenerativeAI instance configured for the specified tier
        
    Tiers (Cost vs Performance):
        - basic: gemini-2.0-flash-lite - Fast, cheap. Warning: Low TPM stability under load.
        - standard: gemini-2.5-flash-lite - Balanced. Warning: Low TPM stability under load.
        - advanced: gemini-2.5-flash - Best reasoning. High Stability & TPM. Recommended for extraction.
        - premium: gemini-3-flash - Latest model. Best for critical tasks.
    """
    model_configs = {
        "basic": {
            "model_id": "gemini-2.0-flash-lite",
            "default_max_tokens": 2048,  # Faster for simple tasks
        },
        "standard": {
            "model_id": "gemini-2.5-flash-lite",
            "default_max_tokens": 2048,  # Balanced
        },
        "advanced": {
            "model_id": "gemini-2.5-flash",
            "default_max_tokens": 4096,  # Full capacity for complex tasks
        },
        "premium": {
            "model_id": "gemini-3-flash-preview",
            "default_max_tokens": 4096,  # Latest model for critical tasks
        }
    }
    
    config = model_configs.get(tier, model_configs["standard"])
    print(f"[LLM] Initialized {tier} tier with model: {config['model_id']}")
    
    # Use tier-specific default if max_tokens not explicitly specified
    effective_max_tokens = max_tokens if max_tokens != 4096 else config.get("default_max_tokens", 4096)
    
    return ChatGoogleGenerativeAI(
        model=config["model_id"],
        google_api_key=settings.gemini_api_key,
        temperature=temperature,
        max_output_tokens=effective_max_tokens,
    )


def get_structured_llm(
    schema: Type[T],
    tier: str = "standard",
    temperature: float = 0.0,
    max_tokens: int = 4096
) -> ChatGoogleGenerativeAI:
    """Get LLM with structured output bound to a Pydantic schema.
    
    This uses Tool Calling to guarantee the output matches the schema.
    No manual JSON parsing required.
    
    Args:
        schema: Pydantic BaseModel class to bind
        tier: Model tier
        temperature: Sampling temperature
        max_tokens: Maximum tokens
        
    Returns:
        LLM instance that returns schema instances directly
        
    Example:
        >>> from app.schemas.settings import SettingExtractionResult
        >>> llm = get_structured_llm(SettingExtractionResult)
        >>> result = await llm.ainvoke("Extract settings from: ...")
        >>> # result is a SettingExtractionResult instance
        >>> result.settings[0].location_name
        'Dark Forest'
    """
    base_llm = get_gemini_llm(tier, temperature, max_tokens)
    return base_llm.with_structured_output(schema)


# Pre-configured model instances (lazy initialization)
BASIC_LLM = None
STANDARD_LLM = None
ADVANCED_LLM = None


def get_basic_llm() -> ChatGoogleGenerativeAI:
    """Get Basic tier LLM (Gemini 2.0 Flash Lite)."""
    global BASIC_LLM
    if BASIC_LLM is None:
        BASIC_LLM = get_gemini_llm("basic")
    return BASIC_LLM


def get_standard_llm() -> ChatGoogleGenerativeAI:
    """Get Standard tier LLM (Gemini 2.0 Flash)."""
    global STANDARD_LLM
    if STANDARD_LLM is None:
        STANDARD_LLM = get_gemini_llm("standard")
    return STANDARD_LLM


def get_advanced_llm() -> ChatGoogleGenerativeAI:
    """Get Advanced tier LLM (Gemini 2.5 Flash)."""
    global ADVANCED_LLM
    if ADVANCED_LLM is None:
        ADVANCED_LLM = get_gemini_llm("advanced")
    return ADVANCED_LLM


async def safe_ainvoke(runnable, input_data: dict):
    """Execute runnable.ainvoke with retry logic.
    
    Wrapper for chains and LLMs to handle rate limits automatically.
    """
    return await retry_with_backoff(runnable.ainvoke, input_data)

