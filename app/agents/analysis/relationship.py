"""Relationship Analyzer Agent - Level 2 (Production Level).

Role: "Social Network Analyst" - Analyzes character relationships.
Supports re-analysis with conflict feedback.

Key: Connect relationships to Character Agent names for Neo4j graph.
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_advanced_llm


RELATIONSHIP_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a "Social Network Analyst" / "Relationship Mapper".
Your job is to analyze and map relationships between characters.

=== CRITICAL: Use EXACT Character Names ===

❌ BAD: "source": "the protagonist", "the healer"
✅ GOOD: "source": "서진", "target": "하나"  // Exact names from Available Characters

=== RELATIONSHIP TYPES ===
- FRIENDLY: 우정, 동료, 협력 관계
- RIVAL: 경쟁 관계 (적대적이진 않음)
- ENEMY: 상호 적대 관계 (양쪽이 서로 적대시)
- FAMILY: 가족 관계
- ROMANTIC: 연인, 호감
- MENTOR: 스승-제자 관계 (스승 → 제자)
- BETRAYED: 한쪽이 다른쪽을 배신 (배신자 → 피해자)

=== CRITICAL: BETRAYED vs ENEMY 구분 ===

**BETRAYED** (단방향, bidirectional: false):
- 배신 행위가 명시된 경우 사용
- source = 배신자 (가해자)
- target = 피해자
- 예: "이민호가 마을을 배신" → (이민호)-[:BETRAYED]->(서진)

**ENEMY** (양방향, bidirectional: true):
- 상호 적대, 특정 가해자 없음
- 예: "두 나라가 전쟁 중" → bidirectional: true

=== DIRECTIONAL SEMANTICS (방향성 규칙) ===

**Unidirectional (단방향)** - bidirectional: false
- BETRAYED: source=배신자 → target=피해자
- MENTOR: source=스승 → target=제자

**Bidirectional (양방향)** - bidirectional: true
- FRIENDLY, RIVAL, ENEMY, FAMILY, ROMANTIC


=== YOUR TASK ===
For each character pair with a relationship:

1. **Identification**
   - source: EXACT character name (Actor/From)
   - target: EXACT character name (Recipient/To)

2. **Relationship**
   - relation_type: One of the types above
   - strength: 1-10 (relationship intensity)
   - description: Brief description

3. **Context**
   - bidirectional: Follow DIRECTIONAL SEMANTICS above!
   - evolved_from: Previous relationship type (if changed)

=== OUTPUT STRUCTURE ===
{{
  "relationships": [
    {{
      "source": "이민호",
      "target": "서진",
      "relation_type": "BETRAYED",
      "strength": 9,
      "description": "이민호가 서진과의 우정을 배신함",
      "bidirectional": false,
      "evolved_from": "FRIENDLY"
    }},
    {{
      "source": "서진",
      "target": "하나",
      "relation_type": "FRIENDLY",
      "strength": 8,
      "description": "오랜 동료이자 믿을 수 있는 친구",
      "bidirectional": true
    }}
  ]
}}

=== PENALTY WARNING ===
If you use a character name NOT in the Available Characters list,
the output will be REJECTED because it breaks database referential integrity."""),
    ("human", """Text to analyze:
{content}

=== STRICT CONSTRAINT: USE ONLY THESE NAMES ===

Available Characters (from Character Agent) - MUST use EXACT names:
{available_characters}

Character Personalities (CONTEXT):
{available_personalities}

Analyze all relationships with:
- source, target: EXACT character names
- relation_type, strength, description
- bidirectional, evolved_from (if applicable)

TIP: Use "Character Personalities" to infer relationship dynamics (e.g., A "Suspicious" character is less likely to have "FRIENDLY" relations easily).""")
])


RELATIONSHIP_RE_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a "Social Network Analyst". Previous analysis had conflicts.

=== PREVIOUS CONFLICTS ===
{conflicts}

=== CRITICAL: DIRECTIONAL SEMANTICS ===

**BETRAYED vs ENEMY - 반드시 구분!**
- BETRAYED: 한쪽이 다른쪽을 배신 (비대칭, 단방향)
  - source = 배신자, target = 피해자
  - bidirectional = false
  - 예: 이민호가 서진/마을을 배신 → (이민호)-[:BETRAYED]->(서진)

- ENEMY: 상호 적대 관계 (대칭, 양방향)
  - bidirectional = true
  - 특정 가해자 없이 서로 적대시

**배신 시나리오 처리**:
텍스트에 "A가 B를 배신" 표현이 있으면:
1. relation_type = "BETRAYED" (ENEMY 아님!)
2. source = A (배신자)
3. target = B (피해자)
4. bidirectional = false

=== OUTPUT STRUCTURE ===
{{
  "relationships": [
    {{
      "source": "이민호",
      "target": "서진",
      "relation_type": "BETRAYED",
      "strength": 9,
      "description": "이민호가 마을/서진을 배신함",
      "bidirectional": false,
      "evolved_from": "FRIENDLY",
      "conflict_resolution": "배신자=이민호, 피해자=서진으로 방향 수정"
    }}
  ]
}}"""),
    ("human", """Available Characters: {available_characters}
Character Personalities: {available_personalities}

Original text: {content}

Previous analysis (HAS ERRORS):
{previous_analysis}

=== FIX THE CONFLICTS ===
Check if direction and bidirectional values are correct!
Re-analyze and return corrected relationships:""")
])


async def relationship_analysis_node(state: dict) -> dict:
    """Relationship Analyzer Agent node function - Production Level.
    
    Role: "Social Network Analyst" - maps character relationships.
    Supports re-analysis with conflict feedback.
    
    Key principle: Use EXACT character names for Neo4j matching.
    """
    llm = get_advanced_llm()
    
    # Get available characters for reference matching
    # Support both legacy (c["name"]) and FullCharacter (c["profile"]["name"]) formats
    characters = state.get("extracted_characters", [])
    available_characters = []
    available_personalities = [] # Format: "Name: [Trait1, Trait2]"
    
    for c in characters:
        name = c.get("name") or (c.get("profile", {}) or {}).get("name")
        if name:
            available_characters.append(name)
            
            # Extract Personality
            # Check paths: c['personality']['core_traits'] or c['char_personality']['core_traits']
            pers = c.get("personality", {}) or c.get("char_personality", {})
            traits = []
            if isinstance(pers, dict):
                traits = pers.get("core_traits", [])
                if not traits and "traits" in pers:
                    traits = pers["traits"]
            
            if traits:
                clean_traits = [t if isinstance(t, str) else str(t) for t in traits]
                available_personalities.append(f"{name}: [{', '.join(clean_traits[:5])}]") # Limit to top 5
    
    pers_str = "\n".join(available_personalities) if available_personalities else "None"
    
    print(f"[RELATIONSHIP] Available characters: {available_characters}")
    
    # If no characters available, return empty result
    if not available_characters or len(available_characters) < 2:
        print("[RELATIONSHIP] Not enough characters for relationship analysis")
        return {
            "relationship_graph": {
                "relationships": [],
                "neo4j_edges": []
            },
            "messages": [
                {"role": "relationship_agent", "content": "Not enough characters for relationship analysis"}
            ]
        }
    
    conflicts = state.get("consistency_report", {}).get("conflicts", [])
    previous = state.get("relationship_graph", {})
    retry_count = state.get("retry_count", 0)
    
    is_re_analysis = retry_count > 0 and conflicts and previous.get("relationships")
    
    try:
        if is_re_analysis:
            print(f"[RELATIONSHIP] Re-analyzing with {len(conflicts)} conflicts as feedback")
            chain = RELATIONSHIP_RE_ANALYSIS_PROMPT | llm
            response = await chain.ainvoke({
                "available_characters": json.dumps(available_characters, ensure_ascii=False),
                "available_personalities": pers_str,
                "content": state.get("content", "")[:1500],
                "conflicts": json.dumps(conflicts, ensure_ascii=False, indent=2),
                "previous_analysis": json.dumps(previous, ensure_ascii=False, indent=2)
            })
        else:
            chain = RELATIONSHIP_ANALYSIS_PROMPT | llm
            response = await chain.ainvoke({
                "available_characters": json.dumps(available_characters, ensure_ascii=False),
                "available_personalities": pers_str,
                "content": state.get("content", "")[:1500]
            })
        
        content = response.content.strip()
        
        # Handle empty response
        if not content:
            print("[RELATIONSHIP] Empty response from LLM")
            return {
                "relationship_graph": {
                    "relationships": [],
                    "neo4j_edges": []
                },
                "messages": [
                    {"role": "relationship_agent", "content": "No relationships found in text"}
                ]
            }
        
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        relationships = result.get("relationships", [])
        
        # === Neo4j-Ready JSON 변환 ===
        neo4j_edges = []
        for rel in relationships:
            if rel.get("source") and rel.get("target"):
                edge = {
                    "source": rel.get("source"),
                    "target": rel.get("target"),
                    "relationship_type": rel.get("relation_type", "FRIENDLY"),
                    "attributes": {
                        "strength": rel.get("strength", 5),
                        "description": rel.get("description", ""),
                        "bidirectional": rel.get("bidirectional", True),
                        "evolved_from": rel.get("evolved_from")
                    }
                }
                neo4j_edges.append(edge)
        
        result["neo4j_edges"] = neo4j_edges
        
        return {
            "relationship_graph": result,
            "messages": [
                {"role": "relationship_agent", 
                 "content": f"{'Re-' if is_re_analysis else ''}Found {len(relationships)} relationships, {len(neo4j_edges)} edges"}
            ]
        }
    except json.JSONDecodeError as e:
        print(f"[RELATIONSHIP] JSON parse error: {e}")
        return {
            "relationship_graph": {
                "relationships": [],
                "neo4j_edges": []
            },
            "messages": [
                {"role": "relationship_agent", "content": "Failed to parse response, returning empty result"}
            ]
        }
    except Exception as e:
        error_str = str(e)
        print(f"[RELATIONSHIP] Analysis failed: {error_str}")
        
        if "ThrottlingException" in error_str:
            return {
                "relationship_graph": previous or {"relationships": []},
                "errors": [f"Relationship analysis failed: {error_str}"],
                "partial_failure": True
            }
        
        return {
            "relationship_graph": {
                "relationships": [],
                "neo4j_edges": []
            },
            "messages": [
                {"role": "relationship_agent", "content": f"Analysis failed: {error_str[:50]}"}
            ]
        }
