"""
Reranker - LLM-based reranking for search results

Uses Ollama to score document relevance with a fast, small model.
"""

import asyncio
import logging
from typing import List, Dict, Optional
import httpx

logger = logging.getLogger(__name__)

# Prompt for relevance scoring
RERANK_PROMPT = """You are a relevance judge. Given a query and a document, determine if the document is relevant.

Query: {query}

Document:
{document}

Is this document relevant to the query? Answer with only YES or NO."""

# Prompt for query expansion
QUERY_EXPANSION_PROMPT = """Generate 2 alternative search queries for: "{query}"

Rules:
- Keep the same meaning/intent
- Use different words or phrasings  
- One should be more specific, one more general
- Keep each under 10 words

Output exactly 2 lines, one query per line:"""


class Reranker:
    """LLM-based document reranking using Ollama."""
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen2.5:0.5b",  # Fast, small model
        timeout: float = 10.0
    ):
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = timeout
    
    async def _generate(self, prompt: str) -> str:
        """Call Ollama generate API."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.0,
                            "num_predict": 10  # Short response
                        }
                    },
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json().get("response", "").strip()
            except Exception as e:
                logger.error(f"Ollama generate error: {e}")
                return ""
    
    async def score_document(self, query: str, document: str) -> float:
        """
        Score a single document's relevance to query.
        
        Returns 1.0 for relevant, 0.0 for not relevant.
        """
        # Truncate document to avoid context overflow
        doc_text = document[:2000]
        
        prompt = RERANK_PROMPT.format(query=query, document=doc_text)
        response = await self._generate(prompt)
        
        # Parse YES/NO response
        response_upper = response.upper().strip()
        if response_upper.startswith("YES"):
            return 1.0
        elif response_upper.startswith("NO"):
            return 0.0
        else:
            # Ambiguous response, give partial score
            logger.debug(f"Ambiguous rerank response: {response}")
            return 0.5
    
    async def rerank(
        self,
        query: str,
        documents: List[Dict],
        content_key: str = "content",
        id_key: str = "file_path",
        top_k: int = 30,
        concurrency: int = 5
    ) -> Dict[str, float]:
        """
        Rerank documents by relevance to query.
        
        Args:
            query: Search query
            documents: List of documents (dicts with content_key)
            content_key: Key for document content
            id_key: Key for document ID
            top_k: Number of docs to rerank
            concurrency: Max concurrent LLM calls
        
        Returns:
            Dict mapping doc_id to relevance score (0-1)
        """
        docs_to_rerank = documents[:top_k]
        
        # Semaphore for concurrency control
        sem = asyncio.Semaphore(concurrency)
        
        async def score_with_semaphore(doc: Dict) -> tuple:
            async with sem:
                doc_id = doc.get(id_key, "")
                content = doc.get(content_key, "")
                
                if not content:
                    # Try 'snippet' as fallback
                    content = doc.get("snippet", doc.get("excerpt", ""))
                
                score = await self.score_document(query, content)
                return (doc_id, score)
        
        # Score all documents concurrently
        tasks = [score_with_semaphore(doc) for doc in docs_to_rerank]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build score dict, handling errors
        scores = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Rerank error: {result}")
                continue
            doc_id, score = result
            scores[doc_id] = score
        
        return scores
    
    async def expand_query(self, query: str) -> List[str]:
        """
        Generate alternative query formulations.
        
        Returns list of queries: [original, alternative1, alternative2]
        """
        prompt = QUERY_EXPANSION_PROMPT.format(query=query)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,  # Some creativity
                            "num_predict": 50
                        }
                    },
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json().get("response", "").strip()
                
                # Parse response lines
                lines = [line.strip() for line in result.split("\n") if line.strip()]
                # Clean up numbered prefixes like "1." or "1:"
                alternatives = []
                for line in lines[:2]:
                    # Remove common prefixes
                    for prefix in ["1.", "2.", "1:", "2:", "1)", "2)", "-", "•"]:
                        if line.startswith(prefix):
                            line = line[len(prefix):].strip()
                    if line and line != query:
                        alternatives.append(line)
                
                return [query] + alternatives
                
            except Exception as e:
                logger.error(f"Query expansion error: {e}")
                return [query]  # Fallback to original only
    
    async def check_model(self) -> bool:
        """Check if the reranker model is available."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.ollama_url}/api/tags",
                    timeout=5.0
                )
                response.raise_for_status()
                models = response.json().get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]
                
                target = self.model.split(":")[0]
                return target in model_names
            except Exception as e:
                logger.error(f"Model check error: {e}")
                return False
