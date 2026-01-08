"""Character Dialogue & Mood Agent - Extracts dialogue config and emotions.

Production Level Features:
- Voice configuration for TTS (pitch, rate, stability)
- Speech samples for few-shot LLM prompting
- Non-verbal cues separation for game engines
- Current mood (TEMPORARY emotional state in this scene)

This handles TEMPORARY emotional states that personality.py explicitly excludes.
"""
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from app.agents.llm import get_structured_llm, safe_ainvoke


# === TTS Mapping ===
TONE_TO_VOICE_CONFIG = {
    # Korean tones
    "차가운": {"base_pitch": "low", "speaking_rate": 0.85, "stability": 0.3},
    "단호한": {"base_pitch": "low", "speaking_rate": 0.95, "stability": 0.5},
    "따뜻한": {"base_pitch": "medium", "speaking_rate": 1.0, "stability": 0.6},
    "부드러운": {"base_pitch": "medium-high", "speaking_rate": 0.9, "stability": 0.7},
    "격앙된": {"base_pitch": "high", "speaking_rate": 1.2, "stability": 0.2},
    "침착한": {"base_pitch": "medium", "speaking_rate": 0.9, "stability": 0.8},
    "위협적인": {"base_pitch": "low", "speaking_rate": 0.8, "stability": 0.3},
    # English tones
    "cold": {"base_pitch": "low", "speaking_rate": 0.85, "stability": 0.3},
    "warm": {"base_pitch": "medium", "speaking_rate": 1.0, "stability": 0.6},
    "aggressive": {"base_pitch": "low", "speaking_rate": 1.1, "stability": 0.2},
    "calm": {"base_pitch": "medium", "speaking_rate": 0.9, "stability": 0.8},
    "formal": {"base_pitch": "medium", "speaking_rate": 0.95, "stability": 0.7},
    "casual": {"base_pitch": "medium-high", "speaking_rate": 1.05, "stability": 0.5},
    "default": {"base_pitch": "medium", "speaking_rate": 1.0, "stability": 0.5},
}

# Non-verbal cue patterns
NONVERBAL_PATTERNS = [
    (r'\((.*?한숨.*?)\)', 'ANIM_SIGH'),
    (r'\((.*?미소.*?)\)', 'ANIM_SMILE'),
    (r'\((.*?웃.*?)\)', 'ANIM_LAUGH'),
    (r'\((.*?울.*?)\)', 'ANIM_CRY'),
    (r'\((.*?분노.*?)\)', 'ANIM_ANGRY'),
    (r'\((.*?고개.*?끄덕.*?)\)', 'ANIM_NOD'),
    (r'\((.*?고개.*?흔들.*?)\)', 'ANIM_SHAKE_HEAD'),
    (r'\((.*?놀라.*?)\)', 'ANIM_SURPRISED'),
]


def generate_voice_config(tone: Optional[str], emotion: Optional[str] = None) -> dict:
    """Generate TTS-ready voice configuration from tone and emotion."""
    config = TONE_TO_VOICE_CONFIG.get("default").copy()
    
    if tone:
        tone_lower = tone.lower()
        for key, value in TONE_TO_VOICE_CONFIG.items():
            if key in tone_lower:
                config = value.copy()
                break
    
    # Adjust based on current emotion
    if emotion:
        emotion_lower = emotion.lower()
        if any(e in emotion_lower for e in ['두려움', 'fear', '불안', 'anxious']):
            config['stability'] = max(0.2, config.get('stability', 0.5) - 0.2)
            config['speaking_rate'] = min(1.3, config.get('speaking_rate', 1.0) + 0.1)
        elif any(e in emotion_lower for e in ['분노', 'anger', '격노', 'rage']):
            config['stability'] = max(0.1, config.get('stability', 0.5) - 0.3)
            config['speaking_rate'] = min(1.4, config.get('speaking_rate', 1.0) + 0.2)
        elif any(e in emotion_lower for e in ['슬픔', 'sad', '우울', 'depressed']):
            config['speaking_rate'] = max(0.7, config.get('speaking_rate', 1.0) - 0.2)
    
    # Add suggested voice ID placeholder
    config['suggested_voice_id'] = None
    
    return config


def extract_speech_samples(text: str, character_name: str) -> list[str]:
    """Extract direct speech samples for few-shot prompting."""
    import re
    samples = []
    
    # Pattern: 'dialogue' or "dialogue" after character name
    patterns = [
        rf'{character_name}[이가는은]?\s*[말했다|외쳤다|말을|].*?[\'\"](.*?)[\'\"]',
        rf'[\'\"]([^\'\"]+)[\'\"]\s*{character_name}',
        rf'{character_name}.*?[\'\"](.*?)[\'\"]',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            clean = match.strip()
            if len(clean) > 3 and clean not in samples:
                samples.append(clean)
    
    return samples[:5]  # Max 5 samples


def parse_nonverbal_cues(text: str) -> dict:
    """Separate non-verbal cues from clean dialogue text."""
    import re
    
    performance_guides = []
    anim_triggers = []
    clean_text = text
    
    for pattern, anim_code in NONVERBAL_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            performance_guides.append(match)
            anim_triggers.append(anim_code)
    
    # Remove parenthetical expressions for clean text
    clean_text = re.sub(r'\([^)]*\)', '', text).strip()
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    return {
        "clean_text": clean_text if clean_text else text,
        "performance_guide": ", ".join(performance_guides) if performance_guides else None,
        "anim_triggers": list(set(anim_triggers)) if anim_triggers else [],
    }


# === Schema ===
class VoiceConfig(BaseModel):
    """TTS-ready voice configuration."""
    base_pitch: str = Field("medium", description="Voice pitch: low/medium/high")
    speaking_rate: float = Field(1.0, ge=0.5, le=2.0, description="Speaking rate (1.0 = normal)")
    stability: float = Field(0.5, ge=0.0, le=1.0, description="Voice stability (0=variable, 1=stable)")
    suggested_voice_id: Optional[str] = Field(None, description="Suggested TTS voice ID")


class DialogueComponents(BaseModel):
    """Separated dialogue components for game engines."""
    clean_text: str = Field("", description="Text without non-verbal cues")
    performance_guide: Optional[str] = Field(None, description="Acting directions (sighing, smiling)")
    anim_triggers: list[str] = Field(default_factory=list, description="Animation trigger codes")


class CurrentMood(BaseModel):
    """Scene-specific emotional state."""
    emotion: Optional[str] = Field(None, description="Primary emotion (fear, anger, hope)")
    intensity: int = Field(5, ge=1, le=10, description="Emotion intensity 1-10")
    trigger: Optional[str] = Field(None, description="What caused this emotion")


class DialogueConfig(BaseModel):
    """Dialogue generation configuration."""
    tone: Optional[str] = Field(None, description="Speaking tone (formal/casual/aggressive/calm)")
    catchphrases: list[str] = Field(default_factory=list, description="Signature phrases")
    forbidden_topics: list[str] = Field(default_factory=list, description="Topics to avoid")
    secret_keys: list[str] = Field(default_factory=list, description="Secrets the character holds")
    
    # Validator to handle None -> empty list
    @field_validator('catchphrases', 'forbidden_topics', 'secret_keys', mode='before')
    @classmethod
    def none_to_empty_list(cls, v):
        """Convert None to empty list for list fields."""
        return v if v is not None else []


class CharacterDialogueMood(BaseModel):
    """Single character's dialogue config and mood."""
    name: str = Field(..., description="Character name for matching")
    dialogue: DialogueConfig = Field(default_factory=DialogueConfig)
    current_mood: CurrentMood = Field(default_factory=CurrentMood)


class CharacterDialogueMoodResult(BaseModel):
    """Result of dialogue/mood extraction."""
    characters: list[CharacterDialogueMood] = Field(default_factory=list)
    
    # Validator to handle string input (LLM sometimes returns JSON string)
    @field_validator('characters', mode='before')
    @classmethod
    def parse_characters_string(cls, v):
        """Parse characters from string if LLM returns JSON string instead of list."""
        if isinstance(v, str):
            import json
            import re
            
            # Clean JSON: remove trailing commas (common LLM error)
            cleaned = re.sub(r',\s*}', '}', v)  # Remove comma before }
            cleaned = re.sub(r',\s*]', ']', cleaned)  # Remove comma before ]
            # Remove any other invalid control characters
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
            
            try:
                # Try direct JSON parse
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
            
            # Try to extract individual character objects
            results = []
            # Pattern to match individual character objects
            object_pattern = r'\{\s*"name"\s*:\s*"[^"]+"\s*,.*?\}(?=\s*[,\]]|\s*$)'
            matches = re.findall(object_pattern, cleaned, re.DOTALL)
            
            for match in matches:
                try:
                    # Try to fix incomplete JSON
                    fixed = match
                    # Count braces to fix incomplete objects
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
                print(f"[DIALOGUE_MOOD] Recovered {len(results)} characters from partial JSON")
                return results
            
            # Last resort: try to fix truncated JSON
            try:
                # Add missing closing brackets
                open_brackets = cleaned.count('[') - cleaned.count(']')
                open_braces = cleaned.count('{') - cleaned.count('}')
                fixed = cleaned + '}' * open_braces + ']' * open_brackets
                return json.loads(fixed)
            except json.JSONDecodeError as e:
                print(f"[DIALOGUE_MOOD] JSON parse error: {e}")
                print(f"[DIALOGUE_MOOD] Cleaned string: {cleaned[:300]}...")
                return []
        return v if v is not None else []


# === Prompt ===
DIALOGUE_MOOD_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert story analyst. Extract DIALOGUE STYLE and CURRENT MOOD.

### ⚠️ CRITICAL: EXTRACT EACH CHARACTER SEPARATELY ⚠️ ###
❗ If there are 3 characters in the story (e.g., 클레어, 잭슨, 헤이즈 교수), you MUST return 3 SEPARATE character entries.
❗ NEVER return only one character when multiple characters exist.
❗ Even if a character has minimal dialogue, include them with inferred mood based on context.

### CORRECT OUTPUT EXAMPLE (3 characters) ###
{{
  "characters": [
    {{"name": "클레어", "current_mood": {{"emotion": "불안", "intensity": 7}}, ...}},
    {{"name": "잭슨", "current_mood": {{"emotion": "흥분", "intensity": 8}}, ...}},
    {{"name": "헤이즈 교수", "current_mood": {{"emotion": "neutral", "intensity": 5}}, ...}}
  ]
}}

### ❌ WRONG: DO NOT DO THIS ###
{{
  "characters": [
    {{"name": "클레어", "current_mood": {{"emotion": "불안"}}, ...}}  ← WRONG! Other characters are missing!
  ]
}}

### LANGUAGE CONSISTENCY RULE ###
Output ALL text in the SAME language as the input.

### CRITICAL: NAME EXTRACTION RULE ###
When a character is introduced as "베라(Vera)" or "리안(Lian)", use ONLY the Korean name.
The English in parentheses is just a transliteration hint - DO NOT use it.
❌ BAD: "name": "Vera", "name": "Lian", "name": "Tio"
✅ GOOD: "name": "베라", "name": "리안", "name": "티오"

### CURRENT MOOD (Temporary Emotional State) - REQUIRED ###
IMPORTANT: You MUST extract current_mood for every character.
Infer emotions from context clues such as:
- Physical descriptions: "심장이 빠르게 뛰다" → 긴장/두려움
- Voice/tone descriptions: "목소리는 차가웠다" → 차가움
- Body language: "입술을 깨물다" → 긴장/불안
- Actions: "검을 뽑았다" → 적의/결의

Examples:
- "그녀의 목소리에 약간의 두려움이 섞여 있었다" → emotion: "두려움", intensity: 6
- "목소리는 차가웠다", "감정을 드러내지 않았다" → emotion: "냉담", intensity: 7
- No emotion cues at all → emotion: "neutral", intensity: 5

Include:
- emotion: The primary feeling (NEVER leave as null - infer from context or use "neutral")
- intensity: How strong (1-10)
- trigger: What caused it (can be null if unclear)

### DIALOGUE CONFIGURATION ###
Extract speaking patterns for AI dialogue generation:
- tone: How they speak (formal, casual, cold, warm)
- catchphrases: Repeated phrases or expressions SPOKEN BY this character
- forbidden_topics: What they refuse to discuss
- secret_keys: Information only they know

### CRITICAL: CATCHPHRASE ATTRIBUTION ###
⚠️ A catchphrase belongs to the SPEAKER, NOT the target!
Example: 베라 said \"여전히 쥐새끼처럼 빠르네, 리안.\"
❌ BAD: 리안.catchphrases = [\"쥐새끼처럼 빠르다\"]  
✅ GOOD: 베라.catchphrases = [\"쥐새끼처럼 빠르네\"]
This phrase was SPOKEN BY 베라, so it goes in 베라's catchphrases, not 리안's.

### RULES ###
1. Focus on dialogue style, not content
2. current_mood is SCENE-SPECIFIC, not permanent personality
3. current_mood.emotion is REQUIRED - always infer from context
4. Other fields can be null if not mentioned in text

REMEMBER: Count the characters in the story and output the SAME number of character entries!"""),
    ("human", """Story text:
{story_text}

Extract dialogue configuration and current mood for ALL characters.
IMPORTANT: Every character MUST have current_mood.emotion filled (infer from context if not explicit).
If the story has 3 characters, return 3 entries. If it has 5 characters, return 5 entries.""")
])


# === Production Post-Processing ===
def validate_catchphrase_speaker(phrase: str, speaker_name: str, story_text: str) -> bool:
    """Validate that the phrase was actually spoken by the claimed speaker.
    
    Strategy:
    1. Find the phrase in the story
    2. Look BEFORE the phrase for speaker attribution patterns
    3. Check if the claimed speaker is the one speaking (not just mentioned in the dialogue)
    
    Returns: True if speaker attribution is valid
    """
    if not phrase or not speaker_name or not story_text:
        return True  # Can't validate, assume valid
    
    import re
    
    # Normalize phrase for search
    phrase_clean = phrase.strip().replace('"', '').replace("'", "")
    
    # Try multiple search strategies
    phrase_pos = -1
    
    # Strategy 1: Direct match of first 15 chars
    phrase_search = phrase_clean[:15] if len(phrase_clean) > 15 else phrase_clean
    phrase_pos = story_text.find(phrase_search)
    
    # Strategy 2: Try key distinctive words (≥3 chars)
    if phrase_pos == -1:
        words = re.findall(r'[가-힣]{3,}', phrase_clean)
        for word in words:
            pos = story_text.find(word)
            if pos != -1:
                phrase_pos = pos
                phrase_search = word
                break
    
    # Strategy 3: Try even shorter match
    if phrase_pos == -1:
        for i in range(min(10, len(phrase_clean)), 3, -1):
            phrase_pos = story_text.find(phrase_clean[:i])
            if phrase_pos != -1:
                phrase_search = phrase_clean[:i]
                break
    
    if phrase_pos == -1:
        # Cannot find phrase - be strict: reject if we can't validate
        print(f"[DIALOGUE_MOOD] FAILED: Cannot find '{phrase_clean[:20]}...' in story - rejecting")
        return False
    
    # Get context BEFORE the phrase (150 chars) - this is where speaker attribution would be
    context_start = max(0, phrase_pos - 150)
    context_before = story_text[context_start:phrase_pos]
    
    # Get context of the phrase itself (to check who is mentioned IN the dialogue)
    phrase_context = story_text[phrase_pos:phrase_pos + len(phrase_clean) + 20]
    
    # === Key logic ===
    # The SPEAKER's name should appear BEFORE the quote (attribution)
    # The TARGET's name might appear IN the quote (being addressed)
    
    # Check if speaker_name is in context_before (speaker attribution)
    speaker_in_attribution = speaker_name in context_before
    
    # Check if speaker_name appears ONLY inside the dialogue (as target)
    speaker_only_in_dialogue = speaker_name in phrase_context and speaker_name not in context_before
    
    if speaker_only_in_dialogue:
        # Speaker name only appears in dialogue = they are being ADDRESSED, not speaking
        print(f"[DIALOGUE_MOOD] Catchphrase validation FAILED: '{phrase_search[:20]}' - '{speaker_name}' is ADDRESSED, not SPEAKER")
        return False
    
    if not speaker_in_attribution:
        # Speaker name not in attribution context
        print(f"[DIALOGUE_MOOD] Catchphrase validation FAILED: '{phrase_search[:20]}' - '{speaker_name}' not found before phrase")
        return False
    
    print(f"[DIALOGUE_MOOD] Catchphrase validation PASSED: '{phrase_search[:20]}' spoken by '{speaker_name}'")
    return True

def post_process_dialogue_mood(
    raw_data: dict,
    story_text: str = "",
) -> dict:
    """Apply production-level post-processing.
    
    Features:
    1. Voice Config generation for TTS
    2. Speech Samples extraction for few-shot LLM
    3. Non-verbal cues parsing for game engines
    4. Catchphrase speaker validation
    """
    import re
    
    data = dict(raw_data)
    name = data.get('name', '')
    
    dialogue = data.get('dialogue', {})
    mood = data.get('current_mood', {})
    
    # 0. Validate catchphrase speaker attribution
    if dialogue.get('catchphrases'):
        validated_catchphrases = []
        for phrase in dialogue['catchphrases']:
            if validate_catchphrase_speaker(phrase, name, story_text):
                validated_catchphrases.append(phrase)
        dialogue['catchphrases'] = validated_catchphrases
        data['dialogue'] = dialogue
    
    # 1. Generate voice config for TTS
    data['voice_config'] = generate_voice_config(
        tone=dialogue.get('tone'),
        emotion=mood.get('emotion')
    )
    
    # 2. Extract speech samples for few-shot prompting
    data['speech_samples'] = extract_speech_samples(story_text, name)
    
    # 3. Parse non-verbal cues from multiple sources
    dialogue_components = []
    seen_texts = set()
    
    # 3a. From catchphrases
    for phrase in dialogue.get('catchphrases', []):
        components = parse_nonverbal_cues(phrase)
        if components['clean_text'] and components['clean_text'] not in seen_texts:
            dialogue_components.append(components)
            seen_texts.add(components['clean_text'])
    
    # 3b. From story text - extract lines mentioning this character with parenthetical cues
    if name and story_text:
        # Find sentences/lines that mention the character AND contain parenthetical expressions
        # Pattern: look for lines with (something) near character name
        lines = story_text.replace('\n\n', '\n').split('\n')
        for line in lines:
            if name in line and re.search(r'\([^)]+\)', line):
                components = parse_nonverbal_cues(line)
                if components['anim_triggers'] and components['clean_text'] not in seen_texts:
                    dialogue_components.append(components)
                    seen_texts.add(components['clean_text'])
    
    data['dialogue_components'] = dialogue_components
    
    return data


# === Node Function ===
async def dialogue_mood_extraction_node(state: dict) -> dict:
    """Dialogue/Mood Agent - Extracts dialogue config and current mood.
    
    Production Features:
    - voice_config: TTS-ready parameters (pitch, rate, stability)
    - speech_samples: Few-shot prompting examples
    - dialogue_components: Non-verbal cues separated
    """
    # Use advanced tier for accurate catchphrase attribution and mood analysis
    structured_llm = get_structured_llm(CharacterDialogueMoodResult, tier="premium")
    chain = DIALOGUE_MOOD_EXTRACTION_PROMPT | structured_llm
    
    story_text = state.get("content", "")
    
    try:
        result: CharacterDialogueMoodResult = await safe_ainvoke(chain, {
            "story_text": story_text
        })
        
        dialogue_mood_data = {}
        for char in result.characters:
            raw_data = char.model_dump()
            # Apply production post-processing
            processed_data = post_process_dialogue_mood(raw_data, story_text)
            dialogue_mood_data[char.name] = processed_data
        
        return {
            "char_dialogue_mood": dialogue_mood_data,
            "completed_agents": (state.get("completed_agents") or []) + ["dialogue_mood"],
            "messages": [{
                "role": "dialogue_mood_agent", 
                "content": f"Extracted {len(dialogue_mood_data)} character dialogues/moods (production-ready)"
            }]
        }
    except Exception as e:
        return {
            "char_dialogue_mood": {},
            "errors": (state.get("errors") or []) + [f"Dialogue/mood extraction failed: {str(e)}"]
        }
