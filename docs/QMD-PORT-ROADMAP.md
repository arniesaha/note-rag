# QMD Improvements Port — Roadmap

**Goal:** Port QMD's search quality, query expansion, reranking, and MCP support to our knowledge-graph.

**Reference:** https://github.com/tobi/qmd (Tobi Lütke's project)

---

## Current State

| Feature | QMD | Our KG | Gap |
|---------|-----|--------|-----|
| Vector Search | ✅ embeddinggemma | ✅ Ollama nomic-embed | ✅ |
| BM25 (FTS) | ✅ SQLite FTS5 | ❌ | Need to add |
| Hybrid Fusion | ✅ RRF | ❌ | Need to add |
| Query Expansion | ✅ Fine-tuned 1.7B | ❌ | Need to add |
| Reranking | ✅ qwen3-reranker | ❌ | Need to add |
| RAG Answers | ❌ | ✅ Claude | ✅ (we're ahead) |
| MCP Server | ✅ | ❌ | Need to add |
| HTTP API | ❌ | ✅ FastAPI | ✅ (we're ahead) |
| n8n/Webhook | ❌ | ✅ | ✅ (we're ahead) |

---

## Phase 1: Hybrid Search (BM25 + Vector + RRF)

**Impact:** High — biggest search quality improvement

### 1.1 Add SQLite FTS5 Table

```python
# New file: fts_index.py
import sqlite3

class FTSIndex:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self._init_tables()
    
    def _init_tables(self):
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts 
            USING fts5(
                file_path,
                title,
                content,
                tokenize='porter unicode61'
            )
        """)
    
    def search(self, query: str, limit: int = 30) -> List[dict]:
        cursor = self.conn.execute("""
            SELECT file_path, title, snippet(documents_fts, 2, '<b>', '</b>', '...', 64),
                   bm25(documents_fts) as score
            FROM documents_fts
            WHERE documents_fts MATCH ?
            ORDER BY score
            LIMIT ?
        """, (query, limit))
        return [{"file_path": r[0], "title": r[1], "snippet": r[2], "score": abs(r[3])} 
                for r in cursor.fetchall()]
```

### 1.2 Implement Reciprocal Rank Fusion (RRF)

```python
def reciprocal_rank_fusion(result_lists: List[List[dict]], k: int = 60) -> List[dict]:
    """
    Combine multiple ranked lists using RRF.
    
    RRF score = Σ 1/(k + rank) for each list the doc appears in
    
    k=60 is standard (balances high vs low ranked docs)
    """
    scores = {}
    docs = {}
    
    for results in result_lists:
        for rank, doc in enumerate(results):
            doc_id = doc["file_path"]
            if doc_id not in scores:
                scores[doc_id] = 0
                docs[doc_id] = doc
            scores[doc_id] += 1.0 / (k + rank + 1)
    
    # Sort by fused score
    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [{"score": score, **docs[doc_id]} for doc_id, score in sorted_docs]
```

### 1.3 Integrate into Searcher

```python
async def hybrid_search(self, query: str, vault: str, limit: int = 10):
    # Run BM25 and vector search in parallel
    bm25_results = self.fts_index.search(query, limit=30)
    vector_results = await self.vector_search(query, vault, limit=30)
    
    # Fuse results
    fused = reciprocal_rank_fusion([bm25_results, vector_results])
    
    return fused[:limit]
```

---

## Phase 2: Query Expansion

**Impact:** Medium — helps with imprecise queries

### 2.1 Add Query Expansion via Ollama

```python
QUERY_EXPANSION_PROMPT = """Generate 2 alternative search queries for: "{query}"

Rules:
- Keep semantic meaning
- Use different words/phrasings
- One should be more specific, one more general

Output format (exactly):
1. [first alternative]
2. [second alternative]"""

async def expand_query(self, query: str) -> List[str]:
    response = await self.ollama_generate(QUERY_EXPANSION_PROMPT.format(query=query))
    # Parse alternatives
    alternatives = parse_numbered_list(response)
    return [query] + alternatives  # Original + expansions
```

### 2.2 Multi-Query Search

```python
async def expanded_hybrid_search(self, query: str, vault: str, limit: int = 10):
    queries = await self.expand_query(query)
    
    all_results = []
    for q in queries:
        results = await self.hybrid_search(q, vault, limit=30)
        all_results.append(results)
    
    # Weight original query higher (appears twice)
    all_results.insert(0, all_results[0])  # Double-weight original
    
    fused = reciprocal_rank_fusion(all_results)
    return fused[:limit]
```

---

## Phase 3: LLM Reranking

**Impact:** High — significant quality boost for top results

### 3.1 Add Reranker

QMD uses `qwen3-reranker-0.6b`. We can use Ollama with a similar approach:

```python
RERANK_PROMPT = """Query: {query}

Document: {document}

Is this document relevant to the query? Answer only YES or NO."""

async def rerank(self, query: str, documents: List[dict], top_k: int = 10) -> List[dict]:
    scored = []
    
    for doc in documents[:30]:  # Rerank top 30
        response = await self.ollama_generate(
            RERANK_PROMPT.format(query=query, document=doc["content"][:2000]),
            model="qwen2.5:0.5b"  # Small, fast model
        )
        
        # Score based on YES/NO
        is_relevant = response.strip().upper().startswith("YES")
        score = 1.0 if is_relevant else 0.0
        scored.append({**doc, "rerank_score": score})
    
    # Position-aware blending (QMD approach)
    for i, doc in enumerate(scored):
        rrf_weight = 0.75 if i < 3 else (0.60 if i < 10 else 0.40)
        rerank_weight = 1 - rrf_weight
        doc["final_score"] = (rrf_weight * doc["score"]) + (rerank_weight * doc["rerank_score"])
    
    return sorted(scored, key=lambda x: x["final_score"], reverse=True)[:top_k]
```

---

## Phase 4: MCP Server

**Impact:** High — enables Claude Desktop/Code integration

### 4.1 Add MCP Endpoint

```python
# New file: mcp_server.py
from mcp import Server, Tool

class KnowledgeGraphMCP:
    def __init__(self, searcher):
        self.searcher = searcher
        self.server = Server("knowledge-graph")
        self._register_tools()
    
    def _register_tools(self):
        @self.server.tool("kg_search")
        async def search(query: str, vault: str = "all", limit: int = 10):
            """Fast hybrid search (BM25 + vector)"""
            return await self.searcher.hybrid_search(query, vault, limit)
        
        @self.server.tool("kg_query")
        async def query(question: str, vault: str = "all"):
            """Hybrid search + reranking + RAG answer"""
            return await self.searcher.query_with_llm(question, vault)
        
        @self.server.tool("kg_get")
        async def get_document(file_path: str):
            """Get full document by path"""
            return await self.searcher.get_document(file_path)
```

### 4.2 Run MCP Server

```bash
# Add CLI command
python -m knowledge_graph.mcp serve
```

### 4.3 Claude Desktop Config

```json
{
  "mcpServers": {
    "knowledge-graph": {
      "command": "python",
      "args": ["-m", "knowledge_graph.mcp", "serve"],
      "env": {
        "KG_API_URL": "http://192.168.1.70:8080"
      }
    }
  }
}
```

---

## Phase 5: OpenClaw Skill Enhancement

**Impact:** Medium — better agent integration

### 5.1 Update Skill with New Endpoints

```yaml
# SKILL.md updates
- Add /hybrid-search endpoint
- Add /query-expanded endpoint  
- Document reranking behavior
- Add MCP setup instructions
```

---

## Implementation Order

| Phase | Effort | Impact | Priority |
|-------|--------|--------|----------|
| 1. Hybrid Search | Medium | High | 🔴 First |
| 3. Reranking | Medium | High | 🔴 Second |
| 2. Query Expansion | Low | Medium | 🟡 Third |
| 4. MCP Server | Medium | High | 🟡 Fourth |
| 5. Skill Update | Low | Medium | 🟢 Last |

---

## Files to Create/Modify

```
services/api/
├── fts_index.py       # NEW - SQLite FTS5 wrapper
├── reranker.py        # NEW - LLM reranking
├── query_expander.py  # NEW - Query expansion
├── fusion.py          # NEW - RRF implementation
├── mcp_server.py      # NEW - MCP protocol
├── searcher.py        # MODIFY - integrate hybrid search
├── main.py            # MODIFY - add new endpoints
└── requirements.txt   # MODIFY - add mcp-sdk
```

---

## Models Needed (Ollama)

| Model | Purpose | Size |
|-------|---------|------|
| nomic-embed-text | Embeddings (existing) | ~275MB |
| qwen2.5:0.5b | Reranking + expansion | ~400MB |

Or use dedicated reranker: `ollama pull snowflake-arctic-embed-rerank`

---

## Next Steps

1. ✅ Create this roadmap
2. ⏳ Implement Phase 1 (Hybrid Search)
3. ⏳ Test with existing data
4. ⏳ Implement Phase 3 (Reranking)
5. ⏳ Add MCP server
6. ⏳ Update skill

---

*Created: 2026-02-06*
*Reference: github.com/tobi/qmd*
