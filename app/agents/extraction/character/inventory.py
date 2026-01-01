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

import json
import re
from app.agents.llm import get_structured_llm, get_bedrock_llm


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
    item_id: Optional[str] = Field(None, description="Item ID")
    name: str = Field(..., description="Item name")
    # Removed: item_type
    quantity: int = Field(1, description="Number of items")
    
    # Rarity and Value - permissive types
    rarity: Optional[str] = Field("COMMON", description="COMMON/UNCOMMON/RARE/EPIC/LEGENDARY")
    estimated_value: Optional[int] = Field(None, description="Estimated gold value")
    
    # Equipment state
    equipped: bool = Field(False, description="Whether currently equipped")
    slot: Optional[str] = Field(None, description="Equipment slot")
    
    # Removed: stats
    
    description: Optional[str] = Field(None, description="Brief item description")
    
    @model_validator(mode='after')
    def infer_value(self):
        """Calculate estimated_value based on rarity."""
        if self.estimated_value is None:
            # Safer access to rarity
            rarity_val = self.rarity if self.rarity else "COMMON"
            # Basic fallback logic
            base_prices = BASE_PRICES.get(rarity_val, BASE_PRICES["COMMON"])
            self.estimated_value = base_prices.get("MISC", 5)
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

### CRITICAL: ITEM EXTRACTION RULES ###
⚠️ Extract ANY physical object that characters POSSESS, WEAR, USE, or CARRY.
⚠️ Items include: weapons, clothing, tech devices, implants, tools, accessories

### WHAT IS AN ITEM? ###
✅ Items: 검, 갑옷, 트렌치코트, 임플란트, 권총, 칩, 홀로그램 방패, 단검, 증강 의안
✅ Cyberpunk Items: 뇌 임플란트, 증강 의안, 기계 팔, 플라즈마 건, 메모리 칩
❌ NOT Items: 머리카락, 눈빛, 감정, 신체 부위(자연적인), 날씨, 장소

### LANGUAGE CONSISTENCY RULE ###
Output ALL text in the SAME language as the input.
If the story is in Korean, ALL item names must be in Korean.

### OWNERSHIP INFERENCE RULES ###
1. If a character WEARS clothing (코트, 슈트) → EQUIPPED
2. If a character HAS implants/enhancements → EQUIPPED  
3. If a character USES weapons → EQUIPPED
4. If a character CARRIES items → BAG
5. Example: "낡은 트렌치코트를 입은 진하" → 진하 has "트렌치코트" equipped
6. Example: "기계 팔을 가진 유민재" → 유민재 has "기계 팔" equipped

### OUTPUT EXAMPLE ###
{{
  "has_inventory_data": true,
  "characters": [
    {{
      "name": "진하",
      "equipped_items": [
        {{"name": "낡은 트렌치코트", "description": "오래된 탐정 코트", "rarity": "COMMON", "equipped": true}},
        {{"name": "리볼버", "description": "구식 38구경 권총", "rarity": "COMMON", "equipped": true}}
      ],
      "bag_items": [
        {{"name": "라이터", "description": "금속 지포 라이터", "rarity": "COMMON", "equipped": false}}
      ]
    }},
    {{
      "name": "세라",
      "equipped_items": [
        {{"name": "기계 팔", "description": "최신형 사이버네틱 의수", "rarity": "RARE", "equipped": true}},
        {{"name": "홀로그램 방패", "description": "손목 내장형 방어 장치", "rarity": "UNCOMMON", "equipped": true}}
      ],
      "bag_items": [
        {{"name": "메모리 칩", "description": "암호화된 데이터 칩", "rarity": "EPIC", "equipped": false}}
      ]
    }}
  ]
}}

### EXTRACTION PATTERN ###
Look for these patterns:
- "~을 입은/입고", "~을 쥔/잡은", "~이 있는"
- "그의/그녀의 ~", "~를 들고"
- Descriptions of cybernetic enhancements, weapons, clothing"""),
    ("human", """Story text:
{story_text}

Available Characters:
{character_list}

Extract ALL physical items (weapons, clothing, implants, devices, accessories) that characters possess.
IMPORTANT: If an item is mentioned near a character or being used by them, assume OWNERSHIP.""")
])


# === Node Function ===
async def inventory_extraction_node(state: dict) -> dict:
    """Inventory Agent - Extracts items and equipment using Raw LLM to avoid Pydantic validation issues."""
    
    # Use standard tier for speed/stability
    llm = get_bedrock_llm(tier="standard")
    chain = INVENTORY_EXTRACTION_PROMPT | llm
    
    # Get available characters from state
    identities = state.get("char_identity", {})
    character_names = list(identities.keys()) if identities else []
    char_list_str = ", ".join(character_names) if character_names else "Detect from text"
    
    print(f"[INVENTORY] Available characters: {char_list_str}")
    
    try:
        print("[INVENTORY] Invoking Raw LLM chain...")
        # Invoke and get AIMessage
        response = await chain.ainvoke({
            "story_text": state["content"],
            "character_list": char_list_str
        })
        
        # Parse JSON from content
        content = response.content
        # Remove potential markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
             content = content.split("```")[1].split("```")[0]
        
        content = content.strip()
        print(f"[INVENTORY] Raw response length: {len(content)}")
        
        try:
            import json
            data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"[INVENTORY] JSON Decode Error: {e}")
            print(f"[INVENTORY] Failed content snippet: {content[:100]}...")
            return {
                "char_inventory": {},
                "completed_agents": (state.get("completed_agents") or []) + ["inventory"],
                "errors": (state.get("errors") or []) + [f"Inventory JSON Error: {str(e)}"]
            }

        # Convert raw dict to expected structure if needed, or pass as is
        # Schema: {"characters": [{"name":..., "equipped_items": [], "bag_items": []}]}
        
        inventory_data = {}
        if isinstance(data, dict) and "characters" in data:
            for char in data["characters"]:
                char_name = char.get("name")
                if char_name:
                    # Validate/Clean items
                    char["equipped_items"] = char.get("equipped_items", [])
                    char["bag_items"] = char.get("bag_items", [])
                    inventory_data[char_name] = char
                    
                    # Quick log
                    e_count = len(char["equipped_items"])
                    b_count = len(char["bag_items"])
                    if e_count + b_count > 0:
                        print(f"[INVENTORY] Extracted for '{char_name}': {e_count} E, {b_count} B")

        has_data = len(inventory_data) > 0
        print(f"[INVENTORY] Total characters with inventory data: {len(inventory_data)}")
        
        return {
            "char_inventory": inventory_data,
            "completed_agents": (state.get("completed_agents") or []) + ["inventory"],
            "messages": [{"role": "inventory_agent", "content": f"Extracted inventory for {len(inventory_data)} characters"}]
        }
        
    except Exception as e:
        print(f"[INVENTORY] Critical Exception: {e}")
        import traceback
        traceback.print_exc()
        return {
            "char_inventory": {},
            "completed_agents": (state.get("completed_agents") or []) + ["inventory"],
            "errors": (state.get("errors") or []) + [f"Inventory Agent Failed: {str(e)}"]
        }
