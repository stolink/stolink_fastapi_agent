"""Setting Extractor Agent - Level 1.

Extracts worldbuilding and setting information from story text.
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_standard_llm


SETTING_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a worldbuilding analysis expert. Extract setting information from the given text.

Provide:
- locations: List of places mentioned
- time_period: When the story takes place
- atmosphere: Overall mood/atmosphere

Return ONLY valid JSON in this exact format:
{{
  "locations": ["..."],
  "time_period": "...",
  "atmosphere": "..."
}}"""),
    ("human", """Text to analyze:
{story_text}

Extract setting as JSON:""")
])


async def setting_extraction_node(state: dict) -> dict:
    """Setting Extractor Agent node function."""
    llm = get_standard_llm()
    
    chain = SETTING_EXTRACTION_PROMPT | llm
    
    try:
        response = await chain.ainvoke({
            "story_text": state["content"]
        })
        
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        
        return {
            "extracted_settings": result,
            "messages": state.get("messages", []) + [
                {"role": "setting_agent", "content": "Extracted settings"}
            ]
        }
    except Exception as e:
        return {
            "extracted_settings": {},
            "errors": state.get("errors", []) + [f"Setting extraction failed: {str(e)}"],
            "partial_failure": True
        }
