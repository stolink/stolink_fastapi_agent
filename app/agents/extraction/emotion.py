"""Emotion Tracker Agent - Level 1.

Tracks character emotional states in story text.
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_basic_llm


EMOTION_TRACKING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an emotion analysis expert. Track character emotions in the text.

For each character, identify:
- character: Name
- emotion: Primary emotion
- intensity: 1-10

Return ONLY valid JSON:
{{
  "emotion_states": [
    {{"character": "...", "emotion": "...", "intensity": 5}}
  ]
}}"""),
    ("human", """Text to analyze:
{story_text}

Track emotions as JSON:""")
])


async def emotion_tracking_node(state: dict) -> dict:
    """Emotion Tracker Agent node function."""
    llm = get_basic_llm()
    
    chain = EMOTION_TRACKING_PROMPT | llm
    
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
            "tracked_emotions": result,
            "messages": state.get("messages", []) + [
                {"role": "emotion_agent", "content": "Tracked emotions"}
            ]
        }
    except Exception as e:
        return {
            "tracked_emotions": {},
            "errors": state.get("errors", []) + [f"Emotion tracking failed: {str(e)}"]
        }
