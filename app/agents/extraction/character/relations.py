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

### RULES ###
1. Output in the SAME language as the input
2. Use ONLY Korean names when character has format "베라(Vera)" → use "베라"
3. Create SEPARATE entries for each direction (A→B and B→A)
4. Extract relationships that are EXPLICITLY shown OR IMPLIED in the text
5. You MUST extract relationships for ALL characters listed in "Available Characters"
6. Include relationships for characters who are MENTIONED but don't directly appear (e.g., family members, past acquaintances)

### RELATIONSHIP TYPES ###
ALLY, ENEMY, RIVAL, NEUTRAL, FAMILY, BETRAYED

### GUIDANCE ###
- BETRAYED: Use only if a betrayal has occurred or is effectively broken. If merely suspicious, use NEUTRAL or ENEMY with 'DISTRUST' private feeling.
- Do not invent relationship types not listed above.
- Ensure 'The man' and 'Monseigneur Bienvenu' relationship reflects the hospitality offered (ALLY) unless hostile action is taken.

### PUBLIC vs PRIVATE ###
- public_stance: What they SHOW (ALLY/NEUTRAL/ENEMY/RESPECT)
- private_feeling: What they FEEL (TRUST/DISTRUST/LOVE/HATE/FEAR/GUILT/CURIOSITY/ANGER)

### IMPORTANT ###
- If character A has a relationship with character B, character B MUST also have a relationship with A
- For FAMILY relationships, both directions must be extracted (e.g., if A is B's sibling, B is also A's sibling)
- Characters who don't directly appear but are mentioned (sick relative, distant friend, etc.) should still have relationships extracted

### OUTPUT EXAMPLE ###
{{
  "characters": [
    {{
      "name": "진하",
      "relations": [
        {{"target": "세라", "type": "ALLY", "strength": 7, "description": "의뢰인을 보호하려 함", "public_stance": "ALLY", "private_feeling": "CURIOSITY"}},
        {{"target": "유민재", "type": "ENEMY", "strength": 8, "description": "적대적 대립", "public_stance": "ENEMY", "private_feeling": "ANGER"}}
      ]
    }},
    {{
      "name": "세라",
      "relations": [
        {{"target": "진하", "type": "ALLY", "strength": 7, "description": "자신을 도와주는 탐정", "public_stance": "ALLY", "private_feeling": "TRUST"}}
      ]
    }}
  ]
}}"""),
    ("human", """Story text:
{story_text}

Available Characters:
{character_list}

Extract relationships for ALL characters in the list.
Include relationships for characters who are MENTIONED but don't directly appear in scenes.
Keep descriptions SHORT (under 20 words).
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
        
        # Create reverse relationship
        reverse_rel = {
            "target": target,
            "type": rel_type,
            "strength": original.get("strength", 5),
            "description": f"Relationship with {target}",
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
                if is_non_character(target):
                    print(f"[RELATIONS] Filtered non-character target: '{target}' from '{char.name}'")
                else:
                    filtered_relations.append(rel)
            char_dump["relations"] = filtered_relations
            
            relations_data[char.name] = char_dump
            # Debug logging
            relation_count = len(filtered_relations)
            print(f"[RELATIONS] Character '{char.name}': {relation_count} relationships")
            if relation_count > 0:
                for rel in char.relations:
                    if not is_non_character(rel.target):
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
