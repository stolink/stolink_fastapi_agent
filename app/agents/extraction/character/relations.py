"""Character Relations Agent - Extracts relationships between characters.

Responsible for:
- Relationships with other characters
- Relationship types (FRIEND, ENEMY, FAMILY, etc.)
- Relationship strength and description

Simplified schema for reliable extraction.
"""
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from app.agents.llm import get_structured_llm, safe_ainvoke
from app.agents.extraction.character.identity import is_likely_item as is_non_character


# === Simplified Schema ===
class Relationship(BaseModel):
    """Single relationship entry - matches result.json schema."""
    target: str = Field(..., description="Target character name")
    type: str = Field(..., description="ALLY/ENEMY/RIVAL/NEUTRAL/FAMILY/BETRAYED")
    strength: int = Field(5, ge=1, le=10, description="Relationship intensity 1-10")
    description: Optional[str] = Field(None, description="Brief description of relationship")
    public_stance: Optional[str] = Field(None, description="Outward: ALLY/NEUTRAL/ENEMY/RESPECT")
    private_feeling: Optional[str] = Field(None, description="Inner: TRUST/DISTRUST/LOVE/HATE/FEAR/GUILT/CURIOSITY/ANGER")


class CharacterRelations(BaseModel):
    """Single character's relationships."""
    name: str = Field(..., description="Character name for matching")
    relations: list[Relationship] = Field(default_factory=list, description="Relationships with other characters")
    location_context: Optional[str] = Field(None, description="Current location description")
    
    @field_validator('relations', mode='before')
    @classmethod
    def none_to_empty_list(cls, v):
        return v if v is not None else []


class CharacterRelationsResult(BaseModel):
    """Result of relations extraction."""
    characters: list[CharacterRelations] = Field(default_factory=list)
    
    @field_validator('characters', mode='before')
    @classmethod
    def parse_characters_string(cls, v):
        """Parse characters from string if LLM returns JSON string instead of list."""
        if isinstance(v, str):
            import json
            import re
            
            # Clean JSON
            cleaned = re.sub(r',\s*}', '}', v)
            cleaned = re.sub(r',\s*]', ']', cleaned)
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
            
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
            
            # Try to extract individual character objects
            results = []
            object_pattern = r'\{\s*"name"\s*:\s*"[^"]+"\s*,.*?\}(?=\s*[,\]]|\s*$)'
            matches = re.findall(object_pattern, cleaned, re.DOTALL)
            
            for match in matches:
                try:
                    fixed = match
                    open_braces = fixed.count('{')
                    close_braces = fixed.count('}')
                    if open_braces > close_braces:
                        fixed += '}' * (open_braces - close_braces)
                    
                    obj = json.loads(fixed)
                    if isinstance(obj, dict) and 'name' in obj:
                        results.append(obj)
                except json.JSONDecodeError:
                    continue
            
            if results:
                print(f"[RELATIONS] Recovered {len(results)} characters from partial JSON")
                return results
            
            # Final attempt - fix brackets
            try:
                open_brackets = cleaned.count('[') - cleaned.count(']')
                open_braces = cleaned.count('{') - cleaned.count('}')
                fixed = cleaned + '}' * open_braces + ']' * open_brackets
                return json.loads(fixed)
            except json.JSONDecodeError as e:
                print(f"[RELATIONS] JSON parse error: {e}")
                return []
        return v if v is not None else []


# === Simplified Prompt ===
RELATIONS_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a story analyst. Extract CHARACTER RELATIONSHIPS from the text.

### ⚠️ CRITICAL: EXTRACT EACH CHARACTER SEPARATELY ⚠️ ###
❗ If there are 3 characters in the story (e.g., 클레어, 잭슨, 헤이즈 교수), you MUST return 3 SEPARATE character entries.
❗ NEVER return only one character when multiple characters exist.
❗ Even if a character has no explicit relationships, include them with an empty relations array.

### RULES ###
1. Output in the SAME language as the input
2. Use ONLY Korean names when character has format "베라(Vera)" → use "베라"
3. Create SEPARATE entries for each direction (A→B and B→A)
4. Extract relationships that are EXPLICITLY shown OR IMPLIED in the text
5. You MUST extract relationships for ALL characters listed in "Available Characters"
6. Include relationships for characters who are MENTIONED but don't directly appear (e.g., family members, past acquaintances)

### RELATIONSHIP TYPES ###
ALLY, ENEMY, RIVAL, NEUTRAL, FAMILY, BETRAYED, KNOWS, PROTECTS, MENTOR

### ⚠️ DESCRIPTION RULES (VERY IMPORTANT) ⚠️ ###
❌ NEVER write generic descriptions like "Relationship with X" or "관계"
✅ ALWAYS include SPECIFIC DETAILS from the text:
  - How they know each other (과거 인연, 공유 경험)
  - Key events or interactions between them
  - Unique identifying details mentioned in text
  - Emotional nuances of the relationship

**Examples of GOOD descriptions:**
- "갤러선 동료 전과자, 체크무늬 멜빵 기억" (specific shared history + unique detail)
- "무고한 피고인을 구하기 위해 자신의 정체를 밝힘" (specific action in story)
- "관용과 친절로 구해준 은인, 주교의 은촉대 사건" (specific event reference)
- "과거를 알아볼 수 있는 유일한 인물, 긴장 관계" (role + emotional tone)

**Examples of BAD descriptions (DO NOT USE):**
- "Relationship with 장 발장" ❌
- "관계" ❌
- "동료" (too vague) ❌

### ⚠️ STRENGTH SCORING GUIDE (1-10) ⚠️ ###
The strength score reflects HOW SIGNIFICANT the relationship is in the story:

| Score | Meaning | Examples |
|-------|---------|----------|
| 9-10 | Life-changing, central to plot | 은인, 숙적, 구원자, 생사를 함께한 관계 |
| 7-8 | Very significant, strong bond/conflict | 오랜 동료, 강한 적대, 깊은 신뢰 |
| 5-6 | Moderate importance | 일반적인 동료, 알게 된 사이, 약간의 갈등 |
| 3-4 | Minor, peripheral | 한두 번 만남, 간접적 언급 |
| 1-2 | Barely connected | 스치듯 언급, 배경 인물 |

**Strength Examples from "Les Misérables":**
- 장 발장 ↔ 주교: 10 (인생을 바꾼 은인)
- 장 발장 ↔ 자베르: 9 (숙명적 추적자)
- 장 발장 ↔ 갤러선 동료: 7 (19년 함께 수감)
- 장 발장 ↔ 재판장: 4 (법정에서 단기 상호작용)

### PUBLIC vs PRIVATE ###
- public_stance: What they SHOW (ALLY/NEUTRAL/ENEMY/RESPECT)
- private_feeling: What they FEEL (TRUST/DISTRUST/LOVE/HATE/FEAR/GUILT/CURIOSITY/ANGER)

### IMPORTANT ###
- If character A has a relationship with character B, character B MUST also have a relationship with A
- For FAMILY relationships, both directions must be extracted
- Characters who don't directly appear but are mentioned should still have relationships extracted

### OUTPUT EXAMPLE ###
{{
  "characters": [
    {{
      "name": "장 발장",
      "relations": [
        {{"target": "브레베", "type": "KNOWS", "strength": 7, "description": "갤러선 동료 전과자, 체크무늬 멜빵 기억", "public_stance": "NEUTRAL", "private_feeling": "NEUTRAL"}},
        {{"target": "자베르", "type": "ENEMY", "strength": 9, "description": "자신을 알아볼 수 있는 추적자, 긴장 관계", "public_stance": "NEUTRAL", "private_feeling": "FEAR"}},
        {{"target": "몽세뇌르 주교", "type": "ALLY", "strength": 10, "description": "관용과 친절로 구원해준 은인", "public_stance": "RESPECT", "private_feeling": "TRUST"}}
      ]
    }}
  ]
}}"""),
    ("human", """Story text:
{story_text}

Available Characters:
{character_list}

Extract relationships for ALL characters in the list.
⚠️ IMPORTANT: Write DETAILED descriptions with SPECIFIC TEXT EVIDENCE, not generic phrases.
⚠️ Set strength scores based on the SIGNIFICANCE of the relationship in the story (1-10).
Create BOTH directions (A→B and B→A) for EVERY relationship.""")
])





def ensure_bidirectional_relations(relations_data: dict) -> dict:
    """Post-process to ensure all relationships are bidirectional.
    
    If A has a relationship with B, but B doesn't have one with A,
    automatically create the reverse relationship.
    
    Note: Skips non-character entities (places, generic descriptors).
    """
    # Collect all existing relationships
    existing_rels = {}  # {(source, target): relationship_data}
    
    for char_name, char_data in relations_data.items():
        relations = char_data.get("relations", [])
        for rel in relations:
            target = rel.get("target")
            if target:
                existing_rels[(char_name, target)] = rel
    
    # Find missing reverse relationships
    missing_reverse = []
    for (source, target), rel_data in existing_rels.items():
        if (target, source) not in existing_rels:
            # Need to create reverse relationship
            missing_reverse.append({
                "source": target,
                "target": source,
                "original": rel_data
            })
    
    # Add missing reverse relationships
    for missing in missing_reverse:
        source = missing["source"]
        target = missing["target"]
        original = missing["original"]
        
        # Skip if source is a non-character (place, generic descriptor, etc.)
        if is_non_character(source):
            print(f"[RELATIONS] Skipping non-character: '{source}' (not a valid character)")
            continue
        
        # Determine reverse relationship type
        rel_type = original.get("type", "NEUTRAL")
        
        # Determine reverse private feeling
        original_feeling = original.get("private_feeling", "NEUTRAL")
        reverse_feeling_map = {
            "LOVE": "LOVE",
            "TRUST": "TRUST", 
            "HATE": "HATE",
            "ANGER": "ANGER",
            "FEAR": "FEAR",
            "GUILT": "GUILT",
            "CURIOSITY": "CURIOSITY",
            "DISTRUST": "DISTRUST"
        }
        reverse_feeling = reverse_feeling_map.get(original_feeling, original_feeling)
        
        # Create reverse relationship - preserve original description
        # The relationship context is typically symmetric (e.g., "갤러선 동료" applies both ways)
        original_desc = original.get("description", "")
        reverse_rel = {
            "target": target,
            "type": rel_type,
            "strength": original.get("strength", 5),
            "description": original_desc if original_desc else f"{source}과(와)의 관계",
            "public_stance": original.get("public_stance", "NEUTRAL"),
            "private_feeling": reverse_feeling
        }
        
        # Add to source character's relations
        if source in relations_data:
            if "relations" not in relations_data[source]:
                relations_data[source]["relations"] = []
            relations_data[source]["relations"].append(reverse_rel)
            print(f"[RELATIONS] Added reverse: {source} → {target}")
        else:
            # Source character doesn't exist in relations_data, create entry
            relations_data[source] = {
                "name": source,
                "relations": [reverse_rel],
                "location_context": None
            }
            print(f"[RELATIONS] Created new entry for {source} with reverse relation to {target}")
    
    return relations_data


# === Node Function ===
async def relations_extraction_node(state: dict) -> dict:
    """Relations Agent - Extracts character relationships."""
    # Use advanced tier (gemini-2.5-flash) for relationship extraction (User Request)
    structured_llm = get_structured_llm(CharacterRelationsResult, tier="premium")
    chain = RELATIONS_EXTRACTION_PROMPT | structured_llm
    
    # Get available characters from state (extracted by identity agent)
    identities = state.get("char_identity", {})
    character_names = list(identities.keys()) if identities else []
    char_list_str = ", ".join(character_names) if character_names else "Detect from text"
    
    print(f"[RELATIONS] Available characters: {char_list_str}")
    
    try:
        result: CharacterRelationsResult = await safe_ainvoke(chain, {
            "story_text": state["content"],
            "character_list": char_list_str
        })
        
        relations_data = {}
        filtered_count = 0
        for char in result.characters:
            # NOTE: Character names are already filtered by Identity Agent.
            # We only filter relationship TARGETS that LLM might generate incorrectly.
            
            char_dump = char.model_dump()
            
            # Also filter out non-character targets from relationships
            filtered_relations = []
            for rel in char_dump.get("relations", []):
                target = rel.get("target", "")
                # if is_non_character(target):
                #     print(f"[RELATIONS] Filtered non-character target: '{target}' from '{char.name}'")
                # else:
                filtered_relations.append(rel)
            char_dump["relations"] = filtered_relations
            
            relations_data[char.name] = char_dump
            # Debug logging
            relation_count = len(filtered_relations)
            print(f"[RELATIONS] Character '{char.name}': {relation_count} relationships")
            if relation_count > 0:
                for rel in char.relations:
                    # if not is_non_character(rel.target):
                    print(f"  - → {rel.target}: {rel.type} (strength={rel.strength})")
        
        if filtered_count > 0:
            print(f"[RELATIONS] Filtered {filtered_count} non-character entities")
        
        # Post-process to ensure bidirectional relationships
        print(f"[RELATIONS] Ensuring bidirectional relationships...")
        relations_data = ensure_bidirectional_relations(relations_data)
        
        print(f"[RELATIONS] Total: {len(relations_data)} characters extracted (after bidirectional sync)")
        
        return {
            "char_relations": relations_data,
            "completed_agents": (state.get("completed_agents") or []) + ["relations"],
            "messages": [{
                "role": "relations_agent", 
                "content": f"Extracted relations for {len(relations_data)} characters"
            }]
        }
    except Exception as e:
        print(f"[RELATIONS] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "char_relations": {},
            "errors": (state.get("errors") or []) + [f"Relations extraction failed: {str(e)}"]
        }
