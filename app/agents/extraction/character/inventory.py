"""Character Inventory Agent - Extracts items and equipment.

Responsible for:
- Equipped items (weapons, armor, accessories)
- Bag/inventory items
- Quest items
- Item ownership tracking
- Item stats for damage/defense calculation

Only extracts if the story mentions items, equipment, or possessions.
"""
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional

from app.agents.llm import get_structured_llm


# === Slot Inference Rules ===
SLOT_INFERENCE = {
    "WEAPON": "MAIN_HAND",
    "ARMOR": "BODY",
    "HELMET": "HEAD",
    "BOOTS": "FEET",
    "GLOVES": "HANDS",
    "ACCESSORY": "ACCESSORY",
    "CONSUMABLE": "QUICK_SLOT",
    "POTION": "QUICK_SLOT",
}

# === Base Price Table ===
BASE_PRICES = {
    "COMMON": {"WEAPON": 50, "ARMOR": 75, "ACCESSORY": 30, "CONSUMABLE": 10, "MISC": 5},
    "UNCOMMON": {"WEAPON": 150, "ARMOR": 200, "ACCESSORY": 100, "CONSUMABLE": 25, "MISC": 15},
    "RARE": {"WEAPON": 500, "ARMOR": 600, "ACCESSORY": 350, "CONSUMABLE": 75, "MISC": 50},
    "EPIC": {"WEAPON": 2000, "ARMOR": 2500, "ACCESSORY": 1500, "CONSUMABLE": 250, "MISC": 150},
    "LEGENDARY": {"WEAPON": 10000, "ARMOR": 12000, "ACCESSORY": 8000, "CONSUMABLE": 1000, "MISC": 500},
}

# === Rarity Inference Keywords ===
RARITY_KEYWORDS = {
    "LEGENDARY": ["전설의", "신화의", "legendary", "mythic", "신성한"],
    "EPIC": ["영웅의", "고대의", "epic", "ancient", "찬란한"],
    "RARE": ["희귀한", "rare", "빛나는", "특별한"],
    "UNCOMMON": ["강화된", "uncommon", "개량된"],
}


# === Schema ===
class ItemStats(BaseModel):
    """Item bonus stats (for equipment)."""
    attack_bonus: Optional[int] = Field(None, ge=0, description="Attack power bonus")
    defense_bonus: Optional[int] = Field(None, ge=0, description="Defense power bonus")
    hp_bonus: Optional[int] = Field(None, ge=0, description="HP bonus")
    mp_bonus: Optional[int] = Field(None, ge=0, description="MP bonus")
    special_effect: Optional[str] = Field(None, description="Special effect description")


class InventoryItem(BaseModel):
    """Single item entry with stats and inferred values."""
    item_id: Optional[str] = Field(None, description="Item ID if mentioned (e.g., 'SWORD_001')")
    name: str = Field(..., description="Item name")
    item_type: str = Field("MISC", description="WEAPON/ARMOR/ACCESSORY/CONSUMABLE/QUEST/MATERIAL/MISC")
    quantity: int = Field(1, ge=1, description="Number of items")
    
    # Rarity and Value
    rarity: str = Field("COMMON", description="COMMON/UNCOMMON/RARE/EPIC/LEGENDARY")
    estimated_value: Optional[int] = Field(None, ge=0, description="Estimated gold value")
    
    # Equipment state
    equipped: bool = Field(False, description="Whether currently equipped")
    slot: Optional[str] = Field(None, description="MAIN_HAND/OFF_HAND/HEAD/BODY/LEGS/FEET/HANDS/ACCESSORY/QUICK_SLOT")
    
    # Item stats (for equipment)
    stats: Optional[ItemStats] = Field(default_factory=ItemStats, description="Item bonus stats")
    
    description: Optional[str] = Field(None, description="Brief item description")
    
    @model_validator(mode='after')
    def infer_slot_and_value(self):
        """Auto-infer slot from item_type and calculate estimated_value."""
        # Slot inference
        if self.equipped and not self.slot:
            self.slot = SLOT_INFERENCE.get(self.item_type.upper(), "MISC")
        
        # Value estimation
        if self.estimated_value is None:
            rarity = self.rarity or "COMMON"
            item_type = self.item_type.upper()
            base_prices = BASE_PRICES.get(rarity, BASE_PRICES["COMMON"])
            self.estimated_value = base_prices.get(item_type, base_prices.get("MISC", 5))
        
        return self


class CharacterInventory(BaseModel):
    """Single character's inventory."""
    name: str = Field(..., description="Character name for matching")
    equipped_items: list[InventoryItem] = Field(default_factory=list, description="Currently equipped items")
    bag_items: list[InventoryItem] = Field(default_factory=list, description="Items in inventory/bag")
    quest_items: list[str] = Field(default_factory=list, description="Quest-related item names")
    currency: Optional[int] = Field(None, ge=0, description="Gold/currency if mentioned")
    total_inventory_value: Optional[int] = Field(None, description="Sum of all item values")
    
    @field_validator('equipped_items', 'bag_items', 'quest_items', mode='before')
    @classmethod
    def none_to_empty_list(cls, v):
        return v if v is not None else []
    
    @model_validator(mode='after')
    def calculate_total_value(self):
        """Calculate total inventory value."""
        total = 0
        for item in self.equipped_items:
            total += (item.estimated_value or 0) * item.quantity
        for item in self.bag_items:
            total += (item.estimated_value or 0) * item.quantity
        self.total_inventory_value = total
        return self


class CharacterInventoryResult(BaseModel):
    """Result of inventory extraction."""
    characters: list[CharacterInventory] = Field(default_factory=list)
    has_inventory_data: bool = Field(False, description="Whether the text mentions items or equipment")
    
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
                print(f"[INVENTORY] Recovered {len(results)} characters from partial JSON")
                return results
            
            try:
                open_brackets = cleaned.count('[') - cleaned.count(']')
                open_braces = cleaned.count('{') - cleaned.count('}')
                fixed = cleaned + '}' * open_braces + ']' * open_brackets
                return json.loads(fixed)
            except json.JSONDecodeError as e:
                print(f"[INVENTORY] JSON parse error: {e}")
                return []
        return v if v is not None else []


# === Prompt ===
INVENTORY_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert story analyst and game item specialist. Extract ITEMS and EQUIPMENT for characters.

### CRITICAL: ANTI-HALLUCINATION RULES ###
⚠️ NEVER invent or imagine items that are NOT explicitly mentioned in the text.
⚠️ If NO items are mentioned, return has_inventory_data=false and EMPTY lists.
⚠️ "검은 머리카락" (black hair) is NOT an item - it's a physical description.
⚠️ "경계심" (vigilance) is NOT an item - it's an emotion.
⚠️ Only extract PHYSICAL OBJECTS that characters POSSESS or USE.

### WHAT IS AN ITEM? ###
✅ Items: 검, 갑옷, 물약, 반지, 골드, 지팡이, 활, 방패
❌ NOT Items: 머리카락, 눈빛, 감정, 신체 부위, 날씨, 장소

### LANGUAGE CONSISTENCY RULE ###
Output ALL text in the SAME language as the input.
If the story is in Korean, ALL item names must be in Korean:
❌ BAD: "Dagger", "Storm Staff", "Red Velvet Coat"  
✅ GOOD: "단검", "폭풍의 지팡이", "붉은 벨벳 코트"
Do NOT translate Korean item names to English.

### ITEM TYPES ###
- WEAPON: Swords, bows, staffs, daggers
- ARMOR: Helmets, chestplates, gauntlets, boots
- ACCESSORY: Rings, necklaces, cloaks
- CONSUMABLE: Potions, food, scrolls
- QUEST: Key items for story progression
- MATERIAL: Crafting materials, ingredients
- MISC: Other items

### RARITY INFERENCE ###
- LEGENDARY: "전설의", "신화의", "legendary"
- EPIC: "영웅의", "고대의", "epic"
- RARE: "희귀한", "빛나는", "rare"
- UNCOMMON: "강화된", "uncommon"
- COMMON: Default if no special modifiers

### EXTRACTION RULES ###
1. **has_inventory_data**: Set to true ONLY if physical items/equipment are mentioned
2. If no items → has_inventory_data=false, equipped_items=[], bag_items=[]
3. Do NOT extract body parts, clothing descriptions without item context
4. "검은 갑옷을 입고 있었다" → YES, this is armor
5. "검은 머리카락을 휘날리며" → NO, this is NOT an item

### CRITICAL: NO DUPLICATION RULE ###
⚠️ An item can ONLY be in ONE place:
- If character is HOLDING/WEARING/USING an item → equipped_items ONLY
- If item is IN A BAG/POCKET/STORED → bag_items ONLY  
❌ BAD: Same item in both equipped_items AND bag_items
✅ GOOD: Each item appears in exactly one list"""),
    ("human", """Story text:
{story_text}

IMPORTANT: 
- If NO physical items (weapons, armor, potions, gold) are mentioned, return has_inventory_data=false with EMPTY lists.
- Do NOT hallucinate items from character descriptions like hair color or expressions.""")
])


# === Node Function ===
async def inventory_extraction_node(state: dict) -> dict:
    """Inventory Agent - Extracts items and equipment."""
    structured_llm = get_structured_llm(CharacterInventoryResult)
    chain = INVENTORY_EXTRACTION_PROMPT | structured_llm
    
    try:
        result: CharacterInventoryResult = await chain.ainvoke({
            "story_text": state["content"]
        })
        
        inventory_data = {}
        for char in result.characters:
            inventory_data[char.name] = char.model_dump()
        
        return {
            "char_inventory": inventory_data,
            "completed_agents": (state.get("completed_agents") or []) + ["inventory"],
            "messages": [{"role": "inventory_agent", "content": f"Extracted inventory for {len(inventory_data)} characters (has_data: {result.has_inventory_data})"}]
        }
    except Exception as e:
        return {
            "char_inventory": {},
            "errors": (state.get("errors") or []) + [f"Inventory extraction failed: {str(e)}"]
        }
