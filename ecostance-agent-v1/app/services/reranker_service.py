from typing import List, Tuple
from sentence_transformers import CrossEncoder

class RerankerService:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, docs: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        if not docs:
            return []
        
        pairs = [[query, doc] for doc in docs]
        scores = self.model.predict(pairs)
        
        # Combine docs with scores
        doc_scores = list(zip(docs, scores))
        
        # Sort by score descending
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        return doc_scores[:top_k]

# Global instance
_reranker = None

def get_reranker_service(model_name: str = "BAAI/bge-reranker-base"):
    global _reranker
    if _reranker is None:
        _reranker = RerankerService(model_name=model_name)
    return _reranker
