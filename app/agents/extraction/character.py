"""Character Extraction Agent - Level 1.

Extracts character information from story text.
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_standard_llm


# Character extraction prompt - simple JSON output
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


async def character_extraction_node(state: dict) -> dict:
    """Character Extraction Agent node function."""
    llm = get_standard_llm()
    
    # Build the chain
    chain = CHARACTER_EXTRACTION_PROMPT | llm
    
    try:
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
            "messages": state.get("messages", []) + [
                {"role": "character_agent", "content": f"Extracted {len(characters)} characters"}
            ]
        }
    except json.JSONDecodeError as e:
        return {
            "extracted_characters": [],
            "errors": state.get("errors", []) + [f"Character JSON parse error: {str(e)}"],
            "messages": state.get("messages", []) + [
                {"role": "character_agent", "content": f"Failed to parse: {response.content[:200]}"}
            ]
        }
    except Exception as e:
        return {
            "extracted_characters": [],
            "errors": state.get("errors", []) + [f"Character extraction failed: {str(e)}"],
            "partial_failure": True
        }
