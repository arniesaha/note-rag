# EM Knowledge System — Project Spec

**Status:** 📋 Planning
**Goal:** Personal knowledge base + intelligence API for Engineering Management

---

## Vision

Transform meeting notes, documents, and accumulated EM knowledge into a queryable system that provides:
- Decision recall ("What did we decide about X?")
- 1:1 prep ("Context on Sarah before our meeting")
- Project context ("Catch me up on Project Y")
- Weekly focus ("What should I pay attention to?")
- Pattern detection ("You've mentioned Z concern 5 times...")

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                   │
├──────────────────┬────────────────────┬─────────────────────────────────┤
│     Granola      │  Existing Obsidian │      Future Sources             │
│ (meeting notes)  │      Vault         │  (Slack exports, docs, etc)     │
└────────┬─────────┴─────────┬──────────┴──────────────┬──────────────────┘
         │                   │                         │
         ▼                   ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 OBSIDIAN VAULT (NAS @ 192.168.1.70)                      │
│                 /volume1/obsidian/em-knowledge/                          │
│                                                                         │
│   meetings/       people/       decisions/       projects/       daily/ │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
   ┌──────────┐            ┌──────────┐            ┌──────────┐
   │ Chunking │            │ Ollama   │            │ Qdrant   │
   │ Pipeline │ ─────────→ │ Embed    │ ─────────→ │ (Vector) │
   │          │            │ (local)  │            │          │
   └──────────┘            └──────────┘            └──────────┘
                                                         │
                                                         ▼
                                              ┌──────────────────┐
                                              │  Intelligence    │
                                              │  API (FastAPI)   │
                                              │  :8080           │
                                              └──────────────────┘
```

---

## Phase 1: Data Pipeline

### 1.1 Granola → Obsidian Sync

**Research Findings:**

| Method | Pros | Cons |
|--------|------|------|
| **Zapier → Webhook → NAS** | Direct to NAS, real-time | Need to expose endpoint (Cloudflare Tunnel or Tailscale Funnel) |
| **Zapier → Google Drive → NAS sync** | No exposed endpoint | Extra hop, slight delay |
| **Granola Enterprise API** | Full transcript, historic backfill | Requires Enterprise plan |

**Zapier Trigger:** "Note Added to Granola Folder" (instant)

**Data Available from Zapier:**
- Note title
- Note content (markdown)
- Meeting date/time
- (Limited attendee info)

**Recommended Flow:**
```
Granola Meeting Ends
        │
        ▼
Zapier Trigger: "Note Added to Granola Folder"
        │
        ▼
Zapier Action: Webhook POST to NAS
        │  POST http://192.168.1.70:5678/webhook/granola
        │  or via Cloudflare Tunnel: https://granola.arnabsaha.com/webhook
        │
        ▼
n8n Workflow on NAS:
  1. Parse webhook payload
  2. Extract metadata (title, date, attendees)
  3. Format as Obsidian markdown with frontmatter
  4. Write to /volume1/obsidian/em-knowledge/meetings/YYYY-MM-DD-{title}.md
```

**Markdown Template:**
```markdown
---
type: meeting
date: {{date}}
attendees: [{{attendees}}]
source: granola
tags: [meeting, {{inferred_tags}}]
---

# {{title}}

## Summary
{{summary}}

## Notes
{{content}}

## Action Items
{{action_items}}
```

### 1.2 Obsidian Vault Sync (NAS ↔ Office Laptop)

**Options Evaluated:**

| Method | Setup | Offline Support | Conflict Handling |
|--------|-------|-----------------|-------------------|
| **SMB Mount** | Easy | ❌ No | N/A (live) |
| **Syncthing** | Medium | ✅ Yes | ✅ Auto-merge |
| **Git + Obsidian Git plugin** | Medium | ✅ Yes | Manual |
| **Obsidian Local REST API** | Complex | ❌ No | N/A |

**Recommended: Syncthing**
- Runs on both NAS and laptop
- Continuous sync when on same network
- Works offline, syncs when reconnected
- Open source, no cloud dependency

**Setup Steps:**
1. Install Syncthing on NAS (Docker or native)
2. Install Syncthing on office laptop
3. Share `/volume1/obsidian/em-knowledge/` folder
4. Configure to sync when on 192.168.1.x network

**Alternative: SMB for simplicity**
- Map `\\192.168.1.70\obsidian\em-knowledge` as network drive
- Point Obsidian vault to that drive
- ⚠️ Only works when on office WiFi

### 1.3 Historic Content Migration

**From Existing Obsidian Vault:**
- Copy relevant notes to new vault
- Add/update frontmatter for consistency
- Organize into folder structure

**From Granola (if Enterprise API available):**
```python
# Pseudocode for historic backfill
notes = granola_api.list_notes(created_after="2024-01-01")
for note in notes:
    full_note = granola_api.get_note(note.id)
    markdown = format_as_obsidian(full_note)
    write_to_vault(f"meetings/{note.date}-{note.title}.md", markdown)
```

---

## Phase 2: Knowledge Indexing

### 2.1 Local Embedding Model

**Choice: Ollama + nomic-embed-text**

| Model | Size | Context | Performance |
|-------|------|---------|-------------|
| nomic-embed-text | 137M | 8192 tokens | Beats OpenAI ada-002 |
| mxbai-embed-large | 335M | 512 tokens | SOTA for size, but smaller context |

**Setup:**
```bash
# On NAS
ollama pull nomic-embed-text

# Test
curl http://localhost:11434/api/embed \
  -d '{"model": "nomic-embed-text", "input": "Test embedding"}'
```

### 2.2 Vector Database

**Choice: Qdrant (local Docker)**

Why Qdrant:
- Runs locally (Docker)
- Good performance
- REST + gRPC APIs
- Filtering support (by date, person, type)

```bash
docker run -p 6333:6333 -v /volume1/qdrant:/qdrant/storage qdrant/qdrant
```

### 2.3 Chunking Strategy

**For meeting notes:**
- Chunk by section (Summary, Notes, Action Items)
- Keep metadata in each chunk
- Overlap: 50 tokens

**For general notes:**
- Chunk by paragraph/section
- 500-800 tokens per chunk
- Overlap: 100 tokens

### 2.4 Indexing Pipeline

```python
# Pseudocode
def index_vault():
    for file in vault.glob("**/*.md"):
        frontmatter, content = parse_markdown(file)
        chunks = chunk_content(content, frontmatter)
        
        for chunk in chunks:
            embedding = ollama.embed("nomic-embed-text", chunk.text)
            qdrant.upsert(
                id=f"{file.stem}_{chunk.index}",
                vector=embedding,
                payload={
                    "text": chunk.text,
                    "file": file.name,
                    "type": frontmatter.get("type"),
                    "date": frontmatter.get("date"),
                    "people": frontmatter.get("attendees", []),
                }
            )

# Watch for changes
def watch_vault():
    for event in watchdog.observe(vault_path):
        if event.is_modified or event.is_created:
            reindex_file(event.path)
```

---

## Phase 3: Intelligence API

### 3.1 API Design

**Base URL:** `http://192.168.1.70:8080`

```
POST /query
  Body: { "question": "What did we decide about the migration?" }
  Returns: { "answer": "...", "sources": [...] }

POST /prep
  Body: { "person": "Sarah", "meeting_type": "1:1" }
  Returns: { "context": "...", "recent_topics": [...], "open_items": [...] }

GET /focus
  Returns: { "items": [...], "upcoming": [...], "patterns": [...] }

POST /recall
  Body: { "topic": "Project X" }
  Returns: { "summary": "...", "timeline": [...], "decisions": [...] }

GET /insights
  Query: ?period=week
  Returns: { "themes": [...], "concerns": [...], "follow_ups": [...] }
```

### 3.2 RAG Implementation

```python
from fastapi import FastAPI
from qdrant_client import QdrantClient
import ollama

app = FastAPI()
qdrant = QdrantClient("localhost", port=6333)

@app.post("/query")
async def query(question: str):
    # Embed question
    q_embed = ollama.embed("nomic-embed-text", question)
    
    # Search vector DB
    results = qdrant.search(
        collection_name="em_knowledge",
        query_vector=q_embed,
        limit=5
    )
    
    # Build context
    context = "\n\n".join([r.payload["text"] for r in results])
    
    # Generate answer (local LLM or Claude)
    answer = llm.generate(
        f"Based on this context:\n{context}\n\nAnswer: {question}"
    )
    
    return {
        "answer": answer,
        "sources": [r.payload["file"] for r in results]
    }
```

### 3.3 Clawdbot/Nix Integration

Add as a tool so you can ask naturally:
- "Prep me for my 1:1 with Sarah"
- "What did we decide about the platform migration?"
- "What should I focus on this week?"

---

## Phase 4: Knowledge Graph (Future)

**Purpose:** Capture relationships beyond semantic similarity

**Entities:**
- People (team members, stakeholders)
- Projects
- Decisions
- Topics/Themes
- Meetings

**Relationships:**
- Person ↔ Meeting (attended)
- Meeting ↔ Decision (made)
- Person ↔ Project (owns/contributes)
- Decision ↔ Project (affects)

**Tech:** Neo4j or Memgraph (local Docker)

---

## Tech Stack Summary

| Component | Choice | Why |
|-----------|--------|-----|
| Note Storage | Obsidian (NAS) | Markdown, portable, good UI |
| Sync | Syncthing | Local, offline support |
| Ingestion | n8n + Zapier | Already have n8n, Zapier for Granola |
| Embeddings | Ollama + nomic-embed-text | Local, good quality |
| Vector DB | Qdrant | Local Docker, filtering |
| API | FastAPI | Simple, Python |
| LLM (queries) | Claude via Clawdbot or local | Flexibility |
| Graph DB | Neo4j (future) | Relationships |

---

## Implementation Order

### Sprint 1: Foundation (Week 1-2)
- [ ] Set up Obsidian vault structure on NAS
- [ ] Configure Syncthing between NAS and laptop
- [ ] Migrate existing relevant notes
- [ ] Set up Qdrant Docker container

### Sprint 2: Granola Pipeline (Week 2-3)
- [ ] Create Zapier trigger for Granola
- [ ] Build n8n webhook endpoint
- [ ] Create markdown formatting logic
- [ ] Test end-to-end flow

### Sprint 3: Indexing (Week 3-4)
- [ ] Pull nomic-embed-text model
- [ ] Build chunking pipeline
- [ ] Create indexing script
- [ ] Add file watcher for incremental updates

### Sprint 4: API (Week 4-5)
- [ ] Build FastAPI service
- [ ] Implement /query endpoint
- [ ] Implement /prep endpoint
- [ ] Add Clawdbot integration

### Sprint 5: Intelligence (Week 5-6)
- [ ] Implement /focus endpoint
- [ ] Add pattern detection logic
- [ ] Build weekly digest generator
- [ ] Test and refine prompts

---

## Open Questions

1. **Granola plan** — Do you have access to Enterprise API for historic backfill?
2. **Expose endpoint?** — For Zapier webhook, use Cloudflare Tunnel, Tailscale Funnel, or just sync via Google Drive?
3. **Local LLM for queries?** — Or use Claude via Clawdbot? (Affects latency and quality)
4. **People extraction** — Should we auto-extract people names from notes and build profiles?

---

## Files

```
em-knowledge/
├── SPEC.md              # This file
├── vault/               # Obsidian vault (on NAS, symlinked here for dev)
│   ├── meetings/
│   ├── people/
│   ├── decisions/
│   ├── projects/
│   └── daily/
├── pipeline/            # Ingestion scripts
│   ├── granola_webhook.py
│   ├── indexer.py
│   └── watcher.py
└── api/                 # Intelligence API
    ├── main.py
    ├── rag.py
    └── prompts/
```

---

*Created: 2026-01-31*
*Last Updated: 2026-01-31*
