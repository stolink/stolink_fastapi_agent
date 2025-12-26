"""Event Extraction Agent - Level 1.

Extracts events and timeline information from story text.
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_standard_llm


# Event extraction prompt
EVENT_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a story analysis expert. Extract all events from the given text.

For each event, provide:
- event_id: Unique ID (E001, E002, etc.)
- description: Brief description
- participants: List of character names involved
- event_type: One of "action", "dialogue", "revelation", "flashback"
- importance: 1-10 scale

Return ONLY valid JSON in this exact format:
{{
  "events": [
    {{"event_id": "E001", "description": "...", "participants": ["..."], "event_type": "action", "importance": 5}}
  ]
}}"""),
    ("human", """Text to analyze:
{story_text}

Extract events as JSON:""")
])


async def event_extraction_node(state: dict) -> dict:
    """Event Extraction Agent node function."""
    llm = get_standard_llm()
    
    chain = EVENT_EXTRACTION_PROMPT | llm
    
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
        events = result.get("events", [])
        
        return {
            "extracted_events": events,
            "messages": state.get("messages", []) + [
                {"role": "event_agent", "content": f"Extracted {len(events)} events"}
            ]
        }
    except json.JSONDecodeError as e:
        return {
            "extracted_events": [],
            "errors": state.get("errors", []) + [f"Event JSON parse error: {str(e)}"]
        }
    except Exception as e:
        return {
            "extracted_events": [],
            "errors": state.get("errors", []) + [f"Event extraction failed: {str(e)}"],
            "partial_failure": True
        }
