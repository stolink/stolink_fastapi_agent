"""Dialogue Analyzer Agent - Level 1.

Analyzes dialogue patterns in story text.
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_basic_llm


DIALOGUE_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a dialogue analysis expert. Analyze any dialogue in the text.

Provide:
- key_dialogues: Important quotes or conversations
- speech_patterns: Character speech characteristics

Return ONLY valid JSON:
{{
  "key_dialogues": ["..."],
  "speech_patterns": {{}}
}}"""),
    ("human", """Text to analyze:
{story_text}

Analyze dialogue as JSON:""")
])


async def dialogue_analysis_node(state: dict) -> dict:
    """Dialogue Analyzer Agent node function."""
    llm = get_basic_llm()
    
    chain = DIALOGUE_ANALYSIS_PROMPT | llm
    
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
            "analyzed_dialogues": result,
            "messages": state.get("messages", []) + [
                {"role": "dialogue_agent", "content": "Analyzed dialogues"}
            ]
        }
    except Exception as e:
        return {
            "analyzed_dialogues": {},
            "errors": state.get("errors", []) + [f"Dialogue analysis failed: {str(e)}"]
        }
