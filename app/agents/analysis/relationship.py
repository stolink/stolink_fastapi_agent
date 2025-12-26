"""Relationship Analyzer Agent - Level 2.

Analyzes character relationships from extracted data.
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


async def relationship_analysis_node(state: dict) -> dict:
    """Relationship Analyzer Agent node function."""
    llm = get_advanced_llm()
    
    characters = state.get("extracted_characters", [])
    
    chain = RELATIONSHIP_ANALYSIS_PROMPT | llm
    
    try:
        response = await chain.ainvoke({
            "characters": json.dumps(characters),
            "content": state.get("content", "")[:1000]  # Limit content length
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
            "messages": state.get("messages", []) + [
                {"role": "relationship_agent", "content": f"Found {len(result.get('relationships', []))} relationships"}
            ]
        }
    except Exception as e:
        return {
            "relationship_graph": {"relationships": []},
            "errors": state.get("errors", []) + [f"Relationship analysis failed: {str(e)}"]
        }
