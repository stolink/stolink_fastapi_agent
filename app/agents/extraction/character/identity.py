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

from app.agents.llm import get_structured_llm, safe_ainvoke
from app.services.embedding_service import get_embedding_service


# === Embedding Generation ===
async def generate_character_embeddings_batch(characters: dict) -> None:
    """Generate embeddings for characters using Gemini (3072 dim).
    
    Args:
        characters: Dict of {name: character_dict}
    """
    if not characters:
        return

    service = get_embedding_service()
    names = list(characters.keys())
    texts = []
    
    for name in names:
        char_data = characters[name]
        role = char_data.get("role", "unknown")
        backstory = char_data.get("backstory", "") or ""
        # Create rich text for embedding
        text_to_embed = f"Character: {name}. Role: {role}. Backstory: {backstory}"
        texts.append(text_to_embed)
    
    try:
        # Batch generation
        embeddings = await service.generate_embeddings_batch(texts)
        
        for i, name in enumerate(names):
            characters[name]["embedding"] = embeddings[i]
            
    except Exception as e:
        print(f"[IDENTITY] Batch embedding generation failed: {e}")
        # Initialize empty
        for name in names:
            if "embedding" not in characters[name]:
                characters[name]["embedding"] = []


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

### ⚠️ CRITICAL: EXTRACT EACH CHARACTER SEPARATELY ⚠️ ###
❗ If there are 3 characters (e.g., 클레어, 잭슨, 헤이즈 교수), you MUST return 3 SEPARATE character entries.
❗ NEVER combine multiple characters into a single entry.
❗ Each character object in the output list represents ONE person.

### CORRECT OUTPUT EXAMPLE (3 characters) ###
{{
  "characters": [
    {{"name": "클레어", "role": "protagonist", "gender": "female", "aliases": [], ...}},
    {{"name": "잭슨", "role": "supporting", "gender": "male", "aliases": [], ...}},
    {{"name": "헤이즈 교수", "role": "supporting", "gender": "male", "aliases": ["박사"], ...}}
  ]
}}

### ❌ WRONG: DO NOT DO THIS ###
{{
  "characters": [
    {{"name": "헤이즈 교수", "aliases": ["클레어", "잭슨", "박사"], ...}}  ← WRONG! Other characters listed as aliases!
  ]
}}

### CRITICAL: aliases RULES ###
⚠️ aliases MUST ONLY contain nicknames, titles, or alternate names for THE SAME character.
⚠️ aliases must NOT contain OTHER CHARACTERS' names.
✅ CORRECT: 헤이즈 교수의 aliases = ["박사", "교수님"] (titles for the same person)
❌ WRONG: 헤이즈 교수의 aliases = ["클레어", "잭슨"] (these are different people!)

### WHAT IS A CHARACTER? ###
✅ A CHARACTER is a SPECIFIC PERSON or BEING with a PROPER NAME who acts, speaks, or thinks.
❌ NOT a character: objects, items, places, organizations, groups, generic crowds

### LANGUAGE CONSISTENCY ###
Output ALL text in the SAME language as the input.
If the story is in Korean, all values must be in Korean.

### KOREAN NAME RULE ###
When a character is introduced as "베라(Vera)", extract ONLY the Korean name "베라".

### EXTRACTION FOCUS ###
For EACH character, extract:
- name: Character's PROPER NAME (REQUIRED)
- age: Exact age or estimate if mentioned
- gender: male/female/unknown
- race: Race/species if mentioned
- occupation: Job, class, or profession
- faction: Organization, group, or affiliation
- role: protagonist/antagonist/supporting/mentor/sidekick/other
- aliases: Nicknames/titles FOR THIS CHARACTER ONLY (not other characters)
- status: alive/deceased/unknown
- backstory: Background information

REMEMBER: If you see 3 different character names in the text, output 3 SEPARATE character objects!"""),
    ("human", """Story text:
{story_text}

Extract ALL characters mentioned. Output each character as a SEPARATE entry in the characters list.""")
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


# === NON-CHARACTER FILTER: Names that should NOT be characters ===
NON_CHARACTER_KEYWORDS = [
    # Items (Weapons/Armor)
    "검", "칼", "창", "활", "방패", "갑옷", "투구", "무기",
    "sword", "blade", "spear", "bow", "shield", "armor", "weapon",
    
    # Modern/Sci-Fi Items
    "총", "건", "라이플", "권총", "슈트", "코트", "임플란트", "칩",
    "gun", "rifle", "pistol", "suit", "coat", "implant", "chip",
    
    # Places (Korean)
    "지구", "서울", "부산", "도쿄", "뉴욕", "도시", "마을",
    "행성", "위성", "우주", "정거장", "우주선", "기지",
    "쉘터", "본부", "연구소", "병원", "학교", "건물",
    "노아", "벙커", "아지트", "광장", "거리", "빌딩",
    
    # Places (English)
    "earth", "planet", "city", "station", "shelter", "base",
    
    # Organizations/Groups
    "생존자들", "회사", "기업", "정부", "군대", "조직", "협회",
    "연합", "동맹", "부대", "기관",
    
    # Generic Descriptors (NOT proper names)
    # Generic Descriptors (NOT proper names)
    # Relaxed filter: Allow generic descriptors that could be key characters (e.g. "Young Woman")
    # Entity Resolution will handle merging duplicates like "생존자" + "젊은 여성"
    "그 남자", "그 여자",
    "사람", "인간", "누군가",
    "당신", "너",
    # NOTE: Removed "이", "저", "그", "그녀", "노인", "아이", "그쪽" - can appear in valid character names
    # e.g., "헤이즈 교수" contains "이", "이선생", "저 사람" (pointing)
]

# Track logged names to prevent duplicate log messages
_logged_filter_matches: set = set()

def is_likely_item(name: str) -> bool:
    """Check if name looks like an item/place/org rather than a character."""
    name_clean = name.strip()
    
    # Explicit Whitelist for Key Generic Characters
    whitelist = ["Young Woman", "Young Man", "Old Man", "Voice", "여성", "젊은 여성", "노인", "목소리"]
    if name_clean in whitelist:
        print(f"[IDENTITY] Whitelist MATCH for: {repr(name_clean)}")
        return False

    # Normalize name (remove spaces) for matching
    name_normalized = name_clean.replace(" ", "").lower()
    for keyword in NON_CHARACTER_KEYWORDS:
        keyword_normalized = keyword.replace(" ", "").lower()
        if keyword_normalized in name_normalized or keyword in name_clean:
            # Suppress duplicate log messages for same name/keyword pair
            log_key = (name, keyword)
            if log_key not in _logged_filter_matches:
                _logged_filter_matches.add(log_key)
                print(f"[IDENTITY] Filter matched: '{name}' contains '{keyword}'")
            return True
    return False

# === Node Function ===
async def identity_extraction_node(state: dict) -> dict:
    """Identity Agent - Extracts basic character information."""
    # Use premium tier (gemini-3-flash) for best character identification
    structured_llm = get_structured_llm(CharacterIdentityResult, tier="premium")
    chain = IDENTITY_EXTRACTION_PROMPT | structured_llm
    
    try:
        result: CharacterIdentityResult = await safe_ainvoke(chain, {
            "story_text": state["content"]
        })
        
        # Convert to dict keyed by character name
        identity_data = {}
        filtered_count = 0
        all_names = [char.name for char in result.characters]
        print(f"[IDENTITY] LLM extracted names: {all_names}")
        
        for char in result.characters:
            # Filter out items that LLM incorrectly identified as characters
            # if is_likely_item(char.name):
            #     print(f"[IDENTITY] Filtered out item: '{char.name}' (not a character)")
            #     filtered_count += 1
            #     continue
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
        
        # === Generate Embeddings ===
        print(f"[IDENTITY] Generating embeddings for {len(identity_data)} characters...")
        await generate_character_embeddings_batch(identity_data)
        
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

