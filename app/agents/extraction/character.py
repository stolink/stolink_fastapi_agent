"""Character Extraction Agent - Level 1.

Extracts character information from story text.
Supports re-extraction with conflict feedback.
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_standard_llm


# Standard extraction prompt
CHARACTER_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a story analysis expert. Extract all characters from the given text.

For each character, provide:
- name: Character's name
- role: One of "protagonist", "antagonist", "supporting", "mentor", "sidekick", "other"
- traits: List of personality traits (max 5)
- status: Current status ("alive", "deceased", "unknown")

Return ONLY valid JSON in this exact format:
{{
  "characters": [
    {{"name": "...", "role": "...", "traits": ["..."], "status": "alive"}}
  ]
}}"""),
    ("human", """Text to analyze:
{story_text}

Extract characters as JSON:""")
])


# Re-extraction prompt with conflict feedback
CHARACTER_RE_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a story analysis expert. You previously extracted characters but some conflicts were detected.

Review the conflicts and re-extract characters with corrections.

PREVIOUS CONFLICTS DETECTED:
{conflicts}

GUIDELINES FOR CORRECTION:
- If a trait conflicts with story events, adjust the trait to be consistent
- If roles seem incorrect based on character actions, reconsider the role
- Ensure character descriptions match their actual behavior in the story

Return ONLY valid JSON in this exact format:
{{
  "characters": [
    {{"name": "...", "role": "...", "traits": ["..."], "status": "alive"}}
  ]
}}"""),
    ("human", """Original text:
{story_text}

Previous extraction:
{previous_extraction}

Re-extract characters with corrections:""")
])


async def character_extraction_node(state: dict) -> dict:
    """Character Extraction Agent node function.
    
    If conflicts exist from previous run, uses re-extraction prompt.
    """
    llm = get_standard_llm()
    
    # Check if this is a re-extraction (conflicts exist)
    conflicts = state.get("consistency_report", {}).get("conflicts", [])
    retry_count = state.get("retry_count", 0)
    previous_chars = state.get("extracted_characters", [])
    
    is_re_extraction = retry_count > 0 and conflicts and previous_chars
    
    try:
        if is_re_extraction:
            # Re-extraction with feedback
            print(f"[CHARACTER] Re-extracting with {len(conflicts)} conflicts as feedback")
            chain = CHARACTER_RE_EXTRACTION_PROMPT | llm
            response = await chain.ainvoke({
                "story_text": state["content"],
                "conflicts": json.dumps(conflicts, ensure_ascii=False, indent=2),
                "previous_extraction": json.dumps(previous_chars, ensure_ascii=False, indent=2)
            })
        else:
            # Standard extraction
            chain = CHARACTER_EXTRACTION_PROMPT | llm
            response = await chain.ainvoke({
                "story_text": state["content"]
            })
        
        # Parse JSON from response
        content = response.content.strip()
        
        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        characters = result.get("characters", [])
        
        return {
            "extracted_characters": characters,
            "messages": [
                {"role": "character_agent", 
                 "content": f"{'Re-' if is_re_extraction else ''}Extracted {len(characters)} characters"}
            ]
        }
    except json.JSONDecodeError as e:
        return {
            "extracted_characters": previous_chars or [],  # Keep previous on error
            "errors": [f"Character JSON parse error: {str(e)}"],
            "messages": [
                {"role": "character_agent", "content": f"Failed to parse response"}
            ]
        }
    except Exception as e:
        return {
            "extracted_characters": previous_chars or [],
            "errors": [f"Character extraction failed: {str(e)}"],
            "partial_failure": True
        }
