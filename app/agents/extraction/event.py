"""Event Extraction Agent - Level 1.

Extracts events and timeline information from story text.
Supports re-extraction with conflict feedback.
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_standard_llm


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


EVENT_RE_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a story analysis expert. You previously extracted events but some conflicts were detected.

Review the conflicts and re-extract events with corrections.

PREVIOUS CONFLICTS DETECTED:
{conflicts}

GUIDELINES FOR CORRECTION:
- If timeline conflicts exist, reorder events logically
- If event types seem incorrect, recategorize them
- Ensure event descriptions are accurate and not contradictory

Return ONLY valid JSON in this exact format:
{{
  "events": [
    {{"event_id": "E001", "description": "...", "participants": ["..."], "event_type": "action", "importance": 5}}
  ]
}}"""),
    ("human", """Original text:
{story_text}

Previous extraction:
{previous_extraction}

Re-extract events with corrections:""")
])


async def event_extraction_node(state: dict) -> dict:
    """Event Extraction Agent node function."""
    llm = get_standard_llm()
    
    conflicts = state.get("consistency_report", {}).get("conflicts", [])
    retry_count = state.get("retry_count", 0)
    previous_events = state.get("extracted_events", [])
    
    is_re_extraction = retry_count > 0 and conflicts and previous_events
    
    try:
        if is_re_extraction:
            print(f"[EVENT] Re-extracting with {len(conflicts)} conflicts as feedback")
            chain = EVENT_RE_EXTRACTION_PROMPT | llm
            response = await chain.ainvoke({
                "story_text": state["content"],
                "conflicts": json.dumps(conflicts, ensure_ascii=False, indent=2),
                "previous_extraction": json.dumps(previous_events, ensure_ascii=False, indent=2)
            })
        else:
            chain = EVENT_EXTRACTION_PROMPT | llm
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
            "messages": [
                {"role": "event_agent", 
                 "content": f"{'Re-' if is_re_extraction else ''}Extracted {len(events)} events"}
            ]
        }
    except json.JSONDecodeError as e:
        return {
            "extracted_events": previous_events or [],
            "errors": [f"Event JSON parse error: {str(e)}"]
        }
    except Exception as e:
        return {
            "extracted_events": previous_events or [],
            "errors": [f"Event extraction failed: {str(e)}"],
            "partial_failure": True
        }
