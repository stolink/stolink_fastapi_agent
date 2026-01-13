"""Character Team State - TypedDict for internal state management."""
from typing import TypedDict, Optional, Annotated
import operator


class CharacterTeamState(TypedDict, total=False):
    """Internal state for Character Team sub-agents.
    
    This state is used within the Character Team's internal graph.
    It's separate from the main pipeline state.
    """
    # Input from main pipeline
    content: str
    retry_count: int
    existing_characters: list  # For ID reuse
    
    # Sub-agent results (keyed by character name)
    char_identity: Optional[dict]        # {name: {profile, role, ...}}
    char_appearance: Optional[dict]      # {name: {physique, hair, ...}}
    char_personality: Optional[dict]     # {name: {core_traits, flaws, ...}}
    char_relations: Optional[dict]       # {name: {relations, ...}}
    
    # Final output
    extracted_characters: list
    
    # Internal tracking
    completed_agents: Annotated[list, operator.add]  # ["identity", "appearance", ...]
    errors: Annotated[list, operator.add]
    messages: Annotated[list, operator.add]
    
    # Routing control
    next: str
