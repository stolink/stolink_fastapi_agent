"""Character Team - Hierarchical Multi-Agent System.

This package implements a hierarchical agent system for character extraction.
The Character Team has its own internal supervisor that manages sub-agents.

Structure:
- supervisor.py: Internal Character Supervisor (routes sub-agents)
- identity.py: Extracts profile, role, aliases, status
- appearance.py: Extracts visual appearance
- personality.py: Extracts traits, flaws, values
- relations.py: Extracts character relationships
- dialogue_mood.py: Extracts dialogue config and current mood
- stats.py: Extracts game-related fields (stats, combat, economy)
- inventory.py: Extracts items and equipment
- aggregator.py: Merges all sub-agent results into FullCharacter
"""
from .supervisor import character_team_graph
from .state import CharacterTeamState

__all__ = ["character_team_graph", "CharacterTeamState"]
