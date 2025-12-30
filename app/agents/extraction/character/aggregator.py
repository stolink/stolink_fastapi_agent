"""Character Aggregator - Merges all sub-agent results into FullCharacter.

Takes results from all 7 sub-agents and combines them by character name
into the FullCharacter format expected by the main pipeline.

Sub-agents:
- Identity, Appearance, Personality, Relations, Dialogue/Mood, Stats, Inventory

Improvements:
- Null Safety: Game-related fields use safe defaults instead of null
- Naming: relations.graph (not relations.relations)
- Optimization: event_refs for Event IDs instead of full text
- Inventory: Equipped items and bag items from inventory agent
"""
from typing import Any

from app.schemas.character_full import FullCharacter, FullCharacterExtractionResult


# === Safe Defaults for Game Engine ===
# Applied when extracted values are null to prevent game engine errors
SAFE_DEFAULTS = {
    "combat": {
        # Base vs Total separation
        "base_attack": 10,
        "base_defense": 10,
        "total_attack": 10,
        "total_defense": 10,
        "source": "default",  # "extracted" for real data, "default" for fallback
        # Other combat stats
        "attack_range": 1.5,
        "crit_chance": 0.05,
        "attack_type": "MELEE",
        # Legacy fields for backward compatibility
        "hitbox_radius": 1.0,
        "mass": 70.0,
        "damage_multiplier": 1.0,
    },
    "social": {
        "rank": "COMMON",
        "influence": 0,
        "faction_reputation": {},
        "trade_unlocked": True,
    },
    "economy": {
        "gold": 0,
        "trade_status": "NORMAL",
    },
    "state": {
        "hp": 100,
        "hp_max": 100,
        "mp": 50,
        "mp_max": 50,
        "status_effects": [],
        "stamina": 100,
        "hunger": 100,
        "is_invincible": False,
    },
    "stats": {
        # Normalized field names (NOT str_, int_, etc.)
        "strength": 10,
        "dexterity": 10,
        "intelligence": 10,
        "constitution": 10,
        "level": 1,
        "exp": 0,
        "skills": [],
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
    
    for korean in korean_names:
        variants = korean_to_romanization_variants(korean)
        variants_lower = [v.lower() for v in variants]
        
        for english in english_names:
            english_lower = english.lower()
            if english_lower in variants_lower:
                matches[english] = korean
                matches[english.lower()] = korean
                matches[english.upper()] = korean
                print(f"[AGGREGATOR] Romanization match: '{english}' → '{korean}'")
    
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
    "adult": ["성인", "청년", "adult", "man", "woman"],
    "elderly": ["노인", "할아버지", "할머니", "elderly", "old man", "old woman", "늙은"],
}

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

def infer_age_group(name: str, appearance_data: dict, story_text: str = "") -> str | None:
    """Infer age_group from appearance descriptions or character-specific context.
    
    Returns: "child", "teen", "adult", "elderly", or None
    """
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
    canonical_names = set()
    
    for name in all_raw_names:
        canonical = normalize_character_name(name, full_mapping)
        merge_map[name] = canonical
        canonical_names.add(canonical)
    
    print(f"[AGGREGATOR] Name merge map: {len(all_raw_names)} raw → {len(canonical_names)} canonical")
    return merge_map



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


def merge_character_data(
    identity: dict,
    appearance: dict,
    personality: dict,
    relations: dict,
    dialogue_mood: dict,
    stats: dict,
    inventory: dict = None,
    existing_characters: list = None,
    story_text: str = None
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
    all_raw_names.update(dialogue_mood.keys())
    all_raw_names.update(stats.keys())
    if inventory:
        all_raw_names.update(inventory.keys())
    
    # === DEDUPLICATION: Build canonical name mapping ===
    # This merges "Vera" and "베라" into a single character
    name_merge_map = build_name_merge_map(all_raw_names, dynamic_mapping)
    canonical_names = set(name_merge_map.values())
    
    print(f"[AGGREGATOR] Raw names: {all_raw_names}")
    print(f"[AGGREGATOR] Canonical names: {canonical_names}")
    
    characters = []
    
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
        def get_merged_data(agent_dict: dict) -> dict:
            """Merge data from all variant names for this character."""
            merged = {}
            for variant in variant_names:
                variant_data = agent_dict.get(variant, {})
                if variant_data:
                    # Merge: non-empty values from variants override empty ones
                    for k, v in variant_data.items():
                        if v and (k not in merged or not merged[k]):
                            merged[k] = v
            return merged
        
        id_data = get_merged_data(identity)
        app_data = get_merged_data(appearance)
        per_data = get_merged_data(personality)
        rel_data = get_merged_data(relations)
        dm_data = get_merged_data(dialogue_mood)
        st_data = get_merged_data(stats)
        inv_data = get_merged_data(inventory) if inventory else {}
        
        # Use canonical name for the character
        name = canonical_name
        
        # === STATS AGGREGATION: Calculate item bonuses ===
        item_attack_bonus = 0
        item_defense_bonus = 0
        item_hp_bonus = 0
        
        for item in inv_data.get("equipped_items", []):
            item_stats = item.get("stats", {})
            if isinstance(item_stats, dict):
                item_attack_bonus += item_stats.get("attack_bonus", 0) or 0
                item_defense_bonus += item_stats.get("defense_bonus", 0) or 0
                item_hp_bonus += item_stats.get("hp_bonus", 0) or 0
        
        # Apply safe defaults first
        base_stats = apply_safe_defaults(st_data.get("stats", {}), SAFE_DEFAULTS["stats"])
        base_state = apply_safe_defaults(st_data.get("state", {}), SAFE_DEFAULTS["state"])
        base_combat = apply_safe_defaults(st_data.get("combat", {}), SAFE_DEFAULTS["combat"])
        
        # Calculate final stats with item bonuses
        final_attack = (base_combat.get("total_attack") or base_combat.get("base_attack", 10)) + item_attack_bonus
        final_defense = (base_combat.get("total_defense") or base_combat.get("base_defense", 10)) + item_defense_bonus
        final_hp_max = (base_state.get("hp_max", 100)) + item_hp_bonus
        
        # Build FullCharacter structure with improvements
        # Role inference: ALWAYS run and override if strong evidence exists
        extracted_role = id_data.get("role") or "other"
        
        # Always run context-based inference
        inferred_role = infer_role_from_context(name, rel_data, story_text or "")
        
        # Decide final role:
        # - If inference returns a result, use it (strong signal from relations)
        # - Otherwise use extracted role or existing_char role or fallback
        if inferred_role:
            final_role = inferred_role
            print(f"[AGGREGATOR] Role for '{name}': LLM='{extracted_role}' → Inferred='{inferred_role}'")
        else:
            final_role = extracted_role if extracted_role != "other" else (char_role or "other")
        
        full_char = {
            # === SEARCH INDEXING: Root-level fields for fast DB queries ===
            "_id": char_id,  # MongoDB-style ID (uses existing if available)
            "name": name,  # Hoisted for search
            "role": final_role,  # Hoisted for search
            "level": base_stats.get("level", 1),  # Hoisted for search
            "faction": id_data.get("faction"),  # Hoisted for search
            
            "profile": {
                "character_id": char_id,
                "name": name,
                "age": id_data.get("age"),
                "gender": id_data.get("gender"),
                "race": id_data.get("race"),
                "faction": id_data.get("faction"),
                "mbti": None,
                "personality": per_data.get("core_traits", []),
                "chapter_appearance": None,
                "backstory": id_data.get("backstory"),
            },
            "role": final_role,
            "aliases": id_data.get("aliases", []),
            "status": id_data.get("status", "alive"),
            "appearance": {
                "physique": app_data.get("physique", "unspecified"),
                "skin_tone": app_data.get("skin_tone", "unspecified"),
                "eyes": app_data.get("eyes", "unspecified"),
                "nose": app_data.get("nose", "unspecified"),
                "mouth": app_data.get("mouth", "unspecified"),
                "hair_style": app_data.get("hair_style", "unspecified"),
                "hair_color": app_data.get("hair_color", "unspecified"),
                "attire": app_data.get("attire", []),
                "expression": app_data.get("expression", "neutral"),
                "scars_tattoos": app_data.get("scars_tattoos", []),
                "cyberware": app_data.get("cyberware", []),
                # Production fields from Appearance Agent
                "hair_color_normalized": app_data.get("hair_color_normalized", {
                    "description": "unspecified",
                    "hex_code": None,
                    "category": "unspecified"
                }),
                "eye_color_normalized": app_data.get("eye_color_normalized", {
                    "description": "unspecified",
                    "hex_code": None,
                    "category": "unspecified"
                }),
                "full_visual_prompt": app_data.get("full_visual_prompt", ""),
                "style_context": app_data.get("style_context", {
                    "art_style": "fantasy illustration",
                    "rendering_engine": None
                }),
            },
            "personality": {
                "core_traits": per_data.get("core_traits", []),
                "flaws": per_data.get("flaws", []),
                "values": per_data.get("values", []),
            },
            "visual": {
                "appearance": [],
                "attire": app_data.get("attire", []),
                "age_group": infer_age_group(name, app_data, story_text or ""),
                "gender": id_data.get("gender"),
            },
            # FIX: relations.graph instead of relations.relations (naming duplication removed)
            "relations": {
                "graph": rel_data.get("relations", []),  # Changed from "relations" to "graph"
                "event_refs": rel_data.get("known_events", []),  # Changed to event_refs for optimization
                "location_context": rel_data.get("location_context"),
            },
            "current_mood": dm_data.get("current_mood", {
                "emotion": None,
                "intensity": 5,
                "trigger": None,
            }),
            "dialogue": dm_data.get("dialogue", {
                "tone": None,
                "catchphrases": [],
                "forbidden_topics": [],
                "secret_keys": [],
            }),
            # Base stats from Stats Agent
            "stats": base_stats,
            "state": base_state,
            "combat": base_combat,
            "social": apply_safe_defaults(st_data.get("social", {}), SAFE_DEFAULTS["social"]),
            "economy": apply_safe_defaults(st_data.get("economy", {}), SAFE_DEFAULTS["economy"]),
            
            # === FINAL STATS: Aggregated with item bonuses ===
            "final_stats": {
                "attack": final_attack,
                "defense": final_defense,
                "hp_max": final_hp_max,
                "details": {
                    "base_attack": base_combat.get("base_attack", 10),
                    "base_defense": base_combat.get("base_defense", 10),
                    "base_hp_max": base_state.get("hp_max", 100),
                    "item_attack_bonus": item_attack_bonus,
                    "item_defense_bonus": item_defense_bonus,
                    "item_hp_bonus": item_hp_bonus,
                }
            },
            
            # Inventory from Inventory Agent
            "inventory": {
                "equipped_items": inv_data.get("equipped_items", []),
                "bag_items": inv_data.get("bag_items", []),
                "quest_items": inv_data.get("quest_items", []),
            },
            "meta": {
                "created_at": None,
                "updated_at": None,
                "is_active": True,
                "data_version": "1.1.0",  # Version bump for new structure
                "lock_version": 0,
                "plot_armor": False,
                "is_player": False,
            },
            "extraction_notes": None,
        }
        
        characters.append(full_char)
    
    return characters


async def character_aggregator_node(state: dict) -> dict:
    """Aggregator Node - Merges all sub-agent results into FullCharacter list."""
    identity = state.get("char_identity") or {}
    appearance = state.get("char_appearance") or {}
    personality = state.get("char_personality") or {}
    relations = state.get("char_relations") or {}
    dialogue_mood = state.get("char_dialogue_mood") or {}
    stats = state.get("char_stats") or {}
    inventory = state.get("char_inventory") or {}
    
    # Extract existing_characters from context if available
    context = state.get("context") or {}
    existing_characters = context.get("existing_characters") or []
    
    # Extract story_text for dynamic name mapping (Korean/English pairs)
    story_text = state.get("story_text") or state.get("content") or ""
    
    characters = merge_character_data(
        identity, appearance, personality, relations, dialogue_mood, stats, inventory,
        existing_characters=existing_characters,
        story_text=story_text
    )
    
    return {
        "extracted_characters": characters,
        "completed_agents": (state.get("completed_agents") or []) + ["aggregator"],
        "messages": [{
            "role": "aggregator",
            "content": f"Merged {len(characters)} characters from 7 sub-agents"
        }]
    }

