"""Character Stats Agent - Extracts game-related numerical information.

Responsible for:
- Stats: STR, DEX, INT, level, skills
- State: HP, MP, status effects
- Combat: Attack, defense, resistances
- Economy: Gold, trade status
- Social: Faction reputation, rank

Only extracts if the story contains numerical/game data.
For narrative-only stories, most fields will be null.
"""
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from app.agents.llm import get_structured_llm


# === Schema ===
class CharacterStats(BaseModel):
    """Game statistics with normalized naming for API output."""
    # Using Field alias for JSON serialization (str_ → strength)
    strength: Optional[int] = Field(None, ge=0, description="Strength (STR)", serialization_alias="strength")
    dexterity: Optional[int] = Field(None, ge=0, description="Dexterity (DEX)", serialization_alias="dexterity")
    intelligence: Optional[int] = Field(None, ge=0, description="Intelligence (INT)", serialization_alias="intelligence")
    constitution: Optional[int] = Field(None, ge=0, description="Constitution (CON)", serialization_alias="constitution")
    level: Optional[int] = Field(None, ge=1, description="Character level")
    exp: Optional[int] = Field(None, ge=0, description="Experience points")
    skills: list[str] = Field(default_factory=list, description="List of skills/abilities")
    
    @field_validator('skills', mode='before')
    @classmethod
    def none_to_empty_list(cls, v):
        return v if v is not None else []
    
    # Backwards compatibility aliases for old field names
    @property
    def str_(self) -> Optional[int]:
        return self.strength
    
    @property
    def int_(self) -> Optional[int]:
        return self.intelligence
    
    @property
    def dex(self) -> Optional[int]:
        return self.dexterity
    
    @property
    def con(self) -> Optional[int]:
        return self.constitution


class CharacterState(BaseModel):
    """Current state and resources (Hot Data - frequently updated)."""
    hp: Optional[int] = Field(None, ge=0, description="Current HP")
    hp_max: Optional[int] = Field(None, ge=1, description="Maximum HP")
    mp: Optional[int] = Field(None, ge=0, description="Current MP")
    mp_max: Optional[int] = Field(None, ge=1, description="Maximum MP")
    status_effects: list[str] = Field(default_factory=list, description="Active status effects")
    
    @field_validator('status_effects', mode='before')
    @classmethod
    def none_to_empty_list(cls, v):
        return v if v is not None else []


class CombatConfig(BaseModel):
    """Combat configuration with base vs total separation."""
    # Base stats (character's innate ability, before equipment)
    base_attack: Optional[int] = Field(None, ge=0, description="Base attack power (without equipment)")
    base_defense: Optional[int] = Field(None, ge=0, description="Base defense power (without equipment)")
    
    # Total stats (including equipment - what's mentioned in text)
    total_attack: Optional[int] = Field(None, ge=0, description="Total attack power (with equipment)")
    total_defense: Optional[int] = Field(None, ge=0, description="Total defense power (with equipment)")
    
    # Meta information
    source: Optional[str] = Field("extracted", description="extracted/estimated/calculated")
    
    # Other combat stats
    attack_range: Optional[float] = Field(None, ge=0, description="Attack range")
    crit_chance: Optional[float] = Field(None, ge=0, le=1, description="Critical hit chance 0-1")
    attack_type: Optional[str] = Field(None, description="MELEE/RANGED/MAGIC")


class EconomyConfig(BaseModel):
    """Economic status."""
    gold: Optional[int] = Field(None, ge=0, description="Currency amount")
    trade_status: Optional[str] = Field(None, description="Trade capability")


class SocialConfig(BaseModel):
    """Social standing."""
    rank: Optional[str] = Field(None, description="Social/military rank")
    influence: Optional[int] = Field(None, ge=0, description="Influence points")


class CharacterGameStats(BaseModel):
    """Single character's game-related stats."""
    name: str = Field(..., description="Character name for matching")
    stats: CharacterStats = Field(default_factory=CharacterStats)
    state: CharacterState = Field(default_factory=CharacterState)
    combat: CombatConfig = Field(default_factory=CombatConfig)
    economy: EconomyConfig = Field(default_factory=EconomyConfig)
    social: SocialConfig = Field(default_factory=SocialConfig)


class CharacterGameStatsResult(BaseModel):
    """Result of game stats extraction."""
    characters: list[CharacterGameStats] = Field(default_factory=list)
    has_game_data: bool = Field(False, description="Whether the text contains game-like numerical data")
    
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
                print(f"[STATS] Recovered {len(results)} characters from partial JSON")
                return results
            
            try:
                open_brackets = cleaned.count('[') - cleaned.count(']')
                open_braces = cleaned.count('{') - cleaned.count('}')
                fixed = cleaned + '}' * open_braces + ']' * open_brackets
                return json.loads(fixed)
            except json.JSONDecodeError as e:
                print(f"[STATS] JSON parse error: {e}")
                return []
        return v if v is not None else []


# === Prompt ===
STATS_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert story analyst. Extract GAME-RELATED NUMERICAL DATA if present.

### IMPORTANT ###
Not all stories have game data. Only extract if the text explicitly mentions:
- Level, HP, MP, stats (STR, DEX, etc.)
- Skills, abilities with specific names
- Gold, currency amounts
- Attack, defense, damage values
- Ranks, titles with numerical significance

### LANGUAGE CONSISTENCY RULE ###
Output ALL text in the SAME language as the input.

### CRITICAL: NAME EXTRACTION RULE ###
When a character is introduced as "베라(Vera)" or "리안(Lian)", use ONLY the Korean name.
The English in parentheses is just a transliteration hint - DO NOT use it.
❌ BAD: "name": "Vera", "name": "Lian", "name": "Tio"
✅ GOOD: "name": "베라", "name": "리안", "name": "티오"

### EXTRACTION FOCUS ###
If game data exists:

1. **stats** (Cold Data - changes on level up):
   - strength, dexterity, intelligence, constitution (NOT str_, int_, etc.)
   - level, exp, skills

2. **state** (Hot Data - changes frequently):
   - hp, hp_max, mp, mp_max
   - status_effects

3. **combat** (with base vs total separation):
   - total_attack, total_defense: What's mentioned in text (includes equipment)
   - base_attack, base_defense: Leave null unless explicitly stated
   - source: Set to "extracted" for values from text
   - attack_range, crit_chance, attack_type (MELEE/RANGED/MAGIC)

4. **economy**:
   - gold, trade_status

5. **social**:
   - rank, influence

### RULES ###
1. Set has_game_data to true ONLY if numerical game data is found
2. Leave all fields null for narrative-only stories
3. Do NOT invent numbers - only use explicit values from text
4. Use total_attack/total_defense for values from text (they likely include equipment)
5. source: "extracted" for direct text values"""),
    ("human", """Story text:
{story_text}

Extract game statistics. Use normalized field names (strength NOT str_, intelligence NOT int_).
Combat values go to total_attack/total_defense with source="extracted".""")
])


# === Node Function ===
async def stats_extraction_node(state: dict) -> dict:
    """Stats Agent - Extracts game-related numerical data."""
    # Use basic tier - formulaic stat generation
    structured_llm = get_structured_llm(CharacterGameStatsResult, tier="basic")
    chain = STATS_EXTRACTION_PROMPT | structured_llm
    
    try:
        result: CharacterGameStatsResult = await chain.ainvoke({
            "story_text": state["content"]
        })
        
        stats_data = {}
        for char in result.characters:
            stats_data[char.name] = char.model_dump()
        
        return {
            "char_stats": stats_data,
            "completed_agents": (state.get("completed_agents") or []) + ["stats"],
            "messages": [{"role": "stats_agent", "content": f"Extracted stats for {len(stats_data)} characters (game_data: {result.has_game_data})"}]
        }
    except Exception as e:
        return {
            "char_stats": {},
            "errors": (state.get("errors") or []) + [f"Stats extraction failed: {str(e)}"]
        }
