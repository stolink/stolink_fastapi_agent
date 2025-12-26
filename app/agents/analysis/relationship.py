"""Relationship Analyzer Agent - Level 2.

Analyzes character relationships from extracted data.
Supports re-analysis with conflict feedback.
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_advanced_llm


RELATIONSHIP_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a relationship analysis expert. Analyze relationships between characters.

For each relationship:
- source: First character name
- target: Second character name  
- type: One of "FRIENDLY", "RIVAL", "FAMILY", "ROMANTIC", "MENTOR", "ENEMY"
- strength: 1-10

Return ONLY valid JSON:
{{
  "relationships": [
    {{"source": "...", "target": "...", "type": "FRIENDLY", "strength": 5}}
  ]
}}"""),
    ("human", """Characters found: {characters}

Original text: {content}

Analyze relationships as JSON:""")
])


RELATIONSHIP_RE_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a relationship analysis expert. Previous analysis had conflicts.

PREVIOUS CONFLICTS:
{conflicts}

GUIDELINES FOR CORRECTION:
- If relationship types conflict with character traits or events, reconsider
- A relationship can evolve (e.g., FRIENDLY → ENEMY) - capture the CURRENT state
- Avoid contradictory relationship types for the same pair

Return ONLY valid JSON:
{{
  "relationships": [
    {{"source": "...", "target": "...", "type": "FRIENDLY", "strength": 5, "evolved_from": "..."}}
  ]
}}"""),
    ("human", """Characters: {characters}
Events: {events}
Original text: {content}

Previous analysis:
{previous_analysis}

Re-analyze relationships:""")
])


async def relationship_analysis_node(state: dict) -> dict:
    """Relationship Analyzer Agent node function."""
    llm = get_advanced_llm()
    
    characters = state.get("extracted_characters", [])
    events = state.get("extracted_events", [])
    conflicts = state.get("consistency_report", {}).get("conflicts", [])
    previous = state.get("relationship_graph", {})
    retry_count = state.get("retry_count", 0)
    
    is_re_analysis = retry_count > 0 and conflicts and previous.get("relationships")
    
    try:
        if is_re_analysis:
            print(f"[RELATIONSHIP] Re-analyzing with {len(conflicts)} conflicts as feedback")
            chain = RELATIONSHIP_RE_ANALYSIS_PROMPT | llm
            response = await chain.ainvoke({
                "characters": json.dumps(characters, ensure_ascii=False),
                "events": json.dumps(events, ensure_ascii=False),
                "content": state.get("content", "")[:1000],
                "conflicts": json.dumps(conflicts, ensure_ascii=False, indent=2),
                "previous_analysis": json.dumps(previous, ensure_ascii=False, indent=2)
            })
        else:
            chain = RELATIONSHIP_ANALYSIS_PROMPT | llm
            response = await chain.ainvoke({
                "characters": json.dumps(characters, ensure_ascii=False),
                "content": state.get("content", "")[:1000]
            })
        
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        
        return {
            "relationship_graph": result,
            "messages": [
                {"role": "relationship_agent", 
                 "content": f"{'Re-' if is_re_analysis else ''}Found {len(result.get('relationships', []))} relationships"}
            ]
        }
    except Exception as e:
        return {
            "relationship_graph": previous or {"relationships": []},
            "errors": [f"Relationship analysis failed: {str(e)}"]
        }
