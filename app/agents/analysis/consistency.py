"""Consistency Checker Agent - Level 2.

The CORE agent that detects story conflicts.
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_advanced_llm


CONSISTENCY_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a story consistency expert. Check for any inconsistencies or conflicts.

Analyze:
- Character actions vs their traits
- Timeline consistency
- Logical contradictions

Return ONLY valid JSON:
{{
  "overall_score": 0-100,
  "conflicts": [
    {{"type": "...", "description": "...", "severity": "LOW/MEDIUM/HIGH"}}
  ],
  "warnings": ["..."]
}}"""),
    ("human", """Characters: {characters}
Events: {events}

Check consistency as JSON:""")
])


async def consistency_check_node(state: dict) -> dict:
    """Consistency Checker Agent node function."""
    llm = get_advanced_llm()
    
    characters = state.get("extracted_characters", [])
    events = state.get("extracted_events", [])
    
    chain = CONSISTENCY_CHECK_PROMPT | llm
    
    try:
        response = await chain.ainvoke({
            "characters": json.dumps(characters),
            "events": json.dumps(events)
        })
        
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        
        return {
            "consistency_report": result,
            "messages": state.get("messages", []) + [
                {"role": "consistency_agent", "content": f"Score: {result.get('overall_score', 'N/A')}"}
            ]
        }
    except Exception as e:
        return {
            "consistency_report": {"overall_score": 100, "conflicts": [], "warnings": []},
            "errors": state.get("errors", []) + [f"Consistency check failed: {str(e)}"]
        }
