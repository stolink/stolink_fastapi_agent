"""Character Relations Agent - Extracts relationships between characters.

Responsible for:
- Relationships with other characters
- Relationship types (FRIEND, ENEMY, FAMILY, etc.)
- Relationship history (former_ally, etc.)
- Mutual/complex feelings (복합 감정)
- Known events
- Location context

Supports ASYMMETRIC relationships:
- A betrayed B: A→B is BETRAYER, B→A is FORMER_ALLY
"""
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from app.agents.llm import get_structured_llm


# === Schema ===
class RelationshipOrigin(BaseModel):
    """Origin event that shaped this relationship."""
    event_ref: Optional[str] = Field(None, description="Reference to event ID if available")
    event_description: Optional[str] = Field(None, description="What happened to shape this relationship")
    time_context: Optional[str] = Field(None, description="When it happened (e.g., '5년 전 대전쟁')")


class Relationship(BaseModel):
    """Single relationship entry with deep psychological modeling."""
    target: str = Field(..., description="Target character name")
    
    # === Basic Relationship ===
    type: str = Field(..., description="FRIEND/ENEMY/FAMILY/ROMANTIC/MENTOR/RIVAL/ALLY/BETRAYER/FORMER_ALLY/NEUTRAL")
    strength: int = Field(5, ge=1, le=10, description="Relationship intensity 1-10")
    description: Optional[str] = Field(None, description="Brief description")
    history: Optional[str] = Field(None, description="Previous relationship (e.g., 'former_friend')")
    
    # === Public vs Private (겉과 속) ===
    public_stance: Optional[str] = Field(None, description="Outward appearance: ALLY/NEUTRAL/ENEMY/RESPECT/IGNORE")
    private_feeling: Optional[str] = Field(None, description="Inner truth: TRUST/DISTRUST/LOVE/HATE/JEALOUSY/GUILT")
    facade_level: int = Field(0, ge=0, le=10, description="0=honest, 10=completely fake facade")
    
    # === Interaction Dynamics ===
    interaction_style: Optional[str] = Field(None, description="Banters/Awkward_Silence/Toxic/Supportive/Competitive/Flirty")
    chemistry: Optional[str] = Field(None, description="What happens when they interact (e.g., '냉소적 농담', '팽팽한 긴장감')")
    
    # === Emotional Depth ===
    mutual_feelings: list[str] = Field(default_factory=list, description="Complex/mixed feelings")
    
    # === Relationship History ===
    relationship_origin: Optional[RelationshipOrigin] = Field(default_factory=RelationshipOrigin, description="What shaped this relationship")
    
    @field_validator('mutual_feelings', mode='before')
    @classmethod
    def none_to_empty_list(cls, v):
        return v if v is not None else []


class CharacterRelations(BaseModel):
    """Single character's relationships."""
    name: str = Field(..., description="Character name for matching")
    relations: list[Relationship] = Field(default_factory=list, description="Relationships with other characters")
    known_events: list[str] = Field(default_factory=list, description="Events this character knows about")
    location_context: Optional[str] = Field(None, description="Current location description")
    
    @field_validator('relations', 'known_events', mode='before')
    @classmethod
    def none_to_empty_list(cls, v):
        return v if v is not None else []


class CharacterRelationsResult(BaseModel):
    """Result of relations extraction."""
    characters: list[CharacterRelations] = Field(default_factory=list)
    
    # Validator to handle string input (LLM sometimes returns JSON string)
    @field_validator('characters', mode='before')
    @classmethod
    def parse_characters_string(cls, v):
        """Parse characters from string if LLM returns JSON string instead of list."""
        if isinstance(v, str):
            import json
            import re
            
            cleaned = re.sub(r',\s*}', '}', v)
            cleaned = re.sub(r',\s*]', ']', cleaned)
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
            
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
            
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
            
            try:
                open_brackets = cleaned.count('[') - cleaned.count(']')
                open_braces = cleaned.count('{') - cleaned.count('}')
                fixed = cleaned + '}' * open_braces + ']' * open_brackets
                return json.loads(fixed)
            except json.JSONDecodeError as e:
                print(f"[RELATIONS] JSON parse error: {e}")
                return []
        return v if v is not None else []


# === Prompt ===
RELATIONS_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert story analyst and social psychologist. Extract CHARACTER RELATIONSHIPS with deep psychological modeling.

### LANGUAGE CONSISTENCY RULE ###
Output ALL text in the SAME language as the input.

### RELATIONSHIP ASYMMETRY ###
⚠️ Create SEPARATE entries for each direction:

Example: "카엘은 왕국을 배신하고 암흑회에 가담했다"
- 카엘 → 아린: type="BETRAYER", public_stance="ENEMY", private_feeling="GUILT", facade_level=6
- 아린 → 카엘: type="FORMER_ALLY", public_stance="ENEMY", private_feeling="DISTRUST", mutual_feelings=["분노와 과거 우정의 아픔"]

### RELATIONSHIP TYPES ###
- FRIEND, ENEMY, FAMILY, ROMANTIC, MENTOR, RIVAL, ALLY, BETRAYER, FORMER_ALLY, NEUTRAL

### EXTRACTION FOCUS ###

#### Part A: Basic Relationship
1. **type**: Primary relationship classification
2. **strength**: Intensity 1-10
3. **history**: Previous relationship if changed

#### Part B: Public vs Private (겉과 속) - CRITICAL FOR STORYTELLING
4. **public_stance**: What they SHOW outwardly (ALLY/NEUTRAL/ENEMY/RESPECT/IGNORE)
5. **private_feeling**: What they TRULY feel (TRUST/DISTRUST/LOVE/HATE/JEALOUSY/GUILT/ADMIRATION)
6. **facade_level**: How much they hide true feelings (0=honest, 10=complete act)

Example inference:
- Former allies now enemies who still care → high facade_level
- "아린은 아직도 그 이유를 알지 못했다" → private_feeling might have confusion/hurt, not just anger

#### Part C: Interaction Dynamics (케미)
7. **interaction_style**: How they behave together
   - Banters: 티키타카, playful teasing
   - Awkward_Silence: 어색한 침묵
   - Toxic: 서로 깎아내림, 상처주기
   - Supportive: 서로 응원
   - Competitive: 경쟁적
   - Tense_Standoff: 팽팽한 대치

8. **chemistry**: Description of their dynamic (e.g., "냉소적 농담", "팽팽한 긴장감", "말없는 신뢰")

#### Part D: Relationship Origin (관계 기원)
9. **relationship_origin**:
   - event_description: What happened to shape this relationship
   - time_context: When it happened (e.g., "5년 전 대전쟁")

#### Part E: Emotional Depth
10. **mutual_feelings**: Complex/mixed emotions

### INFERENCE GUIDELINES - MUST INFER ###
For characters with history:
- Betrayal → likely high facade_level, private_feeling = GUILT or DISTRUST
- Former allies → interaction_style = Tense_Standoff or Awkward_Silence
- "배신자와 할 말은 없어" → public_stance = ENEMY, but private_feeling may be more complex

### RULES ###
1. Create SEPARATE entries for each direction
2. INFER public_stance and private_feeling from context
3. Include relationship_origin for significant relationships
4. facade_level > 0 when public and private don't match"""),
    ("human", """Story text:
{story_text}

Extract relationships with PSYCHOLOGICAL DEPTH for all characters.

⚠️ MUST INCLUDE:
1. public_stance vs private_feeling (겉과 속이 다를 수 있음)
2. interaction_style and chemistry
3. relationship_origin for relationships with history
4. Separate entries for each direction

This data powers realistic dialogue generation where characters can be one thing publicly and another privately.""")
])


# === Node Function ===
async def relations_extraction_node(state: dict) -> dict:
    """Relations Agent - Extracts character relationships."""
    structured_llm = get_structured_llm(CharacterRelationsResult)
    chain = RELATIONS_EXTRACTION_PROMPT | structured_llm
    
    try:
        result: CharacterRelationsResult = await chain.ainvoke({
            "story_text": state["content"]
        })
        
        relations_data = {}
        for char in result.characters:
            relations_data[char.name] = char.model_dump()
        
        return {
            "char_relations": relations_data,
            "completed_agents": (state.get("completed_agents") or []) + ["relations"],
            "messages": [{"role": "relations_agent", "content": f"Extracted {len(relations_data)} character relations"}]
        }
    except Exception as e:
        return {
            "char_relations": {},
            "errors": (state.get("errors") or []) + [f"Relations extraction failed: {str(e)}"]
        }
