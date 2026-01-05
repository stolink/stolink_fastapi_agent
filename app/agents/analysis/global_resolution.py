
from typing import List, Dict, Any
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agents.llm import get_gemini_llm, safe_ainvoke
from app.services.embedding_service import get_embedding_service

class CharacterCluster(BaseModel):
    """Cluster of potential same characters."""
    primary_name: str = Field(description="The most representative name for this cluster")
    aliases: List[str] = Field(description="List of all names in this cluster")
    ids: List[str] = Field(description="List of character IDs in this cluster")
    reasoning: str = Field(description="Why these characters are considered the same")

class GlobalResolutionResult(BaseModel):
    """Result of global entity resolution."""
    clusters: List[CharacterCluster] = Field(description="List of resolved character clusters")

RESOLUTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert editor resolving character inconsistencies in a novel.
    You have identified potential duplicate characters based on semantic similarity.
    Your job is to verify if they are indeed the same person and merge them.
    
    ### Rules
    1. **Strict Verification**: Only merge if you are 90% sure they are the SAME PERSON.
    2. **Descriptive References**: Characters may be referred to by different descriptions.
       - "젊은 여자" (young woman) and "쉘터 생존자" (shelter survivor) could be the SAME person if context matches.
       - "검은 수트의 남자" (man in black suit) and "보험 사기꾼" (insurance fraudster) could be the SAME person.
       - Compare descriptions, roles, and narrative context to determine sameness.
    3. **Named Characters**: "Jean Valjean" and "Mayor Madeleine" -> MERGE (same person, different aliases).
    4. **Different People**: "Jean Valjean" and "Javert" -> SEPARATE (clearly different roles/descriptions).
    5. **Primary Name Selection**: Choose the most formal or frequently used name as the primary name.
       - If only descriptive names exist, pick the most specific one.
    6. **Alias Aggregation**: Collect all other variations as aliases.
    
    ### Input
    List of potential clusters with character profiles (name, role, description).
    """),
    ("human", "{cluster_info}")
])


class GlobalResolutionAgent:
    def __init__(self):
        self.llm = get_gemini_llm(tier="premium") # Use Premium for high reasoning
        self.embedding_service = get_embedding_service()
        # Increased threshold to prevent incorrect merging of distinct characters
        # 0.90 requires near-identical semantic content (same person, different mentions)
        self.similarity_threshold = 0.90 # Increased to prevent incorrect merges (e.g. Heze vs Claire)

    async def resolve_entities(self, characters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve and merge duplicate characters using semantic similarity."""
        if not characters:
            return []
            
        print(f"[GLOBAL_RES] Starting resolution for {len(characters)} characters...")
        
        # 1. Generate Embeddings using name + description + role (semantic matching)
        embeddings = []
        
        for char in characters:
            # 🆕 Combine name + description + role for richer semantic embedding
            # This enables matching "젊은 여자" with "쉘터 생존자" if descriptions overlap
            name = char.get("name", "Unknown")
            description = char.get("description", "") or char.get("profile", {}).get("description", "") or ""
            role = char.get("role", "") or char.get("profile", {}).get("role", "") or ""
            aliases = ", ".join(char.get("aliases", []))
            
            # Build semantic text for embedding
            semantic_text = f"{name}. {role}. {description}. Also known as: {aliases}".strip()
            
            if "embedding" in char and char["embedding"]:
                embeddings.append(char["embedding"])
            else:
                # Generate embedding from semantic text (not just name)
                emb = await self.embedding_service.generate_embedding_async(semantic_text)
                embeddings.append(emb)
        
        if len(embeddings) < 2:
            return characters


        # 2. Initial Clustering (Agglomerative)
        # Using 1 - cosine_similarity as distance
        X = np.array(embeddings)
        # Normalize
        norm = np.linalg.norm(X, axis=1, keepdims=True)
        X_norm = X / (norm + 1e-10)
        
        # Clustering
        # separation distance = 1 - similarity. So threshold 0.30 corresponds to 0.70 similarity
        clustering = AgglomerativeClustering(
            n_clusters=None, 
            metric='cosine', 
            linkage='average',
            distance_threshold=1 - self.similarity_threshold
        )
        labels = clustering.fit_predict(X_norm)
        
        # Group by cluster
        clusters = {}
        for i, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(characters[i])
            
        print(f"[GLOBAL_RES] Found {len(clusters)} potential clusters from {len(characters)} characters.")
        
        # 2.5 Context-Based Merge Candidates (NEW)
        # Find singleton clusters that share location/faction and could be the same person
        singletons = [group[0] for label, group in clusters.items() if len(group) == 1]
        context_merge_candidates = []
        
        for i, char1 in enumerate(singletons):
            for j, char2 in enumerate(singletons):
                if i >= j:
                    continue
                # Check if same location_context or faction
                loc1 = char1.get("relations", {}).get("location_context", "")
                loc2 = char2.get("relations", {}).get("location_context", "")
                fac1 = char1.get("profile", {}).get("faction", {}).get("name", "")
                fac2 = char2.get("profile", {}).get("faction", {}).get("name", "")
                
                same_location = loc1 and loc2 and loc1 == loc2
                same_faction = fac1 and fac2 and fac1 == fac2
                
                if same_location or same_faction:
                    print(f"[GLOBAL_RES] Context match: {char1.get('name')} + {char2.get('name')} (loc={same_location}, fac={same_faction})")
                    context_merge_candidates.append([char1, char2])
        
        # 3. LLM Verification & Merge
        # For trivial clusters (size 1), skip LLM unless context-matched
        final_characters = []
        commits_to_llm = []
        
        # Add multi-member clusters
        for label, group in clusters.items():
            if len(group) == 1:
                # Will be added later if not context-merged
                pass
            else:
                commits_to_llm.append(group)
        
        # Add context-based merge candidates
        context_merged_names = set()
        for pair in context_merge_candidates:
            commits_to_llm.append(pair)
            for c in pair:
                context_merged_names.add(c.get("name"))
        
        # Add remaining singletons (not context-merged)
        for label, group in clusters.items():
            if len(group) == 1 and group[0].get("name") not in context_merged_names:
                final_characters.append(group[0])
        
        if commits_to_llm:
            print(f"[GLOBAL_RES] Verifying {len(commits_to_llm)} multimember clusters with LLM...")
            # Prepare prompt context
            cluster_descriptions = []
            for i, group in enumerate(commits_to_llm):
                desc = f"Cluster {i+1}:\n" + "\n".join([f"- {c.get('name', 'Unknown')} (ID: {c.get('_id')}, Role: {c.get('role')})" for c in group])
                cluster_descriptions.append(desc)
            
            prompt_text = "\n\n".join(cluster_descriptions)
            
            # Simple verify for now (can be structured)
            structured_llm = self.llm.with_structured_output(GlobalResolutionResult)
            chain = RESOLUTION_PROMPT | structured_llm
            
            try:
                result = await safe_ainvoke(chain, {"cluster_info": prompt_text})
                
                # Apply merges
                for cluster_res in result.clusters:
                    # Find original chars
                    involved_ids = set(cluster_res.ids)
                    merged_char = self._merge_character_data(
                        [c for group in commits_to_llm for c in group if c.get("_id") in involved_ids],
                        cluster_res.primary_name,
                        cluster_res.aliases
                    )
                    final_characters.append(merged_char)
                    
            except Exception as e:
                print(f"[GLOBAL_RES] LLM Verification failed: {e}. Keeping original clusters.")
                # Fallbck: just keep valid characters unmerged or simple merge
                for group in commits_to_llm:
                    final_characters.extend(group)

        print(f"[GLOBAL_RES] Resolution complete. Final count: {len(final_characters)}")
        return final_characters

    def _merge_character_data(self, chars: List[dict], primary_name: str, aliases: List[str]) -> dict:
        """Merge multiple character dictionaries into one."""
        if not chars:
            return {}
            
        # Base on the first character or the one matching primary name
        # Use profile.name (FullCharacter format) for matching
        def get_name(c):
            return c.get("profile", {}).get("name") or c.get("name")
        
        primary_char = next((c for c in chars if get_name(c) == primary_name), chars[0])
        merged = primary_char.copy()
        # Do NOT add top-level "name" field - profile.name is the canonical location
        # merged["name"] = primary_name  # REMOVED: causes duplicate name field
        merged["aliases"] = list(set(merged.get("aliases", []) + aliases))
        
        # Merge other fields (events, relations) - overly simplified for now
        # Ideally we union event_refs and re-map relation targets
        return merged

