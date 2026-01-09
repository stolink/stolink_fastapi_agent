"""Event Extraction Agent - with Structured Output.

Role: "Scene Director" - Manages WHO, WHERE, WHAT HAPPENED.
Key: Focus on REFERENCES (to characters and settings) and VISUAL COMPOSITION.

Uses with_structured_output() for:
- Guaranteed valid JSON
- Pydantic schema validation
- No manual parsing required
"""

import json
from langchain_core.prompts import ChatPromptTemplate

from app.agents.llm import get_structured_llm, safe_ainvoke
from app.schemas.events import EventExtractionResult


# === Embedding Generation ===
from app.services.embedding_service import get_embedding_service

async def generate_event_embeddings_batch(events: list[dict]) -> None:
    """Generate embeddings for a batch of events using Gemini (3072 dim).
    
    Updates the 'embedding' field in each event dictionary in-place.
    """
    if not events:
        return

    service = get_embedding_service()
    texts = []
    
    for event in events:
        narrative = event.get("narrative_summary", "")
        participants = event.get("participants", [])
        participants_str = ", ".join(participants[:5]) if participants else ""
        text_to_embed = f"{narrative} (Participants: {participants_str})"
        texts.append(text_to_embed)
    
    try:
        # Use batch generation with high concurrency
        embeddings = await service.generate_embeddings_batch(texts)
        
        for i, embedding in enumerate(embeddings):
            events[i]["embedding"] = embedding
            
    except Exception as e:
        print(f"[EVENT] Batch embedding generation failed: {e}")
        # Initialize empty embedding on failure to prevent DB errors
        for event in events:
            if "embedding" not in event:
                event["embedding"] = []


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

=== LANGUAGE CONSISTENCY RULE ===
**CRITICAL**: Output ALL text content in the SAME LANGUAGE as the input.
- If the input text is in Korean (한국어), ALL descriptions MUST be in Korean.
- If the input text is in English, all descriptions must be in English.
- Never mix languages.

Your goal is to capture the DRAMA and ACTION of the scene."""),
    ("human", """Text to analyze:
{story_text}

=== GUIDELINE: USE THESE NAMES ===

Available Characters (from Character Agent) - MUST use EXACT names:
{available_characters}

Available Locations (from Setting Agent) - MUST use EXACT names:
{available_settings}

=== RELEVANT PAST EVENTS (for causality/continuity) ===
{existing_events}

RULES:
1. participants: ONLY use names from "Available Characters" list above
2. location_ref: ONLY use names from "Available Locations" list above
3. visual_scene: Action and composition focus.
4. description: MUST provide detailed description for each event
5. Consider PAST EVENTS above when determining prev_event_id and causal relationships

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
    structured_llm = get_structured_llm(EventExtractionResult, tier="advanced")
    
    conflicts = state.get("consistency_report", {}).get("conflicts", [])
    retry_count = state.get("retry_count", 0)
    previous_events = state.get("extracted_events", [])
    
    # Get available characters and settings for reference matching
    # Support both legacy (c["name"]) and FullCharacter (c["profile"]["name"]) formats
    characters = state.get("extracted_characters", [])
    settings = state.get("extracted_settings", [])
    
    available_characters = []
    
    for c in characters:
        # Extract Name
        name = c.get("name") or (c.get("profile", {}) or {}).get("name")
        if name:
            available_characters.append(name)
    
    available_settings = [s.get("name", "") for s in settings if s.get("name")]
    
    print(f"[EVENT] Available characters: {available_characters}")
    print(f"[EVENT] Available settings: {available_settings}")
    
    is_re_extraction = retry_count > 0 and conflicts and previous_events
    
    # === Semantic Chunking Logic ===
    from app.services.chunking_service import ChunkingService
    from app.services.embedding_service import get_embedding_service
    
    content = state["content"]
    all_events = []
    
    # If content is large (> 4000 chars), use semantic chunking
    if len(content) > 4000 and not is_re_extraction:
        print(f"[EVENT] Content length {len(content)} > 4000. Using Semantic Chunking.")
        try:
            emb_service = get_embedding_service()
            chunker = ChunkingService(emb_service)
            sections = await chunker.create_semantic_sections(content)
            
            print(f"[EVENT] Split into {len(sections)} semantic sections.")
            
            event_id_counter = 1
            
            for i, section in enumerate(sections):
                print(f"[EVENT] Processing Section {i+1}/{len(sections)} ({len(section['content'])} chars)")
                
                # CRITICAL: Retrieve relevant past events via RAG for this section
                existing_events_text = ""
                try:
                    from app.services.rag_service import get_rag_service
                    rag_service = get_rag_service()
                    
                    # Add previously extracted events in this pipeline run to RAG
                    # (In a streaming architecture, we would add them as they are extracted)
                    # Here we simply ensure we are querying against what we have so far
                    # Note: Ideally, we persist events to RAG immediately after extraction.
                    # For now, we will just query whatever is in 'existing_events' from state.
                    
                    # Query based on current section content (first 500 chars)
                    query = section["content"][:500]
                    # We might need to access global state or a service that has all prior events
                    # In this local loop, 'all_events' grows. We haven't indexed 'all_events' into RAG yet.
                    # This is a limitation of the current synchronous loop.
                    # Improvement: Index 'all_events' into a temporary RAG store as we go.
                    
                    # For this implementation, we will query 'existing_events' passed from previous phases/chapters
                    if state.get("existing_events"):
                         rag_service.add_events(state.get("existing_events"))
                         relevant_events = await rag_service.retrieve_relevant_events(query, top_k=5)
                         
                         if relevant_events:
                             existing_events_text = "\n".join([
                                 f"- [{evt.get('event_id')}] {evt.get('summary') or evt.get('description')}" 
                                 for evt in relevant_events
                             ])
                         else:
                             existing_events_text = "No relevant past events found."
                    else:
                         existing_events_text = "No existing events found."
                         
                except Exception as e:
                    print(f"[EVENT] RAG lookup failed: {e}")
                    existing_events_text = "RAG Error."

                # Chain prompt for each section
                chain = EVENT_EXTRACTION_PROMPT | structured_llm
                result: EventExtractionResult = await safe_ainvoke(chain, {
                    "story_text": section["content"],
                    "available_characters": str(available_characters),
                    "available_settings": str(available_settings),
                    "existing_events": existing_events_text # Add this to prompt
                })
                
                # Update event IDs to be sequential across sections
                section_events = []
                for evt in result.events:
                    # Overwrite ID with global counter
                    evt.event_id = f"E{event_id_counter:03d}"
                    event_id_counter += 1
                    
                    # Link to previous event if strictly sequential
                    if not evt.prev_event_id and len(all_events) > 0:
                         evt.prev_event_id = all_events[-1]["event_id"]
                         
                    section_events.append(evt.model_dump())
                    
                all_events.extend(section_events)
                
        except Exception as e:
            print(f"[EVENT] Chunking failed: {e}. Falling back to full text.")
            # Fallback to normal processing below
            all_events = []

    try:
        if not all_events: # If chunking skipped or failed
            if is_re_extraction:
                print(f"[EVENT] Re-extracting with {len(conflicts)} conflicts as feedback")
                print(f"[EVENT] Re-extracting with {len(conflicts)} conflicts as feedback")
                chain = EVENT_RE_EXTRACTION_PROMPT | structured_llm
                result: EventExtractionResult = await safe_ainvoke(chain, {
                    "story_text": state["content"],
                    "available_characters": str(available_characters),
                    "available_settings": str(available_settings),
                    "conflicts": str(conflicts),
                    "previous_extraction": str(previous_events)
                })
            else:
                chain = EVENT_EXTRACTION_PROMPT | structured_llm
                # Get existing events for context (if any)
                existing_events_list = state.get("existing_events", [])
                existing_events_text = "\n".join([
                    f"- [{evt.get('event_id', 'E?')}] {evt.get('summary') or evt.get('description', '')}"
                    for evt in existing_events_list[:10]  # Limit to 10 for token efficiency
                ]) if existing_events_list else "No prior events."
                
                result: EventExtractionResult = await safe_ainvoke(chain, {
                    "story_text": state["content"],
                    "available_characters": str(available_characters),
                    "available_settings": str(available_settings),
                    "existing_events": existing_events_text
                })
            all_events = [e.model_dump() for e in result.events]
        
        # === Generate embeddings for each event ===
        print(f"[EVENT] Generating embeddings for {len(all_events)} events...")
        await generate_event_embeddings_batch(all_events)
        
        # Validate and log
        for event in all_events:
            participants = event.get("participants", [])
            location = event.get("location_ref", "")
            # Log any mismatches for debugging
            for p in participants:
                if p not in available_characters and available_characters:
                    print(f"[EVENT] Warning: participant '{p}' not in available_characters")
            if location and location not in available_settings and available_settings:
                # Fuzzy matching warning could go here
                pass
        
        return {
            "extracted_events": all_events,
            "messages": [
                {"role": "event_agent", 
                 "content": f"{'Re-' if is_re_extraction else ''}Extracted {len(all_events)} events with embeddings"}
            ]
        }
    except Exception as e:
        print(f"[EVENT] Extraction failed: {e}")
        return {
            "extracted_events": previous_events or [],
            "errors": [f"Event extraction failed: {str(e)}"],
            "partial_failure": True
        }

