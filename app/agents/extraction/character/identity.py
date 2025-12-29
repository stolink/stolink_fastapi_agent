"""Character Identity Agent - Extracts basic character information.

Responsible for:
- Profile: name, age, gender, race, faction, backstory
- Role: protagonist, antagonist, supporting, etc.
- Aliases: nicknames, titles
- Status: alive, deceased, unknown
"""
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from app.agents.llm import get_structured_llm


# === Schema ===
class CharacterIdentity(BaseModel):
    """Single character identity information."""
    name: str = Field(..., description="Character name (REQUIRED)")
    age: Optional[int] = Field(None, description="Age if mentioned")
    gender: Optional[str] = Field(None, description="male/female/unknown")
    race: Optional[str] = Field(None, description="Race/species (e.g., human, elf)")
    occupation: Optional[str] = Field(None, description="Job/class/profession (e.g., warrior, mage, knight)")
    faction: Optional[str] = Field(None, description="Organization/group affiliation")
    role: str = Field("other", description="protagonist/antagonist/supporting/mentor/sidekick/other")
    aliases: list[str] = Field(default_factory=list, description="Nicknames or titles")
    status: str = Field("alive", description="alive/deceased/unknown")
    backstory: Optional[str] = Field(None, description="Background story, past events, or current status description")
    
    # Validator to handle None -> empty list
    @field_validator('aliases', mode='before')
    @classmethod
    def none_to_empty_list(cls, v):
        """Convert None to empty list for list fields."""
        return v if v is not None else []


class CharacterIdentityResult(BaseModel):
    """Result of identity extraction."""
    characters: list[CharacterIdentity] = Field(default_factory=list)
    
    # Validator to handle string input (LLM sometimes returns JSON string)
    @field_validator('characters', mode='before')
    @classmethod
    def parse_characters_string(cls, v):
        """Parse characters from string if LLM returns JSON string instead of list."""
        if isinstance(v, str):
            import json
            import re
            
            # Clean JSON: remove trailing commas (common LLM error)
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
                print(f"[IDENTITY] Recovered {len(results)} characters from partial JSON")
                return results
            
            # Last resort: fix truncated JSON
            try:
                open_brackets = cleaned.count('[') - cleaned.count(']')
                open_braces = cleaned.count('{') - cleaned.count('}')
                fixed = cleaned + '}' * open_braces + ']' * open_brackets
                return json.loads(fixed)
            except json.JSONDecodeError as e:
                print(f"[IDENTITY] JSON parse error: {e}")
                return []
        return v if v is not None else []


# === Prompt ===
IDENTITY_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert story analyst. Extract BASIC IDENTITY information for ALL characters.

### LANGUAGE CONSISTENCY RULE ###
Output ALL text in the SAME language as the input.
If the story is in Korean, all values must be in Korean.
Do NOT translate (e.g., "암흑회" not "Dark Order").

### EXTRACTION FOCUS ###
For each character, extract:
- name: Character's name as it appears in text (REQUIRED)
- age: Exact age or estimate if mentioned
- gender: male/female/unknown
- race: Race/species if mentioned
- occupation: Job, class, or profession (e.g., "여전사", "기사", "마법사", "warrior", "knight")
  * Look for descriptive terms like "전사", "기사", "왕", "상인", etc.
  * This is IMPORTANT for character visualization (armor, weapons, attire)
- faction: Organization, group, or affiliation
- role: Main story role (protagonist/antagonist/supporting/mentor/sidekick/other)
- aliases: Any nicknames or titles
- status: alive/deceased/unknown
- backstory: Background information using FALLBACK POLICY:
  1. First: Extract specific past events if mentioned
  2. Fallback: If no past events, use current status description (e.g., "25세 여전사, 은빛 여명 기사단 소속")
  3. NEVER leave backstory as null if ANY descriptive information exists

### RULES ###
1. Extract ALL characters, even minor ones
2. Use EXACT names from the text
3. occupation and backstory should be filled whenever possible using context clues
4. Focus ONLY on identity information, not appearance or personality"""),
    ("human", """Story text:
{story_text}

Extract identity information for all characters.
IMPORTANT: Fill occupation and backstory using context clues - do not leave them null if descriptive information exists.""")
])


# === Node Function ===
async def identity_extraction_node(state: dict) -> dict:
    """Identity Agent - Extracts basic character information."""
    structured_llm = get_structured_llm(CharacterIdentityResult)
    chain = IDENTITY_EXTRACTION_PROMPT | structured_llm
    
    try:
        result: CharacterIdentityResult = await chain.ainvoke({
            "story_text": state["content"]
        })
        
        # Convert to dict keyed by character name
        identity_data = {}
        for char in result.characters:
            identity_data[char.name] = char.model_dump()
        
        return {
            "char_identity": identity_data,
            "completed_agents": (state.get("completed_agents") or []) + ["identity"],
            "messages": [{"role": "identity_agent", "content": f"Extracted {len(identity_data)} character identities"}]
        }
    except Exception as e:
        return {
            "char_identity": {},
            "errors": (state.get("errors") or []) + [f"Identity extraction failed: {str(e)}"]
        }
