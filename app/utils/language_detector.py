"""Language Detection Utility.

Detects the language of input text to determine response language.
"""

import re


def detect_language(text: str) -> str:
    """Detect language of input text.
    
    Args:
        text: Input text to analyze
        
    Returns:
        "ko" for Korean, "en" for English
    """
    if not text or len(text.strip()) == 0:
        return "en"
    
    # Count Korean characters (Hangul syllables: 0xAC00-0xD7AF)
    korean_chars = len(re.findall(r'[가-힣]', text))
    
    # Count English alphabet characters
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    
    # Count total meaningful characters (excluding whitespace and punctuation)
    total_chars = korean_chars + english_chars
    
    if total_chars == 0:
        return "en"
    
    # If Korean characters make up more than 30% of total, consider it Korean
    korean_ratio = korean_chars / total_chars
    
    return "ko" if korean_ratio > 0.3 else "en"


def get_language_specific_instruction() -> dict[str, str]:
    """Get language-specific instructions for prompts.
    
    Returns:
        Dictionary with language codes as keys and instructions as values
    """
    return {
        "ko": """
=== LANGUAGE INSTRUCTION ===
The input text is in KOREAN. You MUST respond in KOREAN for all text fields including:
- names (이름)
- descriptions (설명)
- summaries (요약)
- narratives (서술)
- conflict descriptions (충돌 설명)
- warnings (경고)
- any other natural language output

Keep technical field names (like event_id, character_id) in English, but all content should be in Korean.
""",
        "en": ""
    }
