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

### CRITICAL: WHAT IS A CHARACTER? ###
⚠️ A CHARACTER is a PERSON or BEING with sentience who can act, speak, or think.
⚠️ A CHARACTER is NOT an object, item, weapon, clothing, or body part.

✅ CHARACTERS: 진하, 세라, ARIA, 유민재, 리사 (people/beings with names who act in the story)
❌ NOT CHARACTERS: 트렌치코트, 홀로그램 방패, 뇌 임플란트, 기계 팔, 메모리 칩, 검은 슈트, 플라즈마 건

	### EXCLUSION EXAMPLES (NOT CHARACTERS) ###
	- "낡은 트렌치코트" → CLOTHING (Item)
	- "전설의 검" → WEAPON (Item)
	- "스마트폰" → DEVICE (Item)
	- "기계 팔" → PROSTHETIC (Body part/Item)
	- "마법 지팡이" → WEAPON (Item)

	### LANGUAGE CONSISTENCY RULE ###
	Output ALL text in the SAME language as the input.
If the story is in Korean, all values must be in Korean.
Do NOT translate (e.g., "암흑회" not "Dark Order").

### CRITICAL: NAME EXTRACTION RULE ###
When a character is introduced as "베라(Vera)" or "리안(Lian)", extract ONLY the Korean name.
The English in parentheses is just a transliteration hint - DO NOT create separate characters.
❌ BAD: Extract both "Vera" and "베라" as different characters
✅ GOOD: Extract only "베라" (use Korean name)

### EXTRACTION FOCUS ###
For each character, extract:
- name: Character's name as it appears in text (REQUIRED)
- age: Exact age or estimate if mentioned
- gender: male/female/unknown
- race: Race/species if mentioned (e.g., human, android, AI)
- occupation: Job, class, or profession
- faction: Organization, group, or affiliation
- role: Main story role (protagonist/antagonist/supporting/mentor/sidekick/other)
- aliases: Any nicknames, titles, descriptive references, or REAL NAMES
- status: alive/deceased/unknown
- backstory: Background information

### RULES ###
1. Extract ONLY characters (people/beings), NOT objects or items
2. Use EXACT names from the text
3. Focus ONLY on identity information, not appearance or personality"""),
    ("human", """Story text:
{story_text}

Extract identity information for all CHARACTERS (people/beings who act in the story).
DO NOT extract items, weapons, clothing, or devices as characters.""")
])


# === Helper: Detect AI/Non-physical characters ===
AI_RACE_KEYWORDS = ["ai", "인공지능", "안드로이드", "로봇", "android", "robot", "artificial intelligence", "시스템", "보조 시스템"]

def is_ai_character(identity: dict) -> bool:
    """Check if character is a non-physical AI (like ARIA)."""
    race = (identity.get("race") or "").lower()
    backstory = (identity.get("backstory") or "").lower()
    
    # Check for AI keywords in race
    for keyword in AI_RACE_KEYWORDS:
        if keyword in race:
            # But exclude androids with physical bodies (like 세라)
            if "바디" in backstory or "body" in backstory.lower():
                return False  # Physical android body
            if "임플란트" in backstory or "탑재" in backstory:
                return True  # Brain implant AI = non-physical
            return True
    return False


# === Helper: Name normalization ===
def normalize_character_names(identity_data: dict, story_text: str) -> dict:
    """Deduplicate Korean/English name variants."""
    from .aggregator import extract_name_pairs_from_text, korean_to_romanization_variants, is_korean
    
    # Build name mapping from story text
    name_mapping = extract_name_pairs_from_text(story_text)
    
    # Also detect romanization matches
    korean_names = {n for n in identity_data.keys() if is_korean(n)}
    english_names = {n for n in identity_data.keys() if not is_korean(n)}
    
    # Helper to normalize names (remove hyphens, spaces, underscores)
    def normalize_for_match(name: str) -> str:
        return name.lower().replace("-", "").replace("_", "").replace(" ", "")
    
    for korean in korean_names:
        variants = korean_to_romanization_variants(korean)
        variants_normalized = [normalize_for_match(v) for v in variants]
        for english in english_names:
            english_normalized = normalize_for_match(english)
            if english_normalized in variants_normalized:
                name_mapping[english] = korean
                print(f"[IDENTITY] Auto-mapped: '{english}' → '{korean}' (matched: {english_normalized})")
    
    # Remove duplicates (keep Korean version)
    to_remove = []
    for english, korean in name_mapping.items():
        if english in identity_data and korean in identity_data:
            to_remove.append(english)
            print(f"[IDENTITY] Removing duplicate: '{english}' (keeping '{korean}')")
        elif english in identity_data:
            # English only - rename to Korean
            identity_data[korean] = identity_data[english]
            identity_data[korean]["name"] = korean
            to_remove.append(english)
            print(f"[IDENTITY] Renamed: '{english}' → '{korean}'")
    
    for name in to_remove:
        if name in identity_data:
            del identity_data[name]
    
    return identity_data


# === Node Function ===
async def identity_extraction_node(state: dict) -> dict:
    """Identity Agent - Extracts basic character information."""
    # Use advanced tier for complex role/identity inference
    structured_llm = get_structured_llm(CharacterIdentityResult, tier="standard")
    chain = IDENTITY_EXTRACTION_PROMPT | structured_llm
    
    # === ITEM FILTER: Names that should NOT be characters ===
    ITEM_KEYWORDS = [
    # Generic Items (Weapons/Armor)
    "검", "칼", "창", "활", "방패", "갑옷", "투구", "무기",
    "sword", "blade", "spear", "bow", "shield", "armor", "helm", "weapon",
    
    # Modern/Sci-Fi Items
    "총", "건", "라이플", "권총", "슈트", "코트", "임플란트", "칩", "디바이스", "폰",
    "gun", "rifle", "pistol", "suit", "coat", "implant", "chip", "device", "phone",
    
    # Common Objects
    "책", "지팡이", "반지", "목걸이", "가방",
    "book", "staff", "ring", "necklace", "bag"
]    
    def is_likely_item(name: str) -> bool:
        """Check if name looks like an item rather than a character."""
        # Normalize name (remove spaces) for matching
        name_normalized = name.replace(" ", "").lower()
        for keyword in ITEM_KEYWORDS:
            keyword_normalized = keyword.replace(" ", "").lower()
            if keyword_normalized in name_normalized or keyword in name:
                return True
        return False
    
    try:
        result: CharacterIdentityResult = await chain.ainvoke({
            "story_text": state["content"]
        })
        
        # Convert to dict keyed by character name
        identity_data = {}
        filtered_count = 0
        all_names = [char.name for char in result.characters]
        print(f"[IDENTITY] LLM extracted names: {all_names}")
        
        for char in result.characters:
            # Filter out items that LLM incorrectly identified as characters
            if is_likely_item(char.name):
                print(f"[IDENTITY] Filtered out item: '{char.name}' (not a character)")
                filtered_count += 1
                continue
            identity_data[char.name] = char.model_dump()
        
        if filtered_count > 0:
            print(f"[IDENTITY] Filtered {filtered_count} items from character list")
        
        # === Method 2: Name Normalization ===
        identity_data = normalize_character_names(identity_data, state["content"])
        
        # === Method 3: Mark AI characters for agent skipping ===
        ai_characters = []
        for name, identity in identity_data.items():
            if is_ai_character(identity):
                identity["_skip_agents"] = ["appearance", "inventory", "stats"]
                ai_characters.append(name)
                print(f"[IDENTITY] AI character detected: '{name}' - will skip appearance/inventory/stats")
        
        return {
            "char_identity": identity_data,
            "ai_characters": ai_characters,  # Pass to supervisor
            "completed_agents": (state.get("completed_agents") or []) + ["identity"],
            "messages": [{"role": "identity_agent", "content": f"Extracted {len(identity_data)} character identities ({len(ai_characters)} AI)"}]
        }
    except Exception as e:
        print(f"[IDENTITY] Exception: {e}")
        return {
            "char_identity": {},
            # CRITICAL: Still mark as completed to prevent infinite loop
            "completed_agents": (state.get("completed_agents") or []) + ["identity"],
            "errors": (state.get("errors") or []) + [f"Identity extraction failed: {str(e)}"]
        }

