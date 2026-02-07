"""
Fusion - Reciprocal Rank Fusion (RRF) for combining search results

Implements the RRF algorithm used by QMD for hybrid search:
- Combines multiple ranked result lists
- Handles position-aware weighting
- Supports top-rank bonuses
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    result_lists: List[List[Dict]],
    k: int = 60,
    id_key: str = "file_path",
    score_key: str = "score",
    top_rank_bonus: bool = True
) -> List[Dict]:
    """
    Combine multiple ranked result lists using Reciprocal Rank Fusion.
    
    RRF score = Σ 1/(k + rank + 1) for each list the document appears in
    
    Args:
        result_lists: List of ranked result lists (each result is a dict)
        k: RRF constant (default 60, balances contribution of high vs low ranks)
        id_key: Key to use for document identity
        score_key: Key to store the fused score
        top_rank_bonus: Add bonus for documents that rank #1 in any list
    
    Returns:
        Fused result list sorted by combined score
    """
    if not result_lists:
        return []
    
    scores: Dict[str, float] = {}
    docs: Dict[str, Dict] = {}
    top_ranks: Dict[str, int] = {}  # Track best rank achieved
    
    for list_idx, results in enumerate(result_lists):
        for rank, doc in enumerate(results):
            doc_id = doc.get(id_key)
            if not doc_id:
                continue
            
            # Initialize if first time seeing this doc
            if doc_id not in scores:
                scores[doc_id] = 0.0
                docs[doc_id] = doc.copy()
                top_ranks[doc_id] = rank
            
            # RRF contribution
            scores[doc_id] += 1.0 / (k + rank + 1)
            
            # Track best rank
            if rank < top_ranks[doc_id]:
                top_ranks[doc_id] = rank
    
    # Apply top-rank bonus (QMD approach)
    if top_rank_bonus:
        for doc_id, best_rank in top_ranks.items():
            if best_rank == 0:
                scores[doc_id] += 0.05  # #1 rank bonus
            elif best_rank <= 2:
                scores[doc_id] += 0.02  # Top 3 bonus
    
    # Sort by fused score
    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # Build result list with fused scores
    results = []
    for doc_id, score in sorted_docs:
        doc = docs[doc_id].copy()
        doc[score_key] = score
        doc["rrf_rank"] = len(results)  # Track position in fused list
        results.append(doc)
    
    return results


def position_aware_blend(
    rrf_results: List[Dict],
    rerank_scores: Dict[str, float],
    id_key: str = "file_path"
) -> List[Dict]:
    """
    Blend RRF scores with reranker scores using position-aware weighting.
    
    QMD's approach:
    - Top 1-3: 75% RRF, 25% reranker (preserve exact matches)
    - Top 4-10: 60% RRF, 40% reranker
    - Top 11+: 40% RRF, 60% reranker (trust reranker more for lower ranks)
    
    Args:
        rrf_results: Results from RRF fusion with 'score' key
        rerank_scores: Dict mapping doc_id to reranker score (0-1)
    
    Returns:
        Results re-sorted by blended score
    """
    results = []
    
    for i, doc in enumerate(rrf_results):
        doc_id = doc.get(id_key)
        rrf_score = doc.get("score", 0)
        rerank_score = rerank_scores.get(doc_id, 0)
        
        # Position-aware weights
        if i < 3:
            rrf_weight = 0.75
        elif i < 10:
            rrf_weight = 0.60
        else:
            rrf_weight = 0.40
        
        rerank_weight = 1.0 - rrf_weight
        
        # Blend scores
        blended_score = (rrf_weight * rrf_score) + (rerank_weight * rerank_score)
        
        result = doc.copy()
        result["rrf_score"] = rrf_score
        result["rerank_score"] = rerank_score
        result["score"] = blended_score
        results.append(result)
    
    # Re-sort by blended score
    return sorted(results, key=lambda x: x["score"], reverse=True)


def normalize_scores(results: List[Dict], score_key: str = "score") -> List[Dict]:
    """
    Normalize scores to 0-1 range using min-max normalization.
    """
    if not results:
        return results
    
    scores = [r.get(score_key, 0) for r in results]
    min_score = min(scores)
    max_score = max(scores)
    
    if max_score == min_score:
        # All same score, normalize to 1.0
        for r in results:
            r[score_key] = 1.0
        return results
    
    for r in results:
        old_score = r.get(score_key, 0)
        r[score_key] = (old_score - min_score) / (max_score - min_score)
    
    return results
