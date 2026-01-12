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
    strength: int = Field(5, ge=1, le=10, description="Overall Significance (1-10)")
    
    # 5D Relationship Metrics (Orthogonal)
    emotional_bond: int = Field(5, ge=1, le=10, description="정서적 유대 (0-10): Intimacy/Affection")
    functional_trust: int = Field(5, ge=1, le=10, description="기능적 신뢰 (0-10): Competence/Reliability")
    value_alignment: int = Field(5, ge=1, le=10, description="가치관 일치 (0-10): Ideology/Morals")
    interdependence: int = Field(5, ge=1, le=10, description="상호 의존성 (0-10): Structural/Systemic Need")
    latent_tension: int = Field(1, ge=1, le=10, description="잠재적 긴장 (0-10): Conflict Probability/Subtext")

    description: Optional[str] = Field(None, description="Detailed basis for these metrics (Specific events/history)")
    public_stance: Optional[str] = Field(None, description="Outward: ALLY/NEUTRAL/ENEMY/RESPECT")
    private_feeling: Optional[str] = Field(None, description="Inner: TRUST/DISTRUST/LOVE/HATE/FEAR/GUILT/CURIOSITY/ANGER")


class CharacterRelations(BaseModel):
    """Single character's relationships."""
    name: str = Field(..., description="Character name for matching")
    relations: list[Relationship] = Field(default_factory=list, description="Relationships with other characters")
    
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
The strength score reflects HOW SIGNIFICANT the relationship is in the story (Plot Relevance).

### ⚠️ 5-DIMENSIONAL METRICS (1-10) ⚠️ ###
Measure these 5 ORTHOGONAL dimensions regardless of overall strength.

1. **Emotional Bond (정서적 유대)**: Pure emotional intimacy/affection.
   - 10: Soulmate, Parent/Child, Deepest Love.
   - 1: Total stranger or pure apathy.
   - *Example*: "My annoying brother" -> High Bond (8), even if annoying.

2. **Functional Trust (기능적 신뢰)**: Trust in ability/competence.
   - 10: "I trust him with my life/mission." (Sherlock & Watson)
   - 1: "He will fail/mess up." (Incompetent minion)
   - *Example*: Business partner -> High Trust (9), Low Bond (3).

3. **Value Alignment (가치관 일치)**: Ideology, morals, political views.
   - 10: Same crusade/belief system.
   - 1: Fundamental opposites (Hero vs Villain with opposing philosophies).
   - *Example*: Professor X & Magneto -> High Bond (8), Low Alignment (2).

4. **Interdependence (상호 의존성)**: Structural/systemic need (Gain/Loss calculation).
   - 10: Cannot survive/succeed without each other (Siamese twins, Pilot & Navigator).
   - 1: Completely independent.
   - *Example*: Forced teammates -> High Interdependence (9), Low Bond (2).

5. **Latent Tension (잠재적 긴장)**: Unspoken conflict, suspense, subtext.
   - 10: "Something will explode soon." (Traitors, hidden love, ticking bomb).
   - 1: Stable, boring, predictable.
   - *Example*: "Keep your friends close, enemies closer" -> High Tension (9).

### METRIC EXAMPLES ###
- **Sherlock & Watson**: Trust(10), Bond(8), Alignment(9), Interdep(9), Tension(2)
- **Prof X & Magneto**: Trust(9), Bond(9), Alignment(2), Interdep(5), Tension(8)
- **Toxic Couple**: Bond(9), Trust(2), Alignment(4), Interdep(8), Tension(9)

### STRENGTH EXAMPLES ###
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
      "relations": [
        {{"target": "브레베", "type": "KNOWS", "strength": 7, "emotional_bond": 4, "functional_trust": 6, "value_alignment": 3, "interdependence": 8, "latent_tension": 2, "description": "갤러선 동료 전과자, 체크무늬 멜빵 기억", "public_stance": "NEUTRAL", "private_feeling": "NEUTRAL"}},
        {{"target": "자베르", "type": "ENEMY", "strength": 9, "emotional_bond": 2, "functional_trust": 9, "value_alignment": 1, "interdependence": 5, "latent_tension": 9, "description": "자신을 알아볼 수 있는 숙적", "public_stance": "NEUTRAL", "private_feeling": "FEAR"}}
      ]
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
            "type": rel_type,
            "strength": original.get("strength", 5),
            # 5D Metrics Logic
            # Symmetric (Copy)
            "value_alignment": original.get("value_alignment", 5),
            "interdependence": original.get("interdependence", 5),
            "latent_tension": original.get("latent_tension", 1),
            # Asymmetric (Default to Neutral 5, let Agnet infer later if possible, but here we fallback)
            # Or assume SOME correlation? No, keep neutrality or copy if we assume high reciprocity.
            # Strategy: Default to 5 (Neutral) for asymmetric emotional/trust.
            "emotional_bond": 5, 
            "functional_trust": 5,
            
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
                "relations": [reverse_rel]
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
        
        # 🔍 DEBUG: Log complete relations_data structure
        print(f"[RELATIONS] 🔍 DEBUG: Complete relations_data structure:")
        for char_name, char_data in relations_data.items():
            rels_list = char_data.get("relations", [])
            print(f"[RELATIONS] 🔍   '{char_name}' -> keys={list(char_data.keys())}, relations_count={len(rels_list)}")
            if rels_list:
                for idx, rel in enumerate(rels_list[:2]):  # Show first 2 relations
                    print(f"[RELATIONS] 🔍     [{idx}] target={rel.get('target')}, type={rel.get('type')}, strength={rel.get('strength')}")
        
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
