"""Event Extraction Agent - with Structured Output.

Role: "Scene Director" - Manages WHO, WHERE, WHAT HAPPENED.
Key: Focus on REFERENCES (to characters and settings) and VISUAL COMPOSITION.

Uses with_structured_output() for:
- Guaranteed valid JSON
- Pydantic schema validation
- No manual parsing required
"""
import boto3
import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_structured_llm
from app.schemas.events import EventExtractionResult


# === Embedding Generation ===
_bedrock_client = None

def get_bedrock_client():
    """Get or create Bedrock client singleton."""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
    return _bedrock_client


def generate_event_embedding(narrative_summary: str, participants: list) -> list[float]:
    """Generate embedding for event using AWS Bedrock Titan.
    
    Creates embedding from narrative_summary + participants for vector search.
    Returns empty list if generation fails (non-blocking).
    """
    try:
        # Build text to embed
        participants_str = ", ".join(participants[:5]) if participants else ""
        text_to_embed = f"{narrative_summary} (Participants: {participants_str})"
        
        client = get_bedrock_client()
        response = client.invoke_model(
            modelId='amazon.titan-embed-text-v1',
            body=json.dumps({"inputText": text_to_embed})
        )
        result = json.loads(response['body'].read())
        return result.get('embedding', [])
    except Exception as e:
        print(f"[EVENT] Embedding generation failed: {e}")
        return []  # Non-blocking - return empty list


EVENT_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a "Scene Director" / "Storyboard Artist".
Your job is to break down the story into SCENES and describe the COMPOSITION for each.

[Example 2: Use participant names as EXACT references]
❌ BAD:
  "participants": ["the protagonist", "the antagonist"]
  
✅ GOOD:
  "participants": ["서진", "이민호"]  // Exact names for Neo4j matching

[Example 3: location_ref should match Setting Agent's name]
❌ BAD:
  "location_ref": "A dark forest where trees are twisted"
  
✅ GOOD:
  "location_ref": "Dark Forest"  // Short name, matches Setting Agent

=== YOUR TASK ===
Extract events with TWO purposes:

1. **Neo4j Graph Edges**:
   - participants: Exact character names → Creates (Event)-[:INVOLVES]->(Character) edges
   - location_ref: Setting name → Creates (Event)-[:HAPPENS_AT]->(Location) edge
   - prev_event_id: Previous event ID → Creates timeline

2. **Narrative Context**:
   - narrative_summary: One-sentence summary
   - description: Detailed description (REQUIRED)
   - importance: 1-10 (use for filtering key events)

=== FIELD REQUIREMENTS ===
For each event, you MUST provide:
- event_id: Unique ID like "E001", "E002"
- event_type: action, dialogue, revelation, flashback, foreshadowing, confrontation, transition
- narrative_summary: Brief one-line summary
- description: Detailed event description (REQUIRED!)
- participants: List of exact character names
- location_ref: Short setting name
- prev_event_id: Previous event ID or null
- importance: 1-10

Your goal is to capture the DRAMA and ACTION of the scene."""),
    ("human", """Text to analyze:
{story_text}

=== GUIDELINE: USE THESE NAMES ===

Available Characters (from Character Agent) - MUST use EXACT names:
{available_characters}

Available Inventory (VISUAL CONTEXT):
{available_inventory}

Available Locations (from Setting Agent) - MUST use EXACT names:
{available_settings}

RULES:
1. participants: ONLY use names from "Available Characters" list above
2. location_ref: ONLY use names from "Available Locations" list above
3. visual_scene: Action and composition focus.
   - TIP: Use "Available Inventory" to describe held items precisely (e.g., "Silver Sword" instead of "sword")
4. description: MUST provide detailed description for each event

If a character or location is not in the list, use the closest match or exclude it.""")
])


EVENT_RE_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a Scene Director. Re-extract events with corrections based on feedback.

PREVIOUS CONFLICTS:
{conflicts}

=== CORRECTION RULES ===
1. Keep all valid events from previous extraction
2. Fix specific issues mentioned in conflicts
3. Ensure participants match exact character names
4. Ensure location_ref matches exact setting names
5. Ensure ALL events have a description field
6. Maintain timeline integrity (prev_event_id chain)

=== GUIDELINE ===
Focus on the action and drama of the story."""),
    ("human", """Original text:
{story_text}

Available Characters: {available_characters}
Available Inventory: {available_inventory}
Available Locations: {available_settings}

Previous extraction (contains errors):
{previous_extraction}

Re-extract with corrections.""")
])


async def event_extraction_node(state: dict) -> dict:
    """Event Extraction Agent node function - with Structured Output + Embedding.
    
    Uses with_structured_output() for guaranteed schema compliance.
    Generates embedding for each event for RAG-based consistency checking.
    """
    # Get LLM with structured output bound to schema
    structured_llm = get_structured_llm(EventExtractionResult, tier="standard")
    
    conflicts = state.get("consistency_report", {}).get("conflicts", [])
    retry_count = state.get("retry_count", 0)
    previous_events = state.get("extracted_events", [])
    
    # Get available characters and settings for reference matching
    # Support both legacy (c["name"]) and FullCharacter (c["profile"]["name"]) formats
    characters = state.get("extracted_characters", [])
    settings = state.get("extracted_settings", [])
    
    available_characters = []
    available_inventory = [] # Format: "Name: [Item1, Item2]"
    
    for c in characters:
        # Extract Name
        name = c.get("name") or (c.get("profile", {}) or {}).get("name")
        if name:
            available_characters.append(name)
            
            # Extract Inventory if available
            # Check various paths: c['inventory'], c['char_inventory'], or flat fields
            inv = c.get("inventory", {}) or c.get("char_inventory", {})
            items = []
            if isinstance(inv, dict):
                # Try 'equipped_items' or 'bag_items'
                items.extend(inv.get("equipped_items", []))
                items.extend(inv.get("bag_items", []))
                # Or generic 'items' list
                if not items and "items" in inv:
                    items = inv["items"]
            
            if items:
                # Cleanup simple strings
                clean_items = [i if isinstance(i, str) else str(i) for i in items]
                available_inventory.append(f"{name}: [{', '.join(clean_items)}]")
    
    inv_str = "\n".join(available_inventory) if available_inventory else "None"
    
    available_settings = [s.get("location_name") or s.get("name", "") for s in settings if s.get("location_name") or s.get("name")]
    
    print(f"[EVENT] Available characters: {available_characters}")
    print(f"[EVENT] Available inventory: {inv_str}")
    print(f"[EVENT] Available settings: {available_settings}")
    
    is_re_extraction = retry_count > 0 and conflicts and previous_events
    
    try:
        if is_re_extraction:
            print(f"[EVENT] Re-extracting with {len(conflicts)} conflicts as feedback")
            chain = EVENT_RE_EXTRACTION_PROMPT | structured_llm
            result: EventExtractionResult = await chain.ainvoke({
                "story_text": state["content"],
                "available_characters": str(available_characters),
                "available_inventory": inv_str,
                "available_settings": str(available_settings),
                "conflicts": str(conflicts),
                "previous_extraction": str(previous_events)
            })
        else:
            chain = EVENT_EXTRACTION_PROMPT | structured_llm
            result: EventExtractionResult = await chain.ainvoke({
                "story_text": state["content"],
                "available_characters": str(available_characters),
                "available_inventory": inv_str,
                "available_settings": str(available_settings)
            })
        
        # Result is already an EventExtractionResult Pydantic object
        events = [e.model_dump() for e in result.events]
        
        # === Generate embeddings for each event ===
        print(f"[EVENT] Generating embeddings for {len(events)} events...")
        for event in events:
            narrative = event.get("narrative_summary", "")
            participants = event.get("participants", [])
            event["embedding"] = generate_event_embedding(narrative, participants)
        
        # Validate and log
        for event in events:
            participants = event.get("participants", [])
            location = event.get("location_ref", "")
            # Log any mismatches for debugging
            for p in participants:
                if p not in available_characters and available_characters:
                    print(f"[EVENT] Warning: participant '{p}' not in available_characters")
            if location and location not in available_settings and available_settings:
                print(f"[EVENT] Warning: location_ref '{location}' not in available_settings")
        
        return {
            "extracted_events": events,
            "messages": [
                {"role": "event_agent", 
                 "content": f"{'Re-' if is_re_extraction else ''}Extracted {len(events)} events with embeddings"}
            ]
        }
    except Exception as e:
        print(f"[EVENT] Extraction failed: {e}")
        return {
            "extracted_events": previous_events or [],
            "errors": [f"Event extraction failed: {str(e)}"],
            "partial_failure": True
        }

