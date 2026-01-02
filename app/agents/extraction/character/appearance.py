"""Character Appearance Agent - Extracts visual/physical information.

Production Level Features:
- Null Fallback: Replace null with "unspecified" or role-based defaults
- Color Normalization: Natural language → structured color data (hex, category)
- Prompt Aggregation: Generate full_visual_prompt for Image AI
- Style Context: art_style, rendering_engine for consistent generation

For image generation AI systems (DALL-E 3, Stable Diffusion, Midjourney).
"""
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from app.agents.llm import get_structured_llm


# === Color Mapping ===
COLOR_MAP = {
    # Korean → English + Hex
    "검은": {"en": "black", "hex": "#000000", "category": "black"},
    "검정": {"en": "black", "hex": "#000000", "category": "black"},
    "흰": {"en": "white", "hex": "#FFFFFF", "category": "white"},
    "하얀": {"en": "white", "hex": "#FFFFFF", "category": "white"},
    "금색": {"en": "gold", "hex": "#FFD700", "category": "blonde"},
    "금발": {"en": "blonde", "hex": "#FAD02E", "category": "blonde"},
    "갈색": {"en": "brown", "hex": "#8B4513", "category": "brown"},
    "밤색": {"en": "brown", "hex": "#5C4033", "category": "brown"},
    "빨간": {"en": "red", "hex": "#DC143C", "category": "red"},
    "붉은": {"en": "red", "hex": "#B22222", "category": "red"},
    "파란": {"en": "blue", "hex": "#1E90FF", "category": "blue"},
    "푸른": {"en": "blue", "hex": "#4169E1", "category": "blue"},
    "초록": {"en": "green", "hex": "#228B22", "category": "green"},
    "녹색": {"en": "green", "hex": "#2E8B57", "category": "green"},
    "회색": {"en": "gray", "hex": "#808080", "category": "gray"},
    "은색": {"en": "silver", "hex": "#C0C0C0", "category": "silver"},
    "은빛": {"en": "silver", "hex": "#C0C0C0", "category": "silver"},
    "보라": {"en": "purple", "hex": "#800080", "category": "purple"},
    "자주": {"en": "purple", "hex": "#8B008B", "category": "purple"},
    "주황": {"en": "orange", "hex": "#FF8C00", "category": "orange"},
    "노란": {"en": "yellow", "hex": "#FFD700", "category": "yellow"},
    "분홍": {"en": "pink", "hex": "#FF69B4", "category": "pink"},
    # English colors
    "black": {"en": "black", "hex": "#000000", "category": "black"},
    "white": {"en": "white", "hex": "#FFFFFF", "category": "white"},
    "brown": {"en": "brown", "hex": "#8B4513", "category": "brown"},
    "blonde": {"en": "blonde", "hex": "#FAD02E", "category": "blonde"},
    "red": {"en": "red", "hex": "#DC143C", "category": "red"},
    "blue": {"en": "blue", "hex": "#1E90FF", "category": "blue"},
    "green": {"en": "green", "hex": "#228B22", "category": "green"},
    "gray": {"en": "gray", "hex": "#808080", "category": "gray"},
    "grey": {"en": "gray", "hex": "#808080", "category": "gray"},
    "silver": {"en": "silver", "hex": "#C0C0C0", "category": "silver"},
}

# Role-based default appearances
ROLE_DEFAULTS = {
    "protagonist": {
        "physique": "athletic",
        "skin_tone": "fair",
        "expression": "determined",
    },
    "antagonist": {
        "physique": "imposing",
        "skin_tone": "pale",
        "expression": "cold",
    },
    "supporting": {
        "physique": "average",
        "skin_tone": "medium",
        "expression": "neutral",
    },
    "default": {
        "physique": "average",
        "skin_tone": "unspecified",
        "expression": "neutral",
    },
}


def normalize_color(color_text: Optional[str]) -> dict:
    """Convert natural language color to structured data."""
    if not color_text:
        return {"description": "unspecified", "hex_code": None, "category": "unspecified"}
    
    color_lower = color_text.lower()
    
    # Find matching color
    for key, value in COLOR_MAP.items():
        if key in color_lower:
            return {
                "description": color_text,
                "hex_code": value["hex"],
                "category": value["category"],
            }
    
    # No match - keep original description
    return {"description": color_text, "hex_code": None, "category": "other"}


def apply_fallback_defaults(
    data: dict, 
    role: str = "default"
) -> dict:
    """Apply fallback defaults for null values based on character role."""
    defaults = ROLE_DEFAULTS.get(role, ROLE_DEFAULTS["default"])
    
    result = dict(data)
    
    # Apply defaults for key visual fields
    if not result.get("physique"):
        result["physique"] = defaults.get("physique", "average")
    if not result.get("skin_tone"):
        result["skin_tone"] = defaults.get("skin_tone", "unspecified")
    if not result.get("expression"):
        result["expression"] = defaults.get("expression", "neutral")
    
    # For other fields, use "unspecified" instead of null
    for field in ["eyes", "nose", "mouth", "hair_style", "hair_color"]:
        if not result.get(field):
            result[field] = "unspecified"
    
    return result


def generate_visual_prompt(data: dict, style: str = "fantasy illustration") -> str:
    """Generate a complete visual prompt for Image AI."""
    parts = []
    
    # Gender/Age hint from name patterns (can be enhanced)
    name = data.get("name", "")
    
    # Build prompt parts
    if data.get("physique") and data["physique"] != "unspecified":
        parts.append(data["physique"])
    
    if data.get("skin_tone") and data["skin_tone"] != "unspecified":
        parts.append(f"{data['skin_tone']} skin")
    
    if data.get("hair_color") and data["hair_color"] != "unspecified":
        color = data["hair_color"]
        if isinstance(color, dict):
            color = color.get("description", "")
        parts.append(f"{color} hair")
    
    if data.get("hair_style") and data["hair_style"] != "unspecified":
        parts.append(data["hair_style"])
    
    if data.get("eyes") and data["eyes"] != "unspecified":
        parts.append(f"{data['eyes']} eyes")
    
    if data.get("expression") and data["expression"] != "unspecified":
        parts.append(f"{data['expression']} expression")
    
    # Attire
    for item in data.get("attire", []):
        if item:
            parts.append(item)
    
    # Scars/tattoos
    for mark in data.get("scars_tattoos", []):
        if mark:
            parts.append(mark)
    
    # Cyberware (for sci-fi)
    for cyber in data.get("cyberware", []):
        if cyber:
            parts.append(cyber)
    
    # Combine with style
    prompt = ", ".join(parts) if parts else "character portrait"
    return f"{prompt}, {style}"


# === Schema ===
class NormalizedColor(BaseModel):
    """Structured color data for rendering engines."""
    description: str = Field("unspecified", description="Original color description")
    hex_code: Optional[str] = Field(None, description="Hex color code (#RRGGBB)")
    category: str = Field("UNSPECIFIED", description="Color category (BLACK, BROWN, etc.)")


class CharacterAppearance(BaseModel):
    """Single character appearance information."""
    name: str = Field(..., description="Character name for matching")
    physique: Optional[str] = Field(None, description="Body type (muscular, slender, average)")
    skin_tone: Optional[str] = Field(None, description="Skin color/tone")
    eyes: Optional[str] = Field(None, description="Eye description (color, shape)")
    nose: Optional[str] = Field(None, description="Nose description")
    mouth: Optional[str] = Field(None, description="Mouth/lips description")
    hair_style: Optional[str] = Field(None, description="Hairstyle (long, short, braided)")
    hair_color: Optional[str] = Field(None, description="Hair color")
    attire: list[str] = Field(default_factory=list, description="Clothing/equipment list")
    expression: Optional[str] = Field(None, description="Default facial expression")
    scars_tattoos: list[str] = Field(default_factory=list, description="Scars, tattoos, birthmarks")
    cyberware: list[str] = Field(default_factory=list, description="Cybernetic enhancements")
    
    # Validator to handle None -> empty list
    
    @field_validator('attire', 'scars_tattoos', 'cyberware', mode='before')
    @classmethod
    def none_to_empty_list(cls, v):
        """Convert None to empty list for list fields."""
        return v if v is not None else []


class CharacterAppearanceResult(BaseModel):
    """Result of appearance extraction."""
    characters: list[CharacterAppearance] = Field(default_factory=list)


# === Prompt ===
APPEARANCE_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert story analyst. Extract VISUAL/PHYSICAL APPEARANCE for ALL characters.

### LANGUAGE CONSISTENCY RULE ###
Output ALL text in the SAME language as the input.
If the story is in Korean, all values must be in Korean.

### CRITICAL: NAME EXTRACTION RULE ###
When a character is introduced as "베라(Vera)" or "리안(Lian)", use ONLY the Korean name.
The English in parentheses is just a transliteration hint - DO NOT use it.
❌ BAD: "name": "Vera", "name": "Lian", "name": "Tio"
✅ GOOD: "name": "베라", "name": "리안", "name": "티오"

### EXTRACTION FOCUS ###
Extract ONLY visual appearance details for image generation:
- physique: Body type (muscular, slender, average)
- skin_tone: Skin color if mentioned
- eyes: Eye color, shape, characteristics, AND any eye coverings (e.g., "black eyepatch on right eye", "검은 안대")
- nose: Nose description
- mouth: Mouth/lips description
- hair_style: Long, short, braided, etc.
- hair_color: Hair color
- attire: Clothing, armor, weapons held
- expression: Default facial expression
- scars_tattoos: Visible marks, eyepatches, face masks, bandages - ANY notable face/body features
- cyberware: Cybernetic parts (if sci-fi)

### IMPORTANT: FACE ACCESSORIES ###
Face accessories like eyepatches, masks, bandages should be captured:
- "오른쪽 눈에는 검은 안대" → eyes: "wearing black eyepatch on right eye"
- "얼굴에 흉터" → scars_tattoos: ["facial scar"]

### RULES ###
1. Focus ONLY on visual/physical traits
2. Do NOT include personality traits here
3. Leave fields as null if not mentioned (will be replaced by defaults)
4. Use descriptive terms suitable for image generation"""),
    ("human", """Story text:
{story_text}

Extract visual appearance for all characters.""")
])


# === Production-Ready Post-Processing ===
def post_process_appearance(
    raw_data: dict, 
    role: str = "default",
    art_style: str = "fantasy illustration",
    rendering_engine: Optional[str] = None,
) -> dict:
    """Apply production-level post-processing to appearance data.
    
    Features:
    1. Null Fallback with role-based defaults
    2. Color Normalization (natural language → hex)
    3. Full Visual Prompt generation
    4. Style Context metadata
    """
    # 1. Apply fallback defaults
    data = apply_fallback_defaults(raw_data, role)
    
    # 2. Normalize colors
    data["hair_color_normalized"] = normalize_color(data.get("hair_color"))
    data["eye_color_normalized"] = normalize_color(data.get("eyes"))
    
    # 3. Generate visual prompt
    data["full_visual_prompt"] = generate_visual_prompt(data, art_style)
    
    # 4. Add style context
    data["style_context"] = {
        "art_style": art_style,
        "rendering_engine": rendering_engine,
    }
    
    return data


# === Node Function ===
async def appearance_extraction_node(state: dict) -> dict:
    """Appearance Agent - Extracts visual character information.
    
    Production Features:
    - Null Fallback: replaces null with "unspecified" or role-based defaults
    - Color Normalization: natural language → structured color data
    - Prompt Aggregation: generates full_visual_prompt for Image AI
    """
    # Use standard tier for visual appearance extraction
    structured_llm = get_structured_llm(CharacterAppearanceResult, tier="standard")
    chain = APPEARANCE_EXTRACTION_PROMPT | structured_llm
    
    # Get art style from state or auto-detect from content
    art_style = state.get("art_style")
    if not art_style:
        # Default to a neutral, high-quality style if not specified
        art_style = "Digital Illustration, Concept Art"
    rendering_engine = state.get("rendering_engine")
    
    try:
        result: CharacterAppearanceResult = await chain.ainvoke({
            "story_text": state["content"]
        })
        
        appearance_data = {}
        for char in result.characters:
            raw_data = char.model_dump()
            
            # Get character role from identity data if available
            identity = state.get("char_identity", {}).get(char.name, {})
            role = identity.get("role", "default")
            
            # Apply production post-processing
            processed_data = post_process_appearance(
                raw_data, 
                role=role,
                art_style=art_style,
                rendering_engine=rendering_engine,
            )
            appearance_data[char.name] = processed_data
        
        return {
            "char_appearance": appearance_data,
            "completed_agents": (state.get("completed_agents") or []) + ["appearance"],
            "messages": [{
                "role": "appearance_agent", 
                "content": f"Extracted {len(appearance_data)} character appearances (production-ready)"
            }]
        }
    except Exception as e:
        return {
            "char_appearance": {},
            "errors": (state.get("errors") or []) + [f"Appearance extraction failed: {str(e)}"]
        }
