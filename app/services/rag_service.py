
from typing import List, Dict, Any, Optional
import structlog
import numpy as np
from app.services.embedding_service import EmbeddingService, get_embedding_service

logger = structlog.get_logger()

class RAGContextService:
    """Service to retrieve relevant context using Vector Search."""
    
    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        self.embedding_service = embedding_service or get_embedding_service()
        self.event_store: List[Dict[str, Any]] = [] # In-memory vector store for now
        
    def add_events(self, events: List[Dict[str, Any]]):
        """Index events for retrieval."""
        valid_events = []
        for evt in events:
            # Assume 'description' or 'summary' is the text to embed
            text = evt.get("description") or evt.get("summary") or ""
            if not text:
                continue
            
            # Check if embedding exists, if not, we can't index efficiently here
            # In a real system, we'd ensure embeddings are generated at extraction time
            if "embedding" not in evt or not evt["embedding"]:
                # Cannot index without embedding in this simple implementation
                continue
                
            valid_events.append(evt)
            
        self.event_store.extend(valid_events)
        logger.info(f"Indexed {len(valid_events)} events for RAG.")

    async def retrieve_relevant_events(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve top_k relevant events for the query."""
        if not self.event_store:
            return []
            
        # Generate query embedding
        try:
            query_embedding = await self.embedding_service.generate_embedding_async(query)
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return []
            
        if not query_embedding:
            return []
            
        # Calculate similarities
        scores = []
        for evt in self.event_store:
            evt_emb = evt.get("embedding")
            if not evt_emb:
                scores.append(-1.0)
                continue
                
            # Cosine similarity
            sim = self._cosine_similarity(query_embedding, evt_emb)
            scores.append(sim)
            
        # Sort and select
        # Get indices of top_k
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0.0: # Filter completely irrelevant or errored
                results.append(self.event_store[idx])
                
        return results

    def _cosine_similarity(self, vec_a, vec_b) -> float:
        """Calculate cosine similarity."""
        a = np.array(vec_a)
        b = np.array(vec_b)
        norm_product = np.linalg.norm(a) * np.linalg.norm(b)
        if norm_product == 0:
            return 0.0
        return np.dot(a, b) / norm_product

# Singleton
_rag_service = None

def get_rag_service() -> RAGContextService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGContextService()
    return _rag_service
