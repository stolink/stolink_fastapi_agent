"""AWS Bedrock LLM configuration and model instances."""
import boto3
from langchain_aws import ChatBedrock
from app.config import settings


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
) -> ChatBedrock:
    """Get Bedrock LLM instance by tier.
    
    Args:
        tier: Model tier - "basic", "standard", or "advanced"
        temperature: Sampling temperature (0.0 = deterministic)
        max_tokens: Maximum tokens to generate
        
    Returns:
        ChatBedrock instance configured for the specified tier
        
    Tiers:
        - basic: Amazon Nova Micro (routing, simple classification)
        - standard: Amazon Nova Lite (extraction, summarization)
        - advanced: Claude 3.5 Haiku (complex reasoning, analysis)
    """
    model_configs = {
        "basic": {
            # Claude 3 Haiku - used for all tiers until Nova models are confirmed available
            "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
            "model_kwargs": {"temperature": temperature, "max_tokens": max_tokens}
        },
        "standard": {
            "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
            "model_kwargs": {"temperature": temperature, "max_tokens": max_tokens}
        },
        "advanced": {
            "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
            "model_kwargs": {"temperature": temperature, "max_tokens": max_tokens}
        }
    }
    
    config = model_configs.get(tier, model_configs["standard"])
    
    return ChatBedrock(
        client=get_bedrock_client(),
        model_id=config["model_id"],
        model_kwargs=config["model_kwargs"],
    )


# Pre-configured model instances
# Use these in agents for consistent configuration
BASIC_LLM = None  # Lazy initialization
STANDARD_LLM = None
ADVANCED_LLM = None


def get_basic_llm() -> ChatBedrock:
    """Get Basic tier LLM (Nova Micro)."""
    global BASIC_LLM
    if BASIC_LLM is None:
        BASIC_LLM = get_bedrock_llm("basic")
    return BASIC_LLM


def get_standard_llm() -> ChatBedrock:
    """Get Standard tier LLM (Nova Lite)."""
    global STANDARD_LLM
    if STANDARD_LLM is None:
        STANDARD_LLM = get_bedrock_llm("standard")
    return STANDARD_LLM


def get_advanced_llm() -> ChatBedrock:
    """Get Advanced tier LLM (Claude 3.5 Haiku)."""
    global ADVANCED_LLM
    if ADVANCED_LLM is None:
        ADVANCED_LLM = get_bedrock_llm("advanced")
    return ADVANCED_LLM
