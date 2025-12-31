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

from app.agents.llm import get_structured_llm


# === Simplified Schema ===
class Relationship(BaseModel):
    """Single relationship entry - simplified for reliable extraction."""
    target: str = Field(..., description="Target character name")
    type: str = Field(..., description="FRIEND/ENEMY/FAMILY/ROMANTIC/MENTOR/RIVAL/ALLY/BETRAYER/NEUTRAL")
    strength: int = Field(5, ge=1, le=10, description="Relationship intensity 1-10")
    description: Optional[str] = Field(None, description="Brief description of relationship")
    public_stance: Optional[str] = Field(None, description="Outward: ALLY/NEUTRAL/ENEMY/RESPECT")
    private_feeling: Optional[str] = Field(None, description="Inner: TRUST/DISTRUST/LOVE/HATE/GUILT")


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
2. Use ONLY Korean names when character is "베라(Vera)" → use "베라"
3. Create SEPARATE entries for each direction (A→B and B→A)
4. ONLY extract relationships that are EXPLICITLY shown in the text

### RELATIONSHIP TYPES ###
FRIEND, ENEMY, FAMILY, ROMANTIC, MENTOR, RIVAL, ALLY, BETRAYER, NEUTRAL

### PUBLIC vs PRIVATE ###
- public_stance: What they SHOW (ALLY/NEUTRAL/ENEMY/RESPECT)
- private_feeling: What they FEEL (TRUST/DISTRUST/LOVE/HATE/GUILT)

### OUTPUT FORMAT ###
For each character, list their relationships with:
- target: Who they relate to
- type: Relationship type
- strength: 1-10
- description: Brief description
- public_stance: External behavior
- private_feeling: Internal emotion"""),
    ("human", """Story text:
{story_text}

Extract relationships for ALL characters who interact.
Keep descriptions SHORT (under 20 words).
Create BOTH directions (A→B and B→A) for each relationship.""")
])


# === Node Function ===
async def relations_extraction_node(state: dict) -> dict:
    """Relations Agent - Extracts character relationships."""
    structured_llm = get_structured_llm(CharacterRelationsResult, tier="standard")
    chain = RELATIONS_EXTRACTION_PROMPT | structured_llm
    
    try:
        result: CharacterRelationsResult = await chain.ainvoke({
            "story_text": state["content"]
        })
        
        relations_data = {}
        for char in result.characters:
            char_dump = char.model_dump()
            relations_data[char.name] = char_dump
            # Debug logging
            relation_count = len(char.relations)
            print(f"[RELATIONS] Character '{char.name}': {relation_count} relationships")
            if relation_count > 0:
                for rel in char.relations:
                    print(f"  - → {rel.target}: {rel.type} (strength={rel.strength})")
        
        print(f"[RELATIONS] Total: {len(relations_data)} characters extracted")
        
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
