"""Dialogue Analyzer Agent - Level 1 (Production Level).

Role: "Script Supervisor" - Analyzes dialogue patterns and relationships.
Key: Connect speakers to Character Agent names, extract speech patterns and subtext.

Output is optimized for:
- Neo4j graph edges (speaker → listener relationships)
- Character personality inference (speech patterns)
- Hidden meaning detection (subtext analysis)
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_standard_llm


DIALOGUE_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a "Script Supervisor" / "Dialogue Analyst".
Your job is to analyze dialogue patterns, speaker relationships, and hidden meanings.

=== CRITICAL: Use EXACT Character Names ===

When identifying speakers and listeners, use the EXACT names from the Available Characters list.

❌ BAD: "speaker": "the protagonist", "listener": "the antagonist"
✅ GOOD: "speaker": "서진", "listener": "이민호"

=== YOUR TASK ===
Analyze dialogues for THREE purposes:

1. **Key Dialogues** (for story highlights):
   - dialogue_id: Unique ID (D001, D002...)
   - participants: [speaker, listener] - use EXACT character names
   - content: The actual dialogue quote
   - significance: Why this dialogue is important
   - subtext: Hidden meaning if any

2. **Speech Patterns** (for character consistency):
   - character_name: EXACT name from Available Characters
   - formality_level: "formal", "informal", "mixed"
   - speech_characteristics: ["차분함", "냉소적", "공격적"...]
   - unique_phrases: Character's signature phrases

3. **Dialogue Relationships** (for Neo4j edges):
   - speaker: EXACT character name
   - listener: EXACT character name
   - formality_to_listener: "formal", "informal", "mixed"
   - power_dynamic: "superior", "equal", "subordinate"
   - intimacy_level: 1-10

=== OUTPUT STRUCTURE ===
{{
  "key_dialogues": [
    {{
      "dialogue_id": "D001",
      "participants": ["하나", "서진"],
      "content": "우리가 이곳에서 그를 만날 수 있을까?",
      "significance": "불안함과 걱정을 드러내는 첫 대사",
      "subtext": "이민호에 대한 두려움"
    }},
    {{
      "dialogue_id": "D002",
      "participants": ["이민호", "서진"],
      "content": "오랜만이군, 서진. 아직도 그 낡은 검을 들고 다니는군.",
      "significance": "과거 관계와 현재 적대감을 암시",
      "subtext": "서진을 깎아내리는 의도"
    }}
  ],
  "speech_patterns": [
    {{
      "character_name": "서진",
      "formality_level": "mixed",
      "speech_characteristics": ["직설적", "정의감"],
      "unique_phrases": []
    }},
    {{
      "character_name": "이민호",
      "formality_level": "informal",
      "speech_characteristics": ["냉소적", "비꼬는 말투", "씁쓸함"],
      "unique_phrases": ["진실은 항상 강자의 편이지"]
    }},
    {{
      "character_name": "하나",
      "formality_level": "formal",
      "speech_characteristics": ["조심스러움", "중재자", "차분함"],
      "unique_phrases": []
    }}
  ],
  "dialogue_relationships": [
    {{
      "speaker": "서진",
      "listener": "이민호",
      "formality_to_listener": "informal",
      "power_dynamic": "equal",
      "intimacy_level": 3
    }},
    {{
      "speaker": "이민호",
      "listener": "서진",
      "formality_to_listener": "informal",
      "power_dynamic": "equal",
      "intimacy_level": 2
    }},
    {{
      "speaker": "하나",
      "listener": "서진",
      "formality_to_listener": "formal",
      "power_dynamic": "subordinate",
      "intimacy_level": 7
    }}
  ]
}}"""),
    ("human", """Text to analyze:
{story_text}

=== STRICT CONSTRAINT: USE ONLY THESE NAMES ===

Available Characters (from Character Agent) - MUST use EXACT names:
{available_characters}

RULES:
1. key_dialogues.participants: ONLY use names from the list above
2. speech_patterns.character_name: ONLY use names from the list above
3. dialogue_relationships.speaker/listener: ONLY use names from the list above

PENALTY WARNING:
If you use a name NOT in the Available Characters list (e.g., "the protagonist", "Minho" instead of "이민호"),
the output will be REJECTED because it breaks database referential integrity.""")
])


async def dialogue_analysis_node(state: dict) -> dict:
    """Dialogue Analyzer Agent node function - Production Level.
    
    Role: "Script Supervisor" - analyzes dialogue patterns
    for Neo4j relationships and character personality inference.
    
    Key principle: Use EXACT character names for graph matching.
    """
    llm = get_standard_llm()
    
    # Get available characters for reference matching
    characters = state.get("extracted_characters", [])
    available_characters = [c.get("name", "") for c in characters if c.get("name")]
    
    print(f"[DIALOGUE] Available characters: {available_characters}")
    
    try:
        chain = DIALOGUE_ANALYSIS_PROMPT | llm
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
        
        # Extract counts for logging
        key_count = len(result.get("key_dialogues", []))
        pattern_count = len(result.get("speech_patterns", []))
        rel_count = len(result.get("dialogue_relationships", []))
        
        # === Neo4j-Ready JSON 변환 (Machine-Readable) ===
        neo4j_edges = []
        for rel in result.get("dialogue_relationships", []):
            if rel.get("speaker") and rel.get("listener"):  # null 체크
                edge = {
                    "source": rel.get("speaker"),
                    "target": rel.get("listener"),
                    "relationship_type": "SPEAKS_TO",
                    "attributes": {
                        "formality": rel.get("formality_to_listener", "mixed"),
                        "power": rel.get("power_dynamic", "equal"),
                        "intimacy": rel.get("intimacy_level", 5)
                    }
                }
                neo4j_edges.append(edge)
        
        # 결과에 neo4j_edges 추가
        result["neo4j_edges"] = neo4j_edges
        
        return {
            "analyzed_dialogues": result,
            "messages": [
                {"role": "dialogue_agent", 
                 "content": f"Analyzed {key_count} dialogues, {pattern_count} speech patterns, {rel_count} relationships, {len(neo4j_edges)} edges"}
            ]
        }
    except json.JSONDecodeError as e:
        return {
            "analyzed_dialogues": {},
            "errors": [f"Dialogue JSON parse error: {str(e)}"],
            "messages": [
                {"role": "dialogue_agent", "content": "Failed to parse response"}
            ]
        }
    except Exception as e:
        return {
            "analyzed_dialogues": {},
            "errors": [f"Dialogue analysis failed: {str(e)}"],
            "partial_failure": True
        }
