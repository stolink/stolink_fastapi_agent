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
    existing_characters: list = None
) -> list[dict]:
    """Merge sub-agent results by character name into FullCharacter format.
    
    Args:
        Each dict is keyed by character name with that agent's extracted data.
        existing_characters: List of pre-existing character dicts from context (reuses their IDs).
    
    Returns:
        List of FullCharacter dicts with:
        - Null Safety: Game fields use safe defaults
        - relations.graph (not relations.relations)
        - event_refs (Event ID list)
        - Existing character IDs preserved
    """
    # Build existing character lookup
    existing_lookup = {}
    if existing_characters:
        for ec in existing_characters:
            ec_name = ec.get("name")
            if ec_name:
                existing_lookup[ec_name] = ec
                print(f"[AGGREGATOR] Found existing character: {ec_name} (id={ec.get('id')})")
    
    # Get all unique character names
    all_names = set()
    all_names.update(identity.keys())
    all_names.update(appearance.keys())
    all_names.update(personality.keys())
    all_names.update(relations.keys())
    all_names.update(dialogue_mood.keys())
    all_names.update(stats.keys())
    if inventory:
        all_names.update(inventory.keys())
    
    characters = []
    
    for name in all_names:
        # Check for existing character - reuse ID and role if available
        existing_char = existing_lookup.get(name)
        if existing_char:
            char_id = existing_char.get("id", f"char-{name}-{len(characters)+1:03d}")
            char_role = existing_char.get("role", "other")
            print(f"[AGGREGATOR] Reusing existing ID for '{name}': {char_id}")
        else:
            char_id = f"char-{name}-{len(characters)+1:03d}"
            char_role = None  # Will be set from id_data
        
        # Get data from each agent (default to empty dict if not found)
        id_data = identity.get(name, {})
        app_data = appearance.get(name, {})
        per_data = personality.get(name, {})
        rel_data = relations.get(name, {})
        dm_data = dialogue_mood.get(name, {})
        st_data = stats.get(name, {})
        inv_data = inventory.get(name, {}) if inventory else {}
        
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
        # Use role from: 1) id_data (extracted), 2) existing_char, 3) fallback to "other"
        final_role = id_data.get("role") or char_role or "other"
        
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
            "role": id_data.get("role", "other"),
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
                    "category": "UNSPECIFIED"
                }),
                "eye_color_normalized": app_data.get("eye_color_normalized", {
                    "description": "unspecified",
                    "hex_code": None,
                    "category": "UNSPECIFIED"
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
                "age_group": None,
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
    
    characters = merge_character_data(
        identity, appearance, personality, relations, dialogue_mood, stats, inventory,
        existing_characters=existing_characters
    )
    
    return {
        "extracted_characters": characters,
        "completed_agents": (state.get("completed_agents") or []) + ["aggregator"],
        "messages": [{
            "role": "aggregator",
            "content": f"Merged {len(characters)} characters from 7 sub-agents"
        }]
    }

