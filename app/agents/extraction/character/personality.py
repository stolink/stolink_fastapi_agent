"""Character Personality Agent - Extracts personality traits.

Responsible for:
- Core traits (persistent personality characteristics)
- Flaws (persistent weaknesses)
- Values (core beliefs)
- Decision style (for AI agent behavior control)
- Stress response (crisis behavior modeling)
- Social orientation (relationship disposition)

CRITICAL: Distinguishes between:
- PERMANENT personality traits → go here
- TEMPORARY emotional states → go to dialogue_mood.py
"""
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from app.agents.llm import get_structured_llm, safe_ainvoke

# === AI Behavioral Control Schemas ===
class DecisionStyle(BaseModel):
    """Decision-making style for AI agent behavior."""
    rationality: float = Field(0.5, ge=0.0, le=1.0, description="0.0=emotional, 1.0=rational")
    risk_tolerance: float = Field(0.5, ge=0.0, le=1.0, description="0.0=risk-averse, 1.0=risk-taker")
    biases: list[str] = Field(default_factory=list, description="Cognitive biases (e.g., Confirmation Bias, Authority Bias)")
    
    @field_validator('biases', mode='before')
    @classmethod
    def none_to_empty_list(cls, v):
        return v if v is not None else []


class StressResponse(BaseModel):
    """Behavior under stress for crisis simulation."""
    trigger: Optional[str] = Field(None, description="What triggers stress (e.g., Betrayal, Loss, Failure)")
    response_type: Optional[str] = Field(None, description="How they react (Aggressive, Withdrawal, Panic, Calm)")
    breaking_point: Optional[str] = Field(None, description="What breaks them completely")


class SocialOrientation(BaseModel):
    """Default disposition towards others."""
    trust_default: int = Field(0, ge=-5, le=5, description="Initial trust level (-5=paranoid, +5=naive)")
    empathy_level: int = Field(0, ge=-5, le=5, description="Empathy capacity (-5=cold, +5=highly empathetic)")
    authority_response: Optional[str] = Field(None, description="How they respond to authority (Obedient, Defiant, Selective)")


# === Literary/Creative Writing Schemas ===
class CharacterArc(BaseModel):
    """Character development trajectory for narrative design."""
    potential_growth: Optional[str] = Field(None, description="What positive change could this character achieve?")
    fatal_flaw: Optional[str] = Field(None, description="The tragic flaw that could lead to downfall")
    arc_direction: Optional[str] = Field(None, description="Growth/Fall/Static/Redemption/Corruption")
    internal_conflict: Optional[str] = Field(None, description="Core inner struggle (e.g., 'duty vs desire', 'trust vs self-reliance')")


class InternalMonologue(BaseModel):
    """Narrative voice style for inner thoughts."""
    thought_process: Optional[str] = Field(None, description="How they think: Intuitive-first, Evidence-based, Emotional-reactive, Analytical")
    inner_voice_tone: Optional[str] = Field(None, description="Tone of internal narration: Self-critical, Confident, Anxious, Philosophical")
    recurring_thoughts: list[str] = Field(default_factory=list, description="Obsessive themes or repeated worries")
    
    @field_validator('recurring_thoughts', mode='before')
    @classmethod
    def none_to_empty_list(cls, v):
        return v if v is not None else []


# === Main Schema ===
class CharacterPersonality(BaseModel):
    """Single character personality information with AI behavioral control and literary analysis."""
    name: str = Field(..., description="Character name for matching")
    core_traits: list[str] = Field(default_factory=list, description="Persistent personality traits")
    flaws: list[str] = Field(default_factory=list, description="Persistent character weaknesses")
    values: list[str] = Field(default_factory=list, description="Core beliefs and values")
    
    # AI Behavioral Control Fields (Production Level)
    decision_style: Optional[DecisionStyle] = Field(default_factory=DecisionStyle, description="Decision-making parameters")
    stress_response: Optional[StressResponse] = Field(default_factory=StressResponse, description="Crisis behavior modeling")
    social_orientation: Optional[SocialOrientation] = Field(default_factory=SocialOrientation, description="Relationship disposition")
    
    # Literary/Creative Writing Fields (NEW)
    character_arc: Optional[CharacterArc] = Field(default_factory=CharacterArc, description="Character development trajectory")
    internal_monologue: Optional[InternalMonologue] = Field(default_factory=InternalMonologue, description="Inner thought style")
    complex_emotions: list[str] = Field(default_factory=list, description="Mixed feelings (e.g., '동경하면서도 질투', '사랑하지만 부담')")
    
    # Validator to handle None -> empty list
    @field_validator('core_traits', 'flaws', 'values', 'complex_emotions', mode='before')
    @classmethod
    def none_to_empty_list(cls, v):
        """Convert None to empty list for list fields."""
        return v if v is not None else []


class CharacterPersonalityResult(BaseModel):
    """Result of personality extraction."""
    characters: list[CharacterPersonality] = Field(default_factory=list)
    
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
                print(f"[PERSONALITY] Recovered {len(results)} characters from partial JSON")
                return results
            
            # Last resort: fix truncated JSON
            try:
                open_brackets = cleaned.count('[') - cleaned.count(']')
                open_braces = cleaned.count('{') - cleaned.count('}')
                fixed = cleaned + '}' * open_braces + ']' * open_brackets
                return json.loads(fixed)
            except json.JSONDecodeError as e:
                print(f"[PERSONALITY] JSON parse error: {e}")
                return []
        return v if v is not None else []


# === Prompt ===
PERSONALITY_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert story analyst, AI behavior designer, and literary critic. Extract PERSONALITY TRAITS, BEHAVIORAL PARAMETERS, and NARRATIVE ELEMENTS for ALL characters.

### ⚠️ CRITICAL: EXTRACT EACH CHARACTER SEPARATELY ⚠️ ###
❗ If there are 3 characters in the story (e.g., 클레어, 잭슨, 헤이즈 교수), you MUST return 3 SEPARATE character entries.
❗ NEVER return only one character when multiple characters exist.
❗ Even if a character has minimal personality clues, include them with inferred traits based on context.

### CORRECT OUTPUT EXAMPLE (3 characters) ###
{{
  "characters": [
    {{"name": "클레어", "core_traits": ["신중함", "단호함"], "flaws": ["다혈질"], ...}},
    {{"name": "잭슨", "core_traits": ["대담함", "충동적"], "flaws": ["무모함"], ...}},
    {{"name": "헤이즈 교수", "core_traits": ["학구적", "신중함"], "flaws": [], ...}}
  ]
}}

### ❌ WRONG: DO NOT DO THIS ###
{{
  "characters": [
    {{"name": "클레어", "core_traits": ["신중함"], ...}}  ← WRONG! Other characters are missing!
  ]
}}

### LANGUAGE CONSISTENCY RULE ###
**CRITICAL**: Respond in the SAME language as the input text.
- If the input is in Korean (한글), ALL text fields (core_traits, flaws, values, biases, descriptions, etc.) MUST be in Korean.
- If the input is in English, ALL text fields MUST be in English.
- Keep technical field names (like "name", "rationality") in English, but content values should match the input language.

### CRITICAL: NAME EXTRACTION RULE ###
When a character is introduced as "베라(Vera)" or "리안(Lian)", use ONLY the Korean name.
The English in parentheses is just a transliteration hint - DO NOT use it.
❌ BAD: "name": "Vera", "name": "Lian", "name": "Tio"
✅ GOOD: "name": "베라", "name": "리안", "name": "티오"

### CRITICAL DISTINCTION ###
⚠️ PERMANENT personality traits vs TEMPORARY emotional states:

✅ core_traits (PERSISTENT): brave, cunning, loyal, compassionate, cold, calculating
✅ flaws (PERSISTENT): impulsive, arrogant, vengeful, distrustful, naive
❌ NOT personality: fearful (in a scary moment), anxious (before a battle), excited (meeting someone)

Example: "단호했지만 약간의 두려움이 섞여 있었다"
- core_traits: ["단호함"] ✅
- flaws: [] (두려움 is situational, NOT a flaw)

### EXTRACTION FOCUS ###

#### Part A: Basic Personality
1. **core_traits**: Defining characteristics that persist across scenes
2. **flaws**: Character weaknesses that affect decisions
3. **values**: Core beliefs (loyalty, justice, power, family)

#### Part B: AI Behavioral Control (for game/simulation)
4. **Decision Style**:
   - rationality: 0.0 (emotional) to 1.0 (logical)
   - risk_tolerance: 0.0 (cautious) to 1.0 (reckless)
   - biases: Cognitive biases (e.g., "권위 편향", "확증 편향")

5. **Stress Response**:
   - trigger: What causes stress (e.g., "배신", "실패")
   - response_type: Reaction type (Aggressive, Withdrawal, Panic, Calm)
   - breaking_point: What breaks them completely

6. **Social Orientation**:
   - trust_default: -5 (paranoid) to +5 (trusting)
   - empathy_level: -5 (cold) to +5 (empathetic)
   - authority_response: Obedient, Defiant, or Selective

#### Part C: Literary/Narrative Analysis (for creative writing) - ⚠️ REQUIRED
7. **Character Arc** (MUST INFER - DO NOT LEAVE NULL):
   - potential_growth: What positive change could they achieve? (REQUIRED)
   - fatal_flaw: The tragic flaw that could lead to downfall (REQUIRED)
   - arc_direction: Growth, Fall, Static, Redemption, or Corruption (REQUIRED)
   - internal_conflict: Core inner struggle (REQUIRED)

8. **Internal Monologue** (MUST INFER - DO NOT LEAVE NULL):
   - thought_process: How they think - MUST choose one: Intuitive-first, Evidence-based, Emotional-reactive, Analytical (REQUIRED)
   - inner_voice_tone: MUST choose one: Self-critical, Confident, Anxious, Philosophical (REQUIRED)
   - recurring_thoughts: At least 1 theme based on their situation

9. **Complex Emotions**:
   - Mixed feelings towards people/situations (e.g., "동경하면서도 질투", "카엘에 대한 분노와 과거 우정의 아픔")

### INFERENCE GUIDELINES - YOU MUST ALWAYS INFER ###
⚠️ CRITICAL: For character_arc and internal_monologue, you MUST infer even from minimal clues. NEVER leave these fields null.

Example inferences for "아린" (young warrior facing a betrayer):
- potential_growth: "배신으로 상처받은 마음을 치유하고 다시 신뢰하는 법을 배움"
- fatal_flaw: "지나친 자기 의존 또는 타인에 대한 불신"
- arc_direction: "Growth" (facing adversity suggests potential for growth)
- internal_conflict: "과거의 동료에 대한 신뢰 vs 배신에 대한 분노"
- thought_process: "Intuitive-first" (warrior who acts on instinct)
- inner_voice_tone: "Self-critical" (blaming herself for not seeing betrayal coming)

Example inferences for "카엘" (former knight, betrayer):
- potential_growth: "자신의 배신 이유를 직면하고 속죄의 길을 찾음"
- fatal_flaw: "극단적 이상주의 또는 환멸로 인한 냉소"
- arc_direction: "Fall" or "Redemption"
- internal_conflict: "과거의 명예 vs 현재의 선택을 정당화하려는 욕구"
- thought_process: "Analytical" (calculating betrayer)
- inner_voice_tone: "Philosophical" (justifying his actions to himself)

Text clue mappings:
- "단호했다" → higher rationality, thought_process likely "Analytical" or "Intuitive-first"
- "배신자" context → internal_conflict about trust, complex_emotions toward betrayer
- "전직 기사" → internal_conflict about past identity, potential_growth about finding new purpose
- "왕국을 배신했다" → fatal_flaw = "환멸" or "극단적 이상주의", arc_direction = "Fall" or "Corruption"

### RULES ###
1. Only extract PERSISTENT traits, not momentary emotions
2. Maximum 5 core_traits, 3 flaws, 3 values per character
3. INFER behavioral and literary parameters from context - NEVER leave null
4. For character_arc and internal_monologue - IMAGINE how a novelist would describe this character
5. ⚠️ FALLBACK: If no explicit clues, use reasonable defaults based on character role (protagonist/antagonist)"""),
    ("human", """Story text:
{story_text}

Extract personality traits, behavioral parameters, AND literary elements for all characters.

⚠️ CRITICAL REQUIREMENTS:
1. character_arc fields MUST be filled (infer from context)
2. internal_monologue fields MUST be filled (imagine their inner voice)
3. complex_emotions should capture mixed feelings about relationships

INFER from context - this is for both AI simulation AND creative writing analysis.
DO NOT return null for character_arc or internal_monologue fields.""")
])


# === Node Function ===
async def personality_extraction_node(state: dict) -> dict:
    """Personality Agent - Extracts personality traits (not emotions)."""
    # Use standard tier for personality trait extraction
    # Use standard tier for personality - basic tier causes empty arrays
    structured_llm = get_structured_llm(CharacterPersonalityResult, tier="premium")
    chain = PERSONALITY_EXTRACTION_PROMPT | structured_llm
    
    try:
        result: CharacterPersonalityResult = await safe_ainvoke(chain, {
            "story_text": state["content"]
        })
        
        personality_data = {}
        for char in result.characters:
            personality_data[char.name] = char.model_dump()
        
        return {
            "char_personality": personality_data,
            "completed_agents": (state.get("completed_agents") or []) + ["personality"],
            "messages": [{"role": "personality_agent", "content": f"Extracted {len(personality_data)} character personalities"}]
        }
    except Exception as e:
        return {
            "char_personality": {},
            "errors": (state.get("errors") or []) + [f"Personality extraction failed: {str(e)}"]
        }
