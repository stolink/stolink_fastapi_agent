"""Character Team Supervisor - Routes sub-agents within the Character Team.

This is the internal supervisor for the Character Team.
It manages the execution of 7 sub-agents using a 2-phase high-performance strategy:
1. Identity Phase (Sequential): Extract core identity provided first.
2. Parallel Phase (Parallel): Execute other agents concurrently based on Identity analysis.
"""
import asyncio
from typing import Literal
from langgraph.graph import StateGraph, END

from .state import CharacterTeamState
from .identity import identity_extraction_node
from .appearance import appearance_extraction_node
from .personality import personality_extraction_node
from .relations import relations_extraction_node
from .dialogue_mood import dialogue_mood_extraction_node
from .stats import stats_extraction_node
from .inventory import inventory_extraction_node
from .aggregator import character_aggregator_node


# Agents for Parallel Phase
PARALLEL_AGENTS = {
    "appearance": appearance_extraction_node,
    "personality": personality_extraction_node,
    "relations": relations_extraction_node,
    "dialogue_mood": dialogue_mood_extraction_node,
    "stats": stats_extraction_node,
    "inventory": inventory_extraction_node,
}


async def parallel_extraction_node(state: CharacterTeamState) -> dict:
    """Execute selected agents in parallel with partial failure tolerance.
    
    This node implements:
    1. Adaptive Analysis: Selects agents based on character role (from state).
    2. Parallel Execution: Runs agents concurrently using asyncio.gather.
    3. Partial Failure Tolerance: One failure doesn't stop others.
    """
    # 1. Adaptive Analysis (Filter agents based on role)
    # Get extracted identity to determine role
    identities = state.get("char_identity", {})
    # Simple heuristic: If "Extra" is detected in any character role, we might skip some agents.
    # For now, we enable full scan for safety, but structure allows filtering.
    # Future optimization: Inspect `identities` and reduce `target_agents` list.
    
    target_agents = list(PARALLEL_AGENTS.keys())
    
    # 2. Context Optimization (Optional)
    # We could filter `state["content"]` here for specific agents.
    
    print(f"[Character Team] Starting Parallel Phase for agents: {target_agents}")
    
    # helper wrapper to catch exceptions for partial failure tolerance
    async def safe_execute(agent_name, agent_func):
        try:
            return await agent_func(state)
        except Exception as e:
            print(f"⚠️ [Character Team] Agent '{agent_name}' failed: {e}")
            return {"errors": [f"Agent {agent_name} failed: {str(e)}"]}

    # Create tasks
    tasks = [
        safe_execute(name, PARALLEL_AGENTS[name])
        for name in target_agents
    ]
    
    # 3. Parallel Execution
    results = await asyncio.gather(*tasks)
    
    # Merge results
    updates = {
        "completed_agents": target_agents,
        "messages": [],
        "errors": []
    }
    
    for res in results:
        for key, val in res.items():
            if key == "messages":
                updates["messages"].extend(val)
            elif key == "errors":
                updates["errors"].extend(val)
            elif key == "completed_agents":
                pass # Already tracked
            else:
                # Merge agent-specific result (e.g., char_appearance)
                # Note: This assumes agents return dicts like {"char_appearance": {...}}
                # which merges cleanly update into state.
                updates[key] = val
                
    return updates


async def character_supervisor_node(state: CharacterTeamState) -> dict:
    """Character Supervisor - Routes between phases.
    
    Flow:
    Start -> Identity -> Supervisor -> Parallel -> Supervisor -> Aggregate -> Done
    """
    completed = state.get("completed_agents") or []
    
    # Phase 1: Identity (Must be done first)
    if "identity" not in completed:
        return {"next": "identity"}
    
    # Phase 2: Parallel Agents (If identity done, but parallel not done)
    # We check if *any* parallel agent is done. If not, run parallel node.
    # Logic: If 'identity' is done, and 'stats' (proxy for parallel) is NOT done, go parallel.
    # Better: Use a dedicated flag or check intersection.
    parallel_done = any(a in completed for a in PARALLEL_AGENTS)
    if not parallel_done:
        return {"next": "parallel_batch"}
        
    # Phase 3: Aggregation (If parallel done)
    if "aggregator" not in completed:
        return {"next": "aggregate"}
        
    return {"next": "done"}


def route_character_agents(state: CharacterTeamState) -> str:
    """Routing function."""
    return state.get("next", "done")


def create_character_team_graph() -> StateGraph:
    """Create the internal Character Team graph."""
    graph = StateGraph(CharacterTeamState)
    
    # Nodes
    graph.add_node("char_supervisor", character_supervisor_node)
    graph.add_node("identity", identity_extraction_node)
    graph.add_node("parallel_batch", parallel_extraction_node)  # New batch node
    graph.add_node("aggregator", character_aggregator_node)
    
    # Edges
    # Supervisor decides where to go
    graph.add_conditional_edges(
        "char_supervisor",
        route_character_agents,
        {
            "identity": "identity",
            "parallel_batch": "parallel_batch",
            "aggregate": "aggregator",
            "done": END,
        }
    )
    
    # Phase 1 & 2 loop back to supervisor to decide next step
    graph.add_edge("identity", "char_supervisor")
    graph.add_edge("parallel_batch", "char_supervisor")
    graph.add_edge("aggregator", "char_supervisor") # After aggregate, supervisor routes to END
    
    # Entry
    graph.set_entry_point("char_supervisor")
    
    return graph


# Pre-compile the graph for efficiency
character_team_graph = create_character_team_graph().compile()
