"""Character Aggregator - Merges all sub-agent results into FullCharacter.

Takes results from all sub-agents and combines them by character name
into the FullCharacter format expected by the main pipeline.

Sub-agents:
- Identity, Appearance, Personality, Relations, Dialogue/Mood, Inventory

Improvements:
- Null Safety: Game-related fields use safe defaults instead of null
- Naming: relations.graph (not relations.relations)
- Optimization: event_refs for Event IDs instead of full text
- Embedding: Generate embedding for Neo4j vector search
"""
# import boto3  <-- Removed AWS dependency
import json
from typing import Any

from app.schemas.characters import FullCharacter, FullCharacterExtractionResult
from app.services.embedding_service import get_embedding_service
from app.agents.extraction.character.identity import NON_CHARACTER_KEYWORDS, is_likely_item



async def generate_character_embedding(name: str, traits: list, role: str) -> list[float]:
    """Generate embedding for character using Gemini (3072 dim).
    
    Creates embedding from character name + traits + role for vector search.
    Returns empty list if generation fails (non-blocking).
    """
    try:
        # Build text to embed
        trait_str = ", ".join(traits[:5]) if traits else ""
        text_to_embed = f"Character: {name}. Role: {role}. Traits: {trait_str}"
        
        service = get_embedding_service()
        # Use async wrapper for embedding generation
        return await service.generate_embedding_async(text_to_embed)
    except Exception as e:
        print(f"[AGGREGATOR] Embedding generation failed for {name}: {e}")
        return []  # Non-blocking - return empty list


# === Safe Defaults for Game Engine ===
# Simplified - only faction.social defaults
SAFE_DEFAULTS = {
    "faction": {
        "social": {
            "rank": "COMMON",
            "influence": 0,
            "faction_reputation": {},
        }
    },
}

# === Dynamic Korean ↔ English Name Detection ===
# Instead of hardcoding, we detect Korean vs English and find matching pairs

import re

def is_korean(text: str) -> bool:
    """Check if text contains Korean characters."""
    if not text:
        return False
    # Korean Unicode ranges: Hangul Syllables (AC00-D7AF), Hangul Jamo (1100-11FF), etc.
    korean_pattern = re.compile(r'[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]')
    return bool(korean_pattern.search(text))

def is_english_only(text: str) -> bool:
    """Check if text is ASCII/English only."""
    if not text:
        return False
    return all(ord(c) < 128 for c in text)

# === Korean Syllable Romanization Table ===
# Maps Korean syllables to possible romanizations
KOREAN_TO_ROMANIZATION = {
    # Common syllables - multiple romanization variants
    "리": ["ri", "li", "ree", "lee"],
    "안": ["an", "ahn"],
    "베": ["be", "ve", "bae"],
    "라": ["ra", "la"],
    "티": ["ti", "tee"],
    "오": ["o", "oh"],
    "아": ["a", "ah"],
    "이": ["i", "ee", "yi"],
    "에": ["e", "ae"],
    "우": ["u", "oo", "wu"],
    "나": ["na"],
    "다": ["da", "ta"],
    "마": ["ma"],
    "바": ["ba", "pa"],
    "사": ["sa"],
    "자": ["ja", "cha"],
    "카": ["ka", "ca"],
    "타": ["ta", "da"],
    "파": ["pa", "ba"],
    "하": ["ha"],
    "가": ["ga", "ka"],
    "노": ["no"],
    "도": ["do", "to"],
    "로": ["ro", "lo"],
    "모": ["mo"],
    "보": ["bo", "po"],
    "소": ["so"],
    "요": ["yo"],
    "조": ["jo", "cho"],
    "코": ["ko", "co"],
    "토": ["to", "do"],
    "포": ["po", "bo"],
    "호": ["ho"],
    "고": ["go", "ko"],
    "미": ["mi", "mee"],
    "니": ["ni", "nee"],
    "시": ["si", "shi", "see"],
    "지": ["ji", "jee", "chi"],
    "키": ["ki", "kee"],
    "히": ["hi", "hee"],
    "기": ["gi", "ki", "gee"],
    "비": ["bi", "bee", "vi"],
    "피": ["pi", "pee"],
    "안": ["an", "ahn"],
    "언": ["eon", "un", "on"],
    "온": ["on", "ohn"],
    "은": ["eun", "un"],
    "인": ["in", "een"],
    "엔": ["en"],
    "운": ["un", "woon", "oon"],
    # === Additional syllables for common names ===
    "진": ["jin", "jean", "jin"],
    "세": ["se", "sae", "seh"],
    "유": ["yu", "you", "yoo"],
    "민": ["min", "meen"],
    "재": ["jae", "je", "jay"],
    "리": ["ri", "lee", "li"],
    "라": ["ra", "la"],
    "아리": ["ari", "arie"],
}

def korean_to_romanization_variants(korean_name: str) -> list[str]:
    """Generate possible romanization variants for a Korean name.
    
    Example: "리안" → ["rian", "lian", "lean", "rean", ...]
    """
    if not korean_name or not is_korean(korean_name):
        return []
    
    # Start with one empty variant
    variants = [""]
    
    for char in korean_name:
        if char in KOREAN_TO_ROMANIZATION:
            # Expand variants with all possible romanizations
            new_variants = []
            for variant in variants:
                for romanization in KOREAN_TO_ROMANIZATION[char]:
                    new_variants.append(variant + romanization)
            variants = new_variants
        else:
            # Keep character as-is (for unknown syllables)
            variants = [v + char for v in variants]
    
    return list(set(variants))  # Remove duplicates


def find_romanization_match(korean_names: set, english_names: set) -> dict:
    """Find matches between Korean and English names using romanization.
    
    Returns: {english_name: korean_name} for matched pairs
    """
    matches = {}
    
    # Helper to normalize names (remove hyphens, spaces, underscores)
    def normalize_for_match(name: str) -> str:
        return name.lower().replace("-", "").replace("_", "").replace(" ", "")
    
    for korean in korean_names:
        variants = korean_to_romanization_variants(korean)
        variants_normalized = [normalize_for_match(v) for v in variants]
        
        for english in english_names:
            english_normalized = normalize_for_match(english)
            if english_normalized in variants_normalized:
                matches[english] = korean
                matches[english.lower()] = korean
                matches[english.upper()] = korean
                print(f"[AGGREGATOR] Romanization match: '{english}' → '{korean}' (matched: {english_normalized})")
    
    return matches


def extract_name_pairs_from_text(story_text: str) -> dict:
    """Extract Korean(English) patterns from story text to build name mapping.
    
    Looks for patterns like:
    - "베라(Vera)" → maps "Vera" to "베라"
    - "리안(Lian)" → maps "Lian" to "리안"
    """
    mapping = {}
    
    # Pattern: Korean name followed by (English name)
    # Example: 베라(Vera), 리안(Lian), 티오(Tio)
    pattern = r'([\uAC00-\uD7AF]+)\s*\(\s*([A-Za-z]+)\s*\)'
    
    matches = re.findall(pattern, story_text)
    for korean, english in matches:
        mapping[english] = korean
        mapping[english.lower()] = korean
        mapping[english.upper()] = korean
        print(f"[AGGREGATOR] Auto-detected name pair: '{english}' → '{korean}'")
    
    return mapping


# === POST-PROCESSING: Age Group Inference ===
AGE_GROUP_KEYWORDS = {
    "child": ["아이", "어린이", "꼬마", "child", "kid"],
    "teen": ["소년", "소녀", "청소년", "앳된", "teen", "teenager", "young man", "young woman"],
    "adult": ["성인", "청년", "adult", "man", "woman", "탐정", "브로커", "해커", "전사", "기사", "용병", "detective", "broker", "hacker", "warrior", "knight", "mercenary"],
    "elderly": ["노인", "할아버지", "할머니", "elderly", "old man", "old woman", "늙은"],
}

# AI/Robot races that should not have age_group
NON_AGING_RACES = ["인공지능", "AI", "로봇", "안드로이드", "android", "robot", "artificial intelligence"]

def get_character_context(name: str, story_text: str, window: int = 100) -> str:
    """Extract text context around character name mentions.
    
    Returns text within 'window' characters of each name mention.
    """
    if not story_text or not name:
        return ""
    
    contexts = []
    lower_story = story_text.lower()
    lower_name = name.lower()
    
    start = 0
    while True:
        pos = lower_story.find(lower_name, start)
        if pos == -1:
            break
        
        # Extract context window around name
        ctx_start = max(0, pos - window)
        ctx_end = min(len(story_text), pos + len(name) + window)
        contexts.append(story_text[ctx_start:ctx_end])
        start = pos + 1
    
    return " ".join(contexts)

def infer_age_group(name: str, appearance_data: dict, story_text: str = "", identity_data: dict = None) -> str | None:
    """Infer age_group from appearance descriptions or character-specific context.
    
    Returns: "child", "teen", "adult", "elderly", or None
    
    Note: AI/Robot characters return None (no biological age).
    """
    # === Skip AI/Robot characters ===
    if identity_data:
        race = (identity_data.get("race") or "").lower()
        for ai_race in NON_AGING_RACES:
            if ai_race.lower() in race:
                print(f"[AGGREGATOR] Skipping age_group for AI/Robot '{name}' (race: {race})")
                return None
    
    # Check full_visual_prompt first (character-specific)
    visual_prompt = appearance_data.get("full_visual_prompt", "")
    expression = appearance_data.get("expression", "")
    attire = " ".join(appearance_data.get("attire", []))
    
    # Get character-specific context (NOT entire story)
    char_context = get_character_context(name, story_text, window=50)
    
    # Combine appearance data + character-specific context
    search_text = f"{visual_prompt} {expression} {attire} {char_context}".lower()
    
    # Search in priority order: teen > elderly > adult > child
    # (teen is most specific, child is most generic)
    priority_order = ["teen", "elderly", "adult", "child"]
    
    for age_group in priority_order:
        keywords = AGE_GROUP_KEYWORDS[age_group]
        for keyword in keywords:
            if keyword.lower() in search_text:
                print(f"[AGGREGATOR] Inferred age_group '{age_group}' for '{name}' (keyword: '{keyword}')")
                return age_group
    
    return None


# === POST-PROCESSING: Role Inference from Context ===
# Keywords that indicate antagonist behavior (subject performs these actions)
ANTAGONIST_ACTION_PATTERNS = [
    (r"가 .{0,20}(공격|위협|죽이|협박|살기|경멸)", 1),  # X가...공격/위협
    (r"(의|는) (적|enemy)", 1),  # X는 적
]

# Keywords that indicate protagonist behavior (subject experiences these)
PROTAGONIST_ACTION_PATTERNS = [
    (r"가 .{0,20}(피하|도망|숨|회피|구하)", 1),  # X가...피하/도망
    (r"(을|를) (구하|지키)", 1),  # X를 구하다
]

def infer_role_from_context(name: str, relations_data: dict, story_text: str = "") -> str | None:
    """Infer character role from relationship context and story patterns.
    
    Strategy:
    1. Check relationship_origin: who is the attacker vs victim
    2. Check story context for action patterns
    3. Score and decide
    
    Returns: "protagonist", "antagonist", or None (keep extracted value)
    """
    import re
    
    antagonist_score = 0
    protagonist_score = 0
    
    # === 1. Relationship-based analysis ===
    relations = relations_data.get("relations", [])
    for rel in relations:
        rel_type = rel.get("type", "")
        origin = rel.get("relationship_origin", {})
        desc = (origin.get("event_description") or "").lower()
        target = (rel.get("target") or "").lower()
        
        if rel_type == "ENEMY":
            # Check: Does THIS character attack the target?
            # Pattern: "{name}가 {target}을 공격" or "{name}이/가 공격하"
            if any(kw in desc for kw in ["공격", "죽이", "위협", "해치"]):
                # Who is attacking whom?
                name_pos = desc.find(name.lower())
                target_pos = desc.find(target)
                attack_words = ["공격", "죽이", "위협"]
                attack_pos = min([desc.find(kw) for kw in attack_words if kw in desc] or [999])
                
                # If name comes before attack word → name is attacker
                if name_pos != -1 and name_pos < attack_pos:
                    antagonist_score += 3
                    print(f"[ROLE] '{name}' is ATTACKER in: {desc}")
                # If name comes after attack word → name is victim
                elif name_pos != -1 and name_pos > attack_pos:
                    protagonist_score += 3
                    print(f"[ROLE] '{name}' is VICTIM in: {desc}")
    
    # === 2. Story context analysis ===
    char_context = get_character_context(name, story_text, window=80)
    
    if char_context:
        lower_context = char_context.lower()
        
        # Check antagonist patterns (this character performs aggressive actions)
        for pattern, score in [
            (f"{name}.*?(공격|위협|죽이|협박)", 2),
            (f"{name}.*?(살기|경멸|비웃)", 1),
            (f"{name}[이가의].*?(마법|주문).*?(시전|영창|외우)", 1),  # Casting attack spells
        ]:
            if re.search(pattern, char_context, re.IGNORECASE):
                antagonist_score += score
        
        # Check protagonist patterns (this character evades/protects)
        for pattern, score in [
            (f"{name}.*?(피하|도망|숨|회피|굴러)", 2),
            (f"{name}.*?(지키|보호|구하)", 2),
            (f"{name}[이가을를].*?(공격|위협).*?받", 2),  # Being attacked
        ]:
            if re.search(pattern, char_context, re.IGNORECASE):
                protagonist_score += score
    
    # === 3. Decision ===
    print(f"[ROLE] '{name}' scores: antagonist={antagonist_score}, protagonist={protagonist_score}")
    
    if antagonist_score > protagonist_score and antagonist_score >= 2:
        print(f"[AGGREGATOR] Inferred role 'antagonist' for '{name}'")
        return "antagonist"
    elif protagonist_score > antagonist_score and protagonist_score >= 2:
        print(f"[AGGREGATOR] Inferred role 'protagonist' for '{name}'")
        return "protagonist"
    elif protagonist_score > 0 and antagonist_score == 0:
        # Only protagonist indicators, even if weak
        print(f"[AGGREGATOR] Inferred role 'protagonist' for '{name}' (weak signal)")
        return "protagonist"
    
    return None


def normalize_character_name(name: str, dynamic_mapping: dict = None) -> str:
    """Normalize character name to canonical form (Korean preferred).
    
    Uses dynamic mapping if available, falls back to keeping the name as-is.
    """
    if not name:
        return name
    
    # Check dynamic mapping first
    if dynamic_mapping and name in dynamic_mapping:
        normalized = dynamic_mapping[name]
        print(f"[AGGREGATOR] Normalizing name: '{name}' → '{normalized}'")
        return normalized
    
    # Keep Korean names as-is (they are canonical)
    return name


def build_name_merge_map(all_raw_names: set, dynamic_mapping: dict = None) -> dict:
    """Build a mapping from raw names to canonical names.
    
    Uses multiple strategies:
    1. Dynamic mapping from story text patterns (e.g., "베라(Vera)")
    2. Romanization matching (e.g., "Lian" ↔ "리안")
    
    Returns: {raw_name: canonical_name}
    Example: {"Vera": "베라", "베라": "베라", "Lian": "리안", ...}
    """
    # Separate Korean and English names
    korean_names = {n for n in all_raw_names if is_korean(n)}
    english_names = {n for n in all_raw_names if is_english_only(n)}
    
    print(f"[AGGREGATOR] Korean names: {korean_names}")
    print(f"[AGGREGATOR] English names: {english_names}")
    
    # Start with story-based mapping
    full_mapping = dict(dynamic_mapping) if dynamic_mapping else {}
    
    # Add romanization-based matching for names not in story pattern
    unmapped_english = {e for e in english_names if e not in full_mapping and e.lower() not in full_mapping}
    if unmapped_english and korean_names:
        romanization_matches = find_romanization_match(korean_names, unmapped_english)
        full_mapping.update(romanization_matches)
        print(f"[AGGREGATOR] Romanization matches found: {len(romanization_matches)}")
    
    # Build merge map
    merge_map = {}
    
    # 1. Initialize with strict mappings
    for name in all_raw_names:
        canonical = normalize_character_name(name, full_mapping)
        merge_map[name] = canonical

    # 2. Advanced Fuzzy Merging (Jaro-Winkler + Substring)
    # Sort canonical names by length (longest first) to prefer "Elara Vance" over "Elara"
    unique_canonicals = list(set(merge_map.values()))
    unique_canonicals.sort(key=len, reverse=True)
    
    final_canonical_map = {}  # {current_name: merged_targer}
    
    # Korean honorific suffixes to remove for matching (씨, 님, 군, 양, 선생, 교수, 주교 등)
    KOREAN_HONORIFICS = ['씨', '님', '군', '양', '선생', '교수', '주교', '신부', '대인', '공']
    
    def strip_honorifics(name: str) -> str:
        """Remove Korean honorifics for comparison."""
        result = name.strip()
        for suffix in KOREAN_HONORIFICS:
            if result.endswith(' ' + suffix):
                result = result[:-len(suffix)-1].strip()
            elif result.endswith(suffix) and len(result) > len(suffix):
                result = result[:-len(suffix)].strip()
        return result
    
    # Simple implementation of Jaro-Winkler-like similarity
    def get_similarity(s1, s2):
        s1, s2 = s1.lower(), s2.lower()
        if s1 == s2: return 1.0
        
        # Strip honorifics for Korean names and compare
        s1_stripped = strip_honorifics(s1)
        s2_stripped = strip_honorifics(s2)
        if s1_stripped and s2_stripped and s1_stripped == s2_stripped:
            return 1.0  # Same name after removing honorifics
        
        # Check if one is contained in the other (with honorifics stripped)
        if s1_stripped and s2_stripped:
            if s1_stripped in s2_stripped or s2_stripped in s1_stripped:
                return 0.95  # High similarity for substring match
        
        if s1 in s2 or s2 in s1: return 0.9  # Substring match
        
        # Count matching characters
        matches = 0
        len1, len2 = len(s1), len(s2)
        match_window = max(len1, len2) // 2 - 1
        
        s1_matches = [False] * len1
        s2_matches = [False] * len2
        
        for i in range(len1):
            start = max(0, i - match_window)
            end = min(i + match_window + 1, len2)
            for j in range(start, end):
                if s2_matches[j]: continue
                if s1[i] == s2[j]:
                    s1_matches[i] = True
                    s2_matches[j] = True
                    matches += 1
                    break
        
        if matches == 0: return 0.0
        
        # Simple Jaro score approximation
        return (matches / len1 + matches / len2 + (matches - 0) / matches) / 3

    processed = set()
    
    for i, name1 in enumerate(unique_canonicals):
        if name1 in processed: continue
        
        final_canonical_map[name1] = name1
        processed.add(name1)
        
        for j in range(i + 1, len(unique_canonicals)):
            name2 = unique_canonicals[j]
            if name2 in processed: continue
            
            # Skip if different scripts (e.g. Korean vs English) unless mapped
            if is_korean(name1) != is_korean(name2) and not is_english_only(name1) == is_english_only(name2):
                 continue

            sim = get_similarity(name1, name2)
            
            # Merge condition: High similarity or nice substring
            # e.g. "Elara Vance" (name1) vs "Elara" (name2) -> sim 0.9 via substring
            if sim > 0.85:
                print(f"[AGGREGATOR] Merging '{name2}' -> '{name1}' (Similarity: {sim:.2f})")
                final_canonical_map[name2] = name1
                processed.add(name2)
    
    # 3. Update original merge map
    for raw, canon in merge_map.items():
        if canon in final_canonical_map:
            merge_map[raw] = final_canonical_map[canon]
    
    canonical_names = set(merge_map.values())
    print(f"[AGGREGATOR] Name merge map: {len(all_raw_names)} raw → {len(canonical_names)} canonical")
    return merge_map




def clean_character_aliases(aliases: list, char_name: str, all_character_names: set) -> list:
    """Remove other character names that were incorrectly added as aliases.
    
    This fixes LLM errors where it puts other characters' names in the aliases list.
    
    Args:
        aliases: The aliases list to clean
        char_name: The name of this character
        all_character_names: Set of all known character names in the story
        
    Returns:
        Cleaned aliases list with only valid nicknames/titles for this character
    """
    if not aliases:
        return []
    
    cleaned = []
    char_name_lower = char_name.lower()
    
    for alias in aliases:
        if not alias or not isinstance(alias, str):
            continue
            
        alias_lower = alias.lower().strip()
        
        # Skip if the alias is another character's name
        is_other_character = False
        for other_name in all_character_names:
            other_name_lower = other_name.lower()
            # Allow aliases that contain this character's name (e.g., "Professor Hayes" for "Hayes")
            if other_name_lower == alias_lower and other_name_lower != char_name_lower:
                is_other_character = True
                print(f"[AGGREGATOR] Removed invalid alias '{alias}' from '{char_name}' (it's another character)")
                break
                
        if not is_other_character:
            cleaned.append(alias)
    
    return cleaned


def apply_safe_defaults(data: dict, defaults: dict) -> dict:
    """Apply safe defaults for null values."""
    result = {}
    for key, default_value in defaults.items():
        extracted_value = data.get(key)
        if extracted_value is None:
            result[key] = default_value
        else:
            result[key] = extracted_value
    return result


async def merge_character_data(
    identity: dict,
    appearance: dict,
    personality: dict,
    relations: dict,
    # Removed: dialogue_mood
    existing_characters: list = None,
    story_text: str = None,
    extracted_events: list = None
) -> list[dict]:
    """Merge sub-agent results by character name into FullCharacter format.
    
    Args:
        Each dict is keyed by character name with that agent's extracted data.
        existing_characters: List of pre-existing character dicts from context (reuses their IDs).
        story_text: Original story text for extracting Korean(English) name pairs.
    
    Returns:
        List of FullCharacter dicts with:
        - Null Safety: Game fields use safe defaults
        - relations.graph (not relations.relations)
        - event_refs (Event ID list)
        - Existing character IDs preserved
        - Deduplicated: Korean/English name variants merged
    """
    # === DYNAMIC NAME MAPPING: Extract Korean(English) pairs from story ===
    dynamic_mapping = {}
    if story_text:
        dynamic_mapping = extract_name_pairs_from_text(story_text)
        print(f"[AGGREGATOR] Dynamic name mapping from story: {dynamic_mapping}")
    
    # === BUILD CHARACTER -> EVENT_IDS MAPPING ===
    char_to_events = {}
    if extracted_events:
        for event in extracted_events:
            event_id = event.get("event_id")
            if event_id:
                for participant in event.get("participants", []):
                    if participant not in char_to_events:
                        char_to_events[participant] = []
                    if event_id not in char_to_events[participant]:
                        char_to_events[participant].append(event_id)
        print(f"[AGGREGATOR] Character-Event mapping: {len(char_to_events)} characters mapped")
    
    # Build existing character lookup
    existing_lookup = {}
    if existing_characters:
        for ec in existing_characters:
            ec_name = ec.get("name")
            if ec_name:
                existing_lookup[ec_name] = ec
                print(f"[AGGREGATOR] Found existing character: {ec_name} (id={ec.get('id')})")
    
    # Get all unique character names
    all_raw_names = set()
    all_raw_names.update(identity.keys())
    all_raw_names.update(appearance.keys())
    all_raw_names.update(personality.keys())
    all_raw_names.update(relations.keys())
    all_raw_names.update(personality.keys())
    all_raw_names.update(relations.keys())
    # Removed: dialogue_mood keys update
    
    # === DEDUPLICATION: Build canonical name mapping ===
    # This merges "Vera" and "베라" into a single character
    name_merge_map = build_name_merge_map(all_raw_names, dynamic_mapping)
    canonical_names = set(name_merge_map.values())
    
    print(f"[AGGREGATOR] Raw names: {all_raw_names}")
    print(f"[AGGREGATOR] Canonical names: {canonical_names}")
    
    characters = []
    
    print(f"[AGGREGATOR] Raw keys - Identity: {list(identity.keys())}")
    print(f"[AGGREGATOR] Raw keys - Appearance: {list(appearance.keys())}")
    print(f"[AGGREGATOR] Raw keys - Personality: {list(personality.keys())}")
    print(f"[AGGREGATOR] Raw keys - Relations: {list(relations.keys())}")
    # Removed: Dialogue keys print

    # === Pre-process Identity: Check for existing characters in DB ===
    for canonical_name in canonical_names:
        # Find all variant names that map to this canonical name
        variant_names = [raw for raw, canon in name_merge_map.items() if canon == canonical_name]
        print(f"[AGGREGATOR] Processing '{canonical_name}' with variants: {variant_names}")
        
        # Check for existing character - reuse ID and role if available
        existing_char = existing_lookup.get(canonical_name)
        if existing_char:
            char_id = existing_char.get("id", f"char-{canonical_name}-{len(characters)+1:03d}")
            char_role = existing_char.get("role", "other")
            print(f"[AGGREGATOR] Reusing existing ID for '{canonical_name}': {char_id}")
        else:
            char_id = f"char-{canonical_name}-{len(characters)+1:03d}"
            char_role = None  # Will be set from id_data
        
        # === MERGE DATA FROM ALL VARIANTS ===
        # Collect data from all name variants (e.g., "Vera" and "베라")
        def get_merged_data(agent_dict: dict, agent_name: str = "unknown") -> dict:
            """Merge data from all variant names for this character."""
            merged = {}
            print(f"[AGGREGATOR] 🔍 get_merged_data({agent_name}) for '{canonical_name}' with variants: {variant_names}")
            for variant in variant_names:
                variant_data = agent_dict.get(variant, {})
                if variant_data:
                    print(f"[AGGREGATOR] 🔍   Found data for variant '{variant}': keys={list(variant_data.keys())}")
                    # Merge: non-empty values from variants override empty ones
                    for k, v in variant_data.items():
                        if v and (k not in merged or not merged[k]):
                            merged[k] = v
                else:
                    print(f"[AGGREGATOR] 🔍   No data for variant '{variant}' in {agent_name}")
            print(f"[AGGREGATOR] 🔍   Merged result for {agent_name}: keys={list(merged.keys())}")
            return merged
        
        # Merge source data using variants
        identity_data = get_merged_data(identity, "identity")
        appearance_data = get_merged_data(appearance, "appearance")
        personality_data = get_merged_data(personality, "personality")
        relations_data = get_merged_data(relations, "relations")
        # Removed: dialogue_mood data merge
        
        # Debug: Log relations data for each character
        rel_graph = relations_data.get("relations", [])
        print(f"[AGGREGATOR] {canonical_name}: rel_data keys={list(relations_data.keys())}, relations count={len(rel_graph)}")
        if rel_graph:
            print(f"[AGGREGATOR] 🔍 Sample relation: {rel_graph[0]}")
        
        
        # Use canonical name for the character
        name = canonical_name
        
        # Build FullCharacter structure with improvements
        # Role inference: ALWAYS run and override if strong evidence exists
        extracted_role = identity_data.get("role") or "other"
        
        # Always run context-based inference
        inferred_role = infer_role_from_context(name, relations_data, story_text or "")
        
        # Decide final role:
        # - If inference returns a result, use it (strong signal from relations)
        # - Otherwise use extracted role or existing_char role or fallback
        if inferred_role:
            final_role = inferred_role
            print(f"[AGGREGATOR] Role for '{name}': LLM='{extracted_role}' → Inferred='{inferred_role}'")
        else:
            final_role = extracted_role if extracted_role != "other" else (char_role or "other")
        
        # Relations - use data directly (no defaults needed)
        # 🐛 FIX: apply_safe_defaults({}, data) returns {} because it only iterates defaults.items()
        final_relations = relations_data
        
        # Removed: Dialogue & Mood
        # dialogue_config = apply_safe_defaults(dm_data.get("dialogue", {}), {})
        # current_mood = apply_safe_defaults(dm_data.get("current_mood", {}), {})
        
        full_char = {
            # === SEARCH INDEXING: Root-level fields ===
            "id": char_id,  # serialization_alias="_id" in schema
            "role": final_role,
            
            "profile": {
                "character_id": char_id,
                "name": name,
                "age": identity_data.get("age"),
                "gender": identity_data.get("gender"),
                "race": identity_data.get("race"),
                "mbti": None,
                # personality as object with core_traits, flaws, values
                "personality": {
                    "core_traits": personality_data.get("core_traits", []),
                    "flaws": personality_data.get("flaws", []),
                    "values": personality_data.get("values", []),
                },
                "backstory": identity_data.get("backstory"),
                # === FACTION: Use defaults (stats agent removed) ===
                "faction": {
                    "name": identity_data.get("faction") or None,  # Faction name from identity agent
                    "social": {
                        "rank": SAFE_DEFAULTS["faction"]["social"]["rank"],
                        "influence": SAFE_DEFAULTS["faction"]["social"]["influence"],
                        "faction_reputation": {},
                    }
                },
            },
            # Clean aliases: remove other character names that LLM incorrectly added
            "aliases": clean_character_aliases(identity_data.get("aliases", []), name, canonical_names),
            "status": identity_data.get("status", "alive"),
            "appearance": {
                "physique": appearance_data.get("physique", "unspecified"),
                "skin_tone": appearance_data.get("skin_tone", "unspecified"),
                "eyes": appearance_data.get("eyes", "unspecified"),
                "nose": appearance_data.get("nose", "unspecified"),
                "mouth": appearance_data.get("mouth", "unspecified"),
                "hair_style": appearance_data.get("hair_style", "unspecified"),
                "hair_color": appearance_data.get("hair_color", "unspecified"),
                "attire": appearance_data.get("attire", []),
                "expression": appearance_data.get("expression", "neutral"),
                "scars_tattoos": appearance_data.get("scars_tattoos", []),
                # Removed: cyberware, full_visual_prompt, hair_color_normalized, eye_color_normalized
                "style_context": {
                    "art_style": appearance_data.get("style_context", {}).get("art_style", "fantasy illustration"),
                    # Removed: rendering_engine
                },
            },
            # Removed: duplicate personality field (now in profile.personality)
            "relations": {
                "graph": final_relations.get("relations", []),
                "event_refs": char_to_events.get(name, []),  # Populated from events
            },
            # 🔍 DEBUG: Log what's being assigned to relations.graph
            # Note: This is after the object is created, so we log it separately

            # === Embedding for Neo4j Vector Search ===
            "embedding": await generate_character_embedding(
                name=name,
                traits=personality_data.get("core_traits", []),
                role=final_role
            ),
        }
        
        # 🔍 DEBUG: Log final relations.graph content
        final_graph = full_char.get("relations", {}).get("graph", [])
        final_event_refs = full_char.get("relations", {}).get("event_refs", [])
        print(f"[AGGREGATOR] 🔍 FINAL '{name}': relations.graph={len(final_graph)} items, event_refs={len(final_event_refs)} items")
        if final_graph:
            print(f"[AGGREGATOR] 🔍   Sample graph item: {final_graph[0]}")
        
        characters.append(full_char)
    
    print(f"[AGGREGATOR] merge_character_data created {len(characters)} characters: {[c.get('profile',{}).get('name','?') for c in characters]}")
    return characters


async def character_aggregator_node(state: dict) -> dict:
    """Aggregator Node - Merges all sub-agent results into FullCharacter list."""
    identity = state.get("char_identity") or {}
    appearance = state.get("char_appearance") or {}
    personality = state.get("char_personality") or {}
    relations = state.get("char_relations") or {}
    # Removed: dialogue_mood = state.get("char_dialogue_mood") or {}
    # Removed: stats = state.get("char_stats") or {}
    
    # Run aggregationg_characters from context if available (from message context)
    # OR directly from state (from graph initial state)
    existing_characters = state.get("existing_characters") or []
    if not existing_characters:
        context = state.get("context") or {}
        existing_characters = context.get("existing_characters") or []
    
    # Extract story_text for dynamic name mapping (Korean/English pairs)
    story_text = state.get("story_text") or state.get("content") or ""
    
    # Extract events for event_refs population
    extracted_events = state.get("extracted_events") or []
    
    # Run aggregation
    characters = await merge_character_data(
        identity, appearance, personality, relations,
        # Removed: dialogue_mood=dialogue_mood,
        existing_characters=existing_characters,
        story_text=story_text,
        extracted_events=extracted_events
    )
    
    # === FINAL FILTER: Remove items AND non-characters ===
    # Using the comprehensive NON_CHARACTER_KEYWORDS list from identity.py
    # This acts as the final gatekeeper against leakage from any agent
    
    # helper is imported from identity.py: is_likely_item(name) -> uses NON_CHARACTER_KEYWORDS
    
    original_count = len(characters)
    filtered_characters = []
    
    for char in characters:
        char_name = char.get("profile", {}).get("name", "") or ""
        
        # 1. Check if it's a non-character (item, place, generic descriptor)
        if is_likely_item(char_name):
            print(f"[AGGREGATOR] Filtered out non-character: '{char_name}'")
            continue
            
        # 2. Check for empty name
        if not char_name.strip():
            print(f"[AGGREGATOR] Filtered out empty name character")
            continue
            
        filtered_characters.append(char)
    
    if len(filtered_characters) < original_count:
        print(f"[AGGREGATOR] Filtered {original_count - len(filtered_characters)} non-character entries")
    
    # === SETTINGS AGGREGATION ===
    # Extract unique settings from events and character contexts
    extracted_settings = {}
    
    # 1. From Events
    events = state.get("extracted_events", [])
    for event in events:
        loc = event.get("location_ref")
        if loc and loc not in extracted_settings:
            extracted_settings[loc] = {
                "name": loc,
                "type": "location",
                "description": f"Extracted from event context: {event.get('description', '')[:50]}...",
                "source": "event_location_ref"
            }
            
    # No longer extract from character location_context (removed attribute)

    settings_list = list(extracted_settings.values())
    print(f"[AGGREGATOR] Aggregated {len(settings_list)} settings.")
    print(f"[AGGREGATOR] FINAL: returning {len(filtered_characters)} characters to state")

    return {
        "extracted_characters": filtered_characters,
        "extracted_settings": settings_list,
        "completed_agents": (state.get("completed_agents") or []) + ["aggregator"],
        "messages": [{
            "role": "aggregator",
            "content": f"Merged {len(filtered_characters)} characters and {len(settings_list)} settings"
        }]
    }
