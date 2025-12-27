"""Emotion Tracker Agent - Level 1 (Production Level).

Role: "Emotional Intelligence Analyst" - Tracks character emotional states.
Key: Connect emotions to Character Agent names, provide intensity and triggers.

Output is optimized for:
- Neo4j node properties (emotion as Character node attribute)
- Visualization (emotion intensity for character portraits)
- Narrative analysis (emotion triggers and transitions)
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_standard_llm


EMOTION_TRACKING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an "Emotional Intelligence Analyst" / "Character Psychologist".
Your job is to track the emotional states of each character in the story.

=== CRITICAL: Use EXACT Character Names ===

❌ BAD: "character": "the protagonist", "the healer"
✅ GOOD: "character": "서진", "하나"  // Exact names from Available Characters

=== YOUR TASK ===
Track emotions for each character with:

1. **Identification**
   - character: EXACT name from Available Characters list
   - emotion_id: Unique ID (EM001, EM002...)

2. **Emotional State**
   - primary_emotion: Main emotion (분노, 슬픔, 두려움, 기쁨, 혐오, 놀람, 걱정, 고통, 복수심, 그리움...)
   - secondary_emotion: Secondary emotion if any
   - intensity: 1-10 scale
   - valence: "positive", "negative", "neutral"

3. **Context**
   - trigger: What caused this emotion
   - expression: How the emotion is physically expressed (표정, 행동, 목소리 등)
   - is_hidden: true if character is hiding this emotion

=== OUTPUT STRUCTURE ===
{{
  "emotion_states": [
    {{
      "emotion_id": "EM001",
      "character": "서진",
      "primary_emotion": "분노",
      "secondary_emotion": "슬픔",
      "intensity": 8,
      "valence": "negative",
      "trigger": "이민호의 배신 사실",
      "expression": "분노로 가득 찬 눈빛",
      "is_hidden": false
    }},
    {{
      "emotion_id": "EM002",
      "character": "하나",
      "primary_emotion": "걱정",
      "secondary_emotion": "두려움",
      "intensity": 6,
      "valence": "negative",
      "trigger": "서진과 이민호의 대치",
      "expression": "걱정스러운 표정",
      "is_hidden": false
    }},
    {{
      "emotion_id": "EM003",
      "character": "이민호",
      "primary_emotion": "복수심",
      "secondary_emotion": "고통",
      "intensity": 9,
      "valence": "negative",
      "trigger": "과거 가족에게 일어난 일",
      "expression": "슬픔과 분노가 섞인 눈빛",
      "is_hidden": true
    }}
  ]
}}

=== PENALTY WARNING ===
If you use a character name NOT in the Available Characters list,
the output will be REJECTED because it breaks database referential integrity."""),
    ("human", """Text to analyze:
{story_text}

=== STRICT CONSTRAINT: USE ONLY THESE NAMES ===

Available Characters (from Character Agent) - MUST use EXACT names:
{available_characters}

Track emotions for each character with:
- primary_emotion, secondary_emotion
- intensity (1-10)
- trigger, expression""")
])


async def emotion_tracking_node(state: dict) -> dict:
    """Emotion Tracker Agent node function - Production Level.
    
    Role: "Emotional Intelligence Analyst" - tracks character emotions
    for Neo4j properties and visualization.
    
    Key principle: Use EXACT character names for graph matching.
    """
    llm = get_standard_llm()
    
    # Get available characters for reference matching
    characters = state.get("extracted_characters", [])
    available_characters = [c.get("name", "") for c in characters if c.get("name")]
    
    print(f"[EMOTION] Available characters: {available_characters}")
    
    try:
        chain = EMOTION_TRACKING_PROMPT | llm
        response = await chain.ainvoke({
            "story_text": state["content"],
            "available_characters": json.dumps(available_characters, ensure_ascii=False)
        })
        
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        emotion_states = result.get("emotion_states", [])
        
        # === Neo4j-Ready JSON 변환 (Character 노드 속성용) ===
        neo4j_updates = []
        for em in emotion_states:
            if em.get("character"):
                update = {
                    "character_name": em.get("character"),
                    "property_updates": {
                        "current_emotion": em.get("primary_emotion", "neutral"),
                        "emotion_intensity": em.get("intensity", 5),
                        "emotion_valence": em.get("valence", "neutral")
                    }
                }
                neo4j_updates.append(update)
        
        result["neo4j_updates"] = neo4j_updates
        
        return {
            "tracked_emotions": result,
            "messages": [
                {"role": "emotion_agent", 
                 "content": f"Tracked {len(emotion_states)} emotion states, {len(neo4j_updates)} updates"}
            ]
        }
    except json.JSONDecodeError as e:
        return {
            "tracked_emotions": {},
            "errors": [f"Emotion JSON parse error: {str(e)}"],
            "messages": [
                {"role": "emotion_agent", "content": "Failed to parse response"}
            ]
        }
    except Exception as e:
        return {
            "tracked_emotions": {},
            "errors": [f"Emotion tracking failed: {str(e)}"],
            "partial_failure": True
        }
