"""Plot Integrator Agent - Level 2.

Integrates events into plot structure.
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_standard_llm


PLOT_INTEGRATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a plot analysis expert. Analyze the story structure.

Provide:
- plot_summary: Brief summary
- foreshadowing: Any hints of future events
- tension_level: 1-10

Return ONLY valid JSON:
{{
  "plot_summary": "...",
  "foreshadowing": ["..."],
  "tension_level": 5
}}"""),
    ("human", """Events: {events}

Analyze plot as JSON:""")
])


async def plot_integration_node(state: dict) -> dict:
    """Plot Integrator Agent node function."""
    llm = get_standard_llm()
    
    events = state.get("extracted_events", [])
    
    chain = PLOT_INTEGRATION_PROMPT | llm
    
    try:
        response = await chain.ainvoke({
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
            "plot_integration": result,
            "messages": state.get("messages", []) + [
                {"role": "plot_agent", "content": "Analyzed plot structure"}
            ]
        }
    except Exception as e:
        return {
            "plot_integration": {},
            "errors": state.get("errors", []) + [f"Plot integration failed: {str(e)}"]
        }
