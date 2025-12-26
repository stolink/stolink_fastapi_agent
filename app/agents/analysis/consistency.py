"""Consistency Checker Agent - Level 2.

The CORE agent that detects story conflicts.
Provides detailed feedback for re-extraction.
Includes programmatic backup checks for obvious contradictions.
"""
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_advanced_llm


# Contradictory trait pairs for backup detection
CONTRADICTORY_TRAITS = [
    ("coward", "brave"),
    ("cowardly", "brave"),
    ("coward", "courageous"),
    ("timid", "brave"),
    ("weak", "strong"),
    ("unskilled", "skilled"),
    ("incompetent", "competent"),
    ("novice", "master"),
    ("beginner", "expert"),
    ("amateur", "professional"),
    ("kind", "cruel"),
    ("gentle", "violent"),
    ("honest", "dishonest"),
    ("truthful", "liar"),
    ("loyal", "traitor"),
    ("friend", "enemy"),
]


CONSISTENCY_CHECK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a story consistency expert. Your job is to find ALL inconsistencies and contradictions.

CRITICAL: Look for these specific types of conflicts:

1. CHARACTER_TRAIT_CONFLICT: 
   - A character described as "coward" but also "brave" = CONFLICT
   - A character described as "unskilled" but also "skilled" = CONFLICT
   - Opposite traits for the same character = ALWAYS A CONFLICT

2. TIMELINE_CONFLICT: Events happen in impossible order

3. EVENT_CONTRADICTION:
   - "Never learned to use a sword" + "greatest swordsman" = CONFLICT
   - Actions that contradict stated abilities = CONFLICT

4. RELATIONSHIP_CONFLICT: Conflicting relationship states

SCORING RULES:
- Each HIGH conflict = -25 points
- Each MEDIUM conflict = -10 points
- Start at 100, minimum is 0

For contradictory character traits (opposite traits like coward/brave), ALWAYS mark as HIGH severity.

Return ONLY valid JSON:
{{
  "overall_score": 0-100,
  "conflicts": [
    {{"type": "...", "description": "...", "severity": "HIGH/MEDIUM/LOW", "affected_elements": ["..."]}}
  ],
  "warnings": ["..."]
}}"""),
    ("human", """Characters: {characters}
Events: {events}
Relationships: {relationships}

IMPORTANT: Check each character's traits list for contradictions (e.g., coward+brave, unskilled+skilled).
Check if events contradict character abilities.

Find ALL conflicts:""")
])


def detect_trait_contradictions(characters: list) -> list:
    """Programmatic backup to detect obvious trait contradictions."""
    conflicts = []
    
    for char in characters:
        name = char.get("name", "Unknown")
        traits = [t.lower() for t in char.get("traits", [])]
        
        # Check for contradictory trait pairs
        for trait1, trait2 in CONTRADICTORY_TRAITS:
            has_trait1 = any(trait1 in t for t in traits)
            has_trait2 = any(trait2 in t for t in traits)
            
            if has_trait1 and has_trait2:
                conflicts.append({
                    "type": "CHARACTER_TRAIT_CONFLICT",
                    "description": f"Character '{name}' has contradictory traits: '{trait1}' and '{trait2}' cannot both be true.",
                    "severity": "HIGH",
                    "affected_elements": [name],
                    "programmatic": True  # Mark as detected by code
                })
    
    return conflicts


async def consistency_check_node(state: dict) -> dict:
    """Consistency Checker Agent node function."""
    llm = get_advanced_llm()
    
    characters = state.get("extracted_characters", [])
    events = state.get("extracted_events", [])
    relationships = state.get("relationship_graph", {}).get("relationships", [])
    
    chain = CONSISTENCY_CHECK_PROMPT | llm
    
    try:
        response = await chain.ainvoke({
            "characters": json.dumps(characters, ensure_ascii=False, indent=2),
            "events": json.dumps(events, ensure_ascii=False, indent=2),
            "relationships": json.dumps(relationships, ensure_ascii=False, indent=2)
        })
        
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        
    except Exception as e:
        print(f"[CONSISTENCY] LLM error: {e}")
        result = {
            "overall_score": 100,
            "conflicts": [],
            "warnings": []
        }
    
    # BACKUP: Programmatic trait contradiction detection
    programmatic_conflicts = detect_trait_contradictions(characters)
    
    # Merge conflicts (avoid duplicates)
    existing_descriptions = {c.get("description", "")[:50] for c in result.get("conflicts", [])}
    for pc in programmatic_conflicts:
        if pc["description"][:50] not in existing_descriptions:
            result.setdefault("conflicts", []).append(pc)
            print(f"[CONSISTENCY] Programmatic conflict added: {pc['description'][:60]}...")
    
    # Calculate score based on all conflicts
    conflicts = result.get("conflicts", [])
    high_count = sum(1 for c in conflicts if c.get("severity") == "HIGH")
    medium_count = sum(1 for c in conflicts if c.get("severity") == "MEDIUM")
    
    # Recalculate score if we added programmatic conflicts
    if programmatic_conflicts:
        calculated_score = 100 - (high_count * 25) - (medium_count * 10)
        result["overall_score"] = max(0, calculated_score)
    
    score = result.get("overall_score", 100)
    
    # Force re-extraction if score <= 50 OR 2+ HIGH severity conflicts OR 1+ HIGH conflicts
    result["requires_reextraction"] = score <= 50 or high_count >= 1
    
    print(f"[CONSISTENCY] Score: {score}, HIGH: {high_count}, MEDIUM: {medium_count}, Reextract: {result['requires_reextraction']}")
    
    return {
        "consistency_report": result,
        "messages": [
            {"role": "consistency_agent", 
             "content": f"Score: {score}, Conflicts: {len(conflicts)} (HIGH: {high_count})"}
        ]
    }
