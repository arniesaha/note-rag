# Knowledge Graph v2 — Personal AI Knowledge Base

**Created:** 2026-02-05
**Status:** Proposal / Ideation
**Goal:** Extend the knowledge graph into a full personal AI knowledge base with conversational interface, multi-source ingestion, and agent capabilities.

---

## Current State (v1)

### Architecture
```
Data Sources → Embeddings → Vector Search → API
    │              │              │           │
 Obsidian      nomic-embed    LanceDB    FastAPI
 Granola         (Ollama)                   │
                                       ┌────┴────┐
                                    /search   /query (RAG)
```

### Capabilities
- ✅ Semantic search across 3,000+ files
- ✅ Basic RAG (question → search → Claude answer)
- ✅ 1:1 prep endpoint (`/prep/{person}`)
- ✅ Daily sync from Granola transcripts
- ✅ ~280-750ms query time

### Limitations
- API-only (no chat interface)
- Single-turn queries (no conversation memory)
- Only Obsidian/Granola data sources
- No proactive insights
- No entity relationships (documents only, no graph)
- No hybrid search (vector only, no keyword)

---

## Proposed Extension (v2)

### Vision

Transform from a search API into a **conversational AI assistant** that:
1. Understands context across multiple turns
2. Pulls from diverse data sources
3. Can reason and perform multi-step research
4. Surfaces proactive insights

### New Capabilities

#### 1. Conversational Interface

**Current:**
```bash
curl -X POST /query -d '{"question": "What did I discuss with Hitesh?"}'
# Returns answer, no follow-up possible
```

**Proposed:**
```
You: "What did I discuss with Hitesh last month?"
AI:  "You had 3 meetings with Hitesh in January:
      - Jan 8: Iceberg migration timeline
      - Jan 15: Team resourcing
      - Jan 22: Q1 planning"

You: "What were the action items from those?"
AI:  "Based on those meetings, the open items are:
      - [ ] Finalize migration runbook (due Jan 30)
      - [ ] Schedule architecture review
      ..."
      ↑
      Remembers context from previous question
```

**Tech:** Chainlit, Gradio, or custom CLI

---

#### 2. Multi-Source Ingestion

**Current sources:**
- Obsidian notes
- Granola transcripts

**Proposed additional sources:**

| Source | Data Type | Sync Method |
|--------|-----------|-------------|
| Slack | Messages, threads | Export + incremental API |
| GitHub | Issues, PRs, comments | API polling |
| Calendar | Events, attendees | Google Calendar API |
| Email | Summaries (not full text) | Gmail API or manual export |
| Browser | Bookmarks, reading list | Export |
| Twitter/X | Bookmarks, likes | Export |

**Architecture:**
```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Obsidian   │  │   Slack     │  │   GitHub    │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
                ┌───────▼───────┐
                │   Ingestion   │
                │   Pipeline    │
                └───────┬───────┘
                        │
              ┌─────────▼─────────┐
              │  Unified Index    │
              │  (LanceDB + BM25) │
              └───────────────────┘
```

---

#### 3. Advanced RAG Pipeline

**Current:**
```
Query → Embed → Vector Search → Top-K → LLM Answer
```

**Proposed:**
```
Query → Expand → Hybrid Search → Re-rank → Synthesize
         │           │              │           │
    Query        Semantic +     Cross-encoder  Claude
    expansion    BM25 keyword   scoring        with
    (synonyms,   fusion                        citations
    related
    terms)
```

**Components:**

| Component | Purpose | Tech |
|-----------|---------|------|
| Query Expansion | Improve recall | LLM-based or thesaurus |
| Hybrid Search | Best of both worlds | BM25 (tantivy) + vector |
| Re-ranking | Precision boost | Cross-encoder (ms-marco-MiniLM) |
| Citations | Source attribution | Return doc refs with answer |

---

#### 4. Agent Layer

Enable multi-step reasoning and task execution.

**Example: Meeting Prep Agent**
```
User: "Prepare me for my 1:1 with Suman tomorrow"

Agent thinks:
├── Search recent interactions with Suman
├── Find open action items assigned to/from Suman
├── Check Suman's recent PRs/commits (GitHub)
├── Pull tomorrow's calendar context
├── Look for any mentions in team channels
└── Generate prep doc with:
    - Recent topics discussed
    - Open items to follow up
    - Their recent work
    - Suggested talking points
```

**Tech:** LangGraph for orchestration, tool definitions for each data source

**Potential Agents:**
| Agent | Purpose |
|-------|---------|
| Prep Agent | Meeting preparation briefs |
| Research Agent | Deep dive on any topic |
| Action Tracker | Follow up on commitments |
| Weekly Digest | Summarize the week |
| People Agent | "Catch me up on X" |

---

#### 5. Knowledge Graph (Actual Graph)

Move from document-centric to entity-centric.

**Current (documents only):**
```
[Doc 1] ──similarity──► [Doc 2]
```

**Proposed (entities + relationships):**
```
[Hitesh] ──works_on──────► [Iceberg Migration]
    │                            │
 reports_to                  blocked_by
    │                            │
[Arnab] ◄──discussed_in───► [Q1 Planning Meeting]
    │
 assigned
    │
[Action: Review runbook]
```

**Entities to extract:**
- People (team members, external contacts)
- Projects (initiatives, epics)
- Decisions (what was decided, when, by whom)
- Action Items (task, owner, due date, status)
- Topics (recurring themes)

**Tech:** 
- Entity extraction: NER + LLM
- Storage: Neo4j or lightweight (NetworkX + JSON)
- Queries: "Who has context on X?" "What decisions led to Y?"

---

## Implementation Phases

### Phase 2a: Chat Interface (1-2 days)
- [ ] Add Chainlit or Gradio frontend
- [ ] Connect to existing `/query` endpoint
- [ ] Basic conversation UI

### Phase 2b: Multi-turn Memory (2-3 days)
- [ ] Implement conversation buffer
- [ ] Context windowing (last N turns)
- [ ] Session management

### Phase 2c: Hybrid Search (2-3 days)
- [ ] Add BM25 index (tantivy-py or rank_bm25)
- [ ] Implement score fusion (RRF)
- [ ] Compare quality vs pure vector

### Phase 2d: Re-ranking (1-2 days)
- [ ] Add cross-encoder model
- [ ] Re-rank top-K results
- [ ] Measure latency impact

### Phase 3a: Additional Sources (3-5 days)
- [ ] Slack export ingestion
- [ ] GitHub API integration
- [ ] Calendar sync

### Phase 3b: Entity Extraction (3-5 days)
- [ ] Define entity schema
- [ ] Extract entities from documents
- [ ] Store relationships

### Phase 4a: Agent Workflows (5-7 days)
- [ ] Design agent architecture
- [ ] Implement Prep Agent
- [ ] Add tool definitions

---

## Learning Outcomes

| Phase | New Skills |
|-------|------------|
| 2a-2b | Conversational AI, session management |
| 2c-2d | Hybrid search, re-ranking, IR fundamentals |
| 3a | API integrations, incremental sync |
| 3b | NER, relationship extraction, graph modeling |
| 4a | Agent orchestration, tool use, LangGraph |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Query latency | 280-750ms | <500ms p95 |
| Search relevance | Good | Measurably better (eval set) |
| Data sources | 2 | 5+ |
| Use frequency | API calls | Daily conversations |
| Prep quality | Basic | Comprehensive briefs |

---

## Recommended Starting Point

**Start with Phase 2a + 2b: Chat Interface with Memory**

Why:
1. Immediately useful (talk to your knowledge base)
2. Low complexity (builds on existing API)
3. Teaches conversation management patterns
4. Foundation for agent work later

**Estimated time:** 3-5 days

---

## Open Questions

1. **Hosting:** Chat UI on NAS or separate?
2. **Auth:** How to secure chat interface?
3. **Slack data:** Full history or recent only?
4. **Graph DB:** Neo4j (heavier) or lightweight JSON?
5. **Agents:** Build custom or use framework (LangGraph/CrewAI)?

---

*This document captures the v2 vision. Update as decisions are made.*
