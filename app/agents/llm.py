"""AWS Bedrock LLM configuration with Structured Output support.

Uses ChatBedrockConverse for:
- Tool Calling based structured output
- Pydantic v2 schema binding
- Guaranteed JSON format compliance
- Exponential backoff retry for throttling
"""
import asyncio
import random
import boto3
from typing import Type, TypeVar
from pydantic import BaseModel
from langchain_aws import ChatBedrockConverse
from app.config import settings

T = TypeVar('T', bound=BaseModel)

# Retry configuration
MAX_RETRIES = 5
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 30.0  # seconds


async def retry_with_backoff(func, *args, **kwargs):
    """Execute function with exponential backoff retry.
    
    Handles ThrottlingException from AWS Bedrock.
    """
    last_exception = None
    
    for attempt in range(MAX_RETRIES):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_str = str(e)
            if "ThrottlingException" in error_str or "Too many requests" in error_str:
                last_exception = e
                delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
                print(f"[LLM] Throttled, retrying in {delay:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
                await asyncio.sleep(delay)
            else:
                raise e
    
    raise last_exception


def get_bedrock_client():
    """Create AWS Bedrock runtime client."""
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def get_bedrock_llm(
    tier: str = "standard",
    temperature: float = 0.0,
    max_tokens: int = 4096
) -> ChatBedrockConverse:
    """Get Bedrock LLM instance by tier.
    
    Args:
        tier: Model tier - "basic", "standard", or "advanced"
        temperature: Sampling temperature (0.0 = deterministic)
        max_tokens: Maximum tokens to generate
        
    Returns:
        ChatBedrockConverse instance configured for the specified tier
        
    Tiers (Cost vs Performance):
        - basic: Claude 3 Haiku - Fast, cheap. For routing, simple classification.
        - standard: Claude 3.5 Sonnet - Balanced. For extraction, summarization.
        - advanced: Claude 3.5 Sonnet v2 - Best reasoning. For complex analysis, role inference.
    """
    model_configs = {
        "basic": {
            "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
        },
        "standard": {
            "model_id": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
        },
        "advanced": {
            "model_id": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        }
    }
    
    config = model_configs.get(tier, model_configs["standard"])
    
    return ChatBedrockConverse(
        client=get_bedrock_client(),
        model=config["model_id"],
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_structured_llm(
    schema: Type[T],
    tier: str = "standard",
    temperature: float = 0.0,
    max_tokens: int = 4096
) -> ChatBedrockConverse:
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
    base_llm = get_bedrock_llm(tier, temperature, max_tokens)
    return base_llm.with_structured_output(schema)


# Pre-configured model instances (lazy initialization)
BASIC_LLM = None
STANDARD_LLM = None
ADVANCED_LLM = None


def get_basic_llm() -> ChatBedrockConverse:
    """Get Basic tier LLM (Claude 3 Haiku)."""
    global BASIC_LLM
    if BASIC_LLM is None:
        BASIC_LLM = get_bedrock_llm("basic")
    return BASIC_LLM


def get_standard_llm() -> ChatBedrockConverse:
    """Get Standard tier LLM (Claude 3 Haiku)."""
    global STANDARD_LLM
    if STANDARD_LLM is None:
        STANDARD_LLM = get_bedrock_llm("standard")
    return STANDARD_LLM


def get_advanced_llm() -> ChatBedrockConverse:
    """Get Advanced tier LLM (Claude 3 Haiku)."""
    global ADVANCED_LLM
    if ADVANCED_LLM is None:
        ADVANCED_LLM = get_bedrock_llm("advanced")
    return ADVANCED_LLM
