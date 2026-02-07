# Knowledge Graph — Architecture Document

**Version:** 1.0
**Date:** 2026-02-01
**Status:** Draft — Pending Review

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                   NAS                                        │
│                            192.168.1.70                                      │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         Docker Compose                               │   │
│  │                                                                      │   │
│  │   ┌─────────────┐                       ┌─────────────────────┐    │   │
│  │   │   Ollama    │                       │    Knowledge API    │    │   │
│  │   │   (CPU)     │                       │     (FastAPI)       │    │   │
│  │   │             │                       │                     │    │   │
│  │   │ nomic-embed │◄─────────────────────►│  /search           │    │   │
│  │   │    :11434   │                       │  /prep/{person}    │    │   │
│  │   │             │                       │  /query            │    │   │
│  │   └─────────────┘                       │  /restructure      │    │   │
│  │                                         │  /index            │    │   │
│  │                                         │  /health           │    │   │
│  │                                         │    :8080           │    │   │
│  │                                         └──────────┬──────────┘    │   │
│  └─────────────────────────────────────────────────────┼───────────────┘   │
│                                                        │                    │
│  ┌─────────────────────────────────────────────────────┼───────────────┐   │
│  │                        File System                  │               │   │
│  │                                                     │               │   │
│  │   /home/Arnab/clawd/projects/knowledge-graph/          │               │   │
│  │   ├── obsidian/                                     │               │   │
│  │   │   ├── work/          (1,247 files)             │               │   │
│  │   │   │   ├── people/                              │ File Watcher  │   │
│  │   │   │   ├── projects/                            │ (watchdog)    │   │
│  │   │   │   ├── team/                                │               │   │
│  │   │   │   └── ...                                  │               │   │
│  │   │   └── personal/      (65 files)                │               │   │
│  │   │       ├── health/                              │               │   │
│  │   │       ├── finance/   ⛔ (excluded from Claude) │               │   │
│  │   │       └── ...                                  │               │   │
│  │   │                                                │               │   │
│  │   └── lancedb/           (embedded vector DB)      │               │   │
│  │       ├── work.lance/    (~10k vectors)       ◄────┘               │   │
│  │       └── personal.lance/ (~500 vectors)                           │   │
│  │                                                                    │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTP (localhost)
                                      ▼
                          ┌─────────────────────┐
                          │   Clawdbot Gateway  │
                          │   :18789             │
                          │                     │
                          │   POST /api/chat    │
                          │   (routes to Claude)│
                          └─────────────────────┘
```

---

## 2. Components

### 2.1 Ollama (Embedding Service)

**Purpose:** Generate vector embeddings for documents and queries

**Configuration:**
```yaml
image: ollama/ollama:latest
ports: ["11434:11434"]
volumes:
  - ollama_data:/root/.ollama
environment:
  - OLLAMA_HOST=0.0.0.0
deploy:
  resources:
    limits:
      memory: 2G
```

**Model:** `nomic-embed-text`
- 137M parameters
- 768-dimension vectors
- 8192 token context window
- Optimized for CPU inference

**API:**
```bash
POST http://localhost:11434/api/embed
{
  "model": "nomic-embed-text",
  "input": "text to embed"
}
```

---

### 2.2 LanceDB (Embedded Vector Database)

**Purpose:** Store and search document embeddings

**Why LanceDB:**
- Embedded library (no separate server process)
- Data stored as files (easy backup: just copy the folder)
- Fast vector search with filtering
- Simple Python API

**Installation:**
```bash
pip install lancedb
```

**Tables:**

| Table | Content | Est. Vectors | Location |
|-------|---------|--------------|----------|
| `work` | Work vault chunks | ~10,000 | `lancedb/work.lance/` |
| `personal` | Personal vault chunks | ~500 | `lancedb/personal.lance/` |

**Schema:**
```python
import lancedb
from lancedb.pydantic import LanceModel, Vector

class DocumentChunk(LanceModel):
    id: str                    # Unique chunk ID
    vector: Vector(768)        # nomic-embed-text dimension
    file_path: str
    title: str
    category: str              # people, projects, team, etc.
    people: list[str]          # Mentioned people
    projects: list[str]        # Mentioned projects
    date: str                  # ISO date
    vault: str                 # "work" or "personal"
    chunk_index: int
    content: str               # Actual text content

# Usage
db = lancedb.connect("./lancedb")
table = db.create_table("work", schema=DocumentChunk)
```

**Backup:**
```bash
# Daily backup - just copy the folder
cp -r ./lancedb ./backups/lancedb_$(date +%Y%m%d)
```

---

### 2.3 Knowledge API (FastAPI)

**Purpose:** Main application service

**Configuration:**
```yaml
build: ./api
ports: ["8080:8080"]
volumes:
  - /home/Arnab/clawd/projects/knowledge-graph/obsidian:/data/obsidian
  - /home/Arnab/clawd/projects/knowledge-graph/lancedb:/data/lancedb
  - ./config:/app/config
environment:
  - OLLAMA_URL=http://ollama:11434
  - LANCEDB_PATH=/data/lancedb
  - VAULT_WORK_PATH=/data/obsidian/work
  - VAULT_PERSONAL_PATH=/data/obsidian/personal
  - CLAWDBOT_URL=http://host.docker.internal:18789
  - CLAWDBOT_TOKEN=${CLAWDBOT_TOKEN}
  - EXCLUDED_FOLDERS=personal/finance
  - LOG_LEVEL=INFO
depends_on:
  - ollama
extra_hosts:
  - "host.docker.internal:host-gateway"
```

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/search` | POST | Semantic search across vaults |
| `/query` | POST | RAG query with LLM answer |
| `/prep/{person}` | GET | 1:1 preparation context |
| `/actions` | GET | Open action items |
| `/restructure` | POST | Trigger file reorganization |
| `/index` | POST | Trigger reindexing |
| `/stats` | GET | Index statistics |

---

### 2.4 File Watcher

**Purpose:** Detect new/modified files and trigger processing

**Implementation:** Built into Knowledge API using `watchdog` library

**Behavior:**
1. Watch `work/` and `personal/` directories
2. On new file detected:
   - Categorize based on content/filename
   - Move to appropriate subfolder
   - Add frontmatter if missing
   - Queue for indexing
3. On modified file:
   - Re-index affected chunks
4. Debounce: 30 seconds (avoid processing during active sync)

---

## 3. Data Flow

### 3.1 Ingestion Flow

```
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│  Granola   │────▶│  Obsidian  │────▶│    NAS     │────▶│   File     │
│  Meeting   │     │   Plugin   │     │   Vault    │     │  Watcher   │
└────────────┘     └────────────┘     └────────────┘     └─────┬──────┘
                                                               │
     ┌─────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│ Categorize │────▶│   Chunk    │────▶│   Embed    │────▶│   Store    │
│ & Move     │     │  Content   │     │  (Ollama)  │     │  (Qdrant)  │
└────────────┘     └────────────┘     └────────────┘     └────────────┘
```

### 3.2 Query Flow

```
┌────────────┐     ┌────────────┐     ┌────────────┐     ┌────────────┐
│   User     │────▶│  Embed     │────▶│  Vector    │────▶│  Retrieve  │
│   Query    │     │  Query     │     │  Search    │     │  Top-K     │
└────────────┘     └────────────┘     └────────────┘     └─────┬──────┘
                                                               │
     ┌─────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────┐     ┌────────────┐     ┌────────────┐
│  Build     │────▶│  Claude    │────▶│  Return    │
│  Context   │     │  Generate  │     │  Answer    │
└────────────┘     └────────────┘     └────────────┘
```

---

## 4. Directory Structure

```
knowledge-graph/
├── docs/                        # Project documentation
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   └── SPEC.md
├── obsidian/
│   ├── work/                    # Work vault (synced from Granola)
│   │   ├── people/
│   │   ├── projects/
│   │   ├── team/
│   │   ├── incidents/
│   │   ├── interviews/
│   │   ├── insights/
│   │   └── reference/
│   ├── personal/                # Personal vault
│   │   ├── health/
│   │   ├── finance/             # ⛔ Excluded from Claude
│   │   ├── immigration/
│   │   └── misc/
│   └── vault/                   # Original source (backup)
├── lancedb/                     # Vector database (file-based)
│   ├── work.lance/
│   └── personal.lance/
├── services/                    # Docker services
│   ├── docker-compose.yml
│   ├── api/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   ├── indexer.py
│   │   ├── searcher.py
│   │   ├── restructurer.py
│   │   └── watcher.py
│   └── config/
│       └── settings.yaml
├── scripts/                     # Utility scripts
│   ├── analyze_meetings.py
│   ├── reorganize_vault.py
│   └── generate_insights.py
├── backups/                     # Daily LanceDB backups
│   └── lancedb_YYYYMMDD/
├── analysis/                    # Analysis outputs
│   └── meetings_analysis.json
├── workflows/                   # n8n job search workflow
└── README.md
```

---

## 5. API Specification

### 5.1 Search

```http
POST /search
Content-Type: application/json
Authorization: Bearer {token}

{
  "query": "migration timeline",
  "vault": "work",           // Optional: "work", "personal", "all"
  "category": "projects",    // Optional filter
  "person": "Sriram",        // Optional filter
  "date_from": "2026-01-01", // Optional filter
  "limit": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "score": 0.89,
      "file_path": "work/projects/lean-graph/2026-01-23-migration.md",
      "title": "Migration workflow optimization",
      "excerpt": "...decided to proceed with shadow deployment...",
      "date": "2026-01-23",
      "people": ["Sriram", "Suman"],
      "category": "projects"
    }
  ],
  "total": 42,
  "query_time_ms": 234
}
```

### 5.2 Query (RAG)

```http
POST /query
Content-Type: application/json
Authorization: Bearer {token}

{
  "question": "What did we decide about the migration timeline?",
  "vault": "work"
}
```

**Response:**
```json
{
  "answer": "Based on the meetings from January 2026, the team decided to...",
  "sources": [
    {
      "file": "work/projects/lean-graph/2026-01-23-migration.md",
      "excerpt": "..."
    }
  ],
  "confidence": 0.85,
  "query_time_ms": 2341
}
```

### 5.3 Prep (1:1 Context)

```http
GET /prep/hitesh
Authorization: Bearer {token}
```

**Response:**
```json
{
  "person": "Hitesh",
  "meeting_count": 18,
  "last_meeting": "2026-01-28",
  "recent_topics": [
    "Bedrock benchmarking",
    "Janus Graph upgrade",
    "AI agent development"
  ],
  "open_actions": [
    "Complete right-sizing validation",
    "Create benchmarking issues"
  ],
  "recent_meetings": [
    {
      "date": "2026-01-28",
      "title": "Hitesh / Arnab",
      "summary": "..."
    }
  ]
}
```

---

## 6. Configuration

### 6.1 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_URL` | Ollama API endpoint | `http://ollama:11434` |
| `LANCEDB_PATH` | Path to LanceDB data | `/data/lancedb` |
| `VAULT_WORK_PATH` | Path to work vault | `/data/obsidian/work` |
| `VAULT_PERSONAL_PATH` | Path to personal vault | `/data/obsidian/personal` |
| `EXCLUDED_FOLDERS` | Folders to exclude from Claude | `personal/finance` |
| `CLAWDBOT_URL` | Clawdbot gateway endpoint | `http://host.docker.internal:18789` |
| `CLAWDBOT_TOKEN` | Clawdbot gateway auth token | Required |
| `API_TOKEN` | Bearer token for API auth | Required |
| `LOG_LEVEL` | Logging level | `INFO` |
| `WATCH_INTERVAL` | File watch debounce (sec) | `30` |
| `CHUNK_SIZE` | Max tokens per chunk | `500` |
| `CHUNK_OVERLAP` | Token overlap between chunks | `50` |

### 6.2 settings.yaml

```yaml
indexing:
  chunk_size: 500
  chunk_overlap: 50
  batch_size: 10
  # Reindex strategy
  incremental: true           # Index on file change
  full_reindex_day: "sunday"  # Weekly full reindex
  full_reindex_hour: 3        # 3 AM
  
search:
  default_limit: 10
  max_limit: 50
  similarity_threshold: 0.7

rag:
  model: "claude-sonnet-4-20250514"
  max_context_chunks: 5
  temperature: 0.3
  excluded_folders:           # Never send to Claude
    - "personal/finance"

watcher:
  enabled: true
  debounce_seconds: 30
  patterns:
    - "*.md"

backup:
  enabled: true
  schedule: "0 3 * * *"       # Daily at 3 AM
  retention_days: 7
  path: "/home/Arnab/clawd/backups"
```

---

## 7. Deployment

### 7.1 Prerequisites

- Docker & Docker Compose on NAS
- At least 4GB RAM available
- Clawdbot gateway running (handles Claude API)

### 7.2 Docker Compose

```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: kg-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G

  api:
    build: ./api
    container_name: kg-api
    ports:
      - "8080:8080"
    volumes:
      - /home/Arnab/clawd/projects/knowledge-graph/obsidian:/data/obsidian
      - /home/Arnab/clawd/projects/knowledge-graph/lancedb:/data/lancedb
      - ./config:/app/config
    environment:
      - OLLAMA_URL=http://ollama:11434
      - LANCEDB_PATH=/data/lancedb
      - VAULT_WORK_PATH=/data/obsidian/work
      - VAULT_PERSONAL_PATH=/data/obsidian/personal
      - CLAWDBOT_URL=http://host.docker.internal:18789
      - CLAWDBOT_TOKEN=${CLAWDBOT_TOKEN}
      - API_TOKEN=${API_TOKEN}
      - EXCLUDED_FOLDERS=personal/finance
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - ollama
    restart: unless-stopped

volumes:
  ollama_data:
```

### 7.3 Startup Sequence

1. Start containers: `docker-compose up -d`
2. Pull embedding model: `docker exec kg-ollama ollama pull nomic-embed-text`
3. Initialize tables: `curl -X POST http://localhost:8080/index/init`
4. Run full index: `curl -X POST http://localhost:8080/index/full`
5. Verify: `curl http://localhost:8080/health`

### 7.4 Backup (Daily Cron)

```bash
# /etc/cron.d/knowledge-graph-backup
0 3 * * * root cp -r /home/Arnab/clawd/projects/knowledge-graph/lancedb /home/Arnab/clawd/backups/lancedb_$(date +\%Y\%m\%d)
# Keep last 7 days
0 4 * * * root find /home/Arnab/clawd/backups -name "lancedb_*" -mtime +7 -exec rm -rf {} \;
```

---

## 8. Monitoring

### 8.1 Health Check

```http
GET /health
```

```json
{
  "status": "healthy",
  "components": {
    "ollama": "ok",
    "qdrant": "ok",
    "watcher": "running"
  },
  "stats": {
    "work_vectors": 9847,
    "personal_vectors": 423,
    "last_index": "2026-02-01T10:30:00Z"
  }
}
```

### 8.2 Logging

- Structured JSON logs
- Log levels: DEBUG, INFO, WARNING, ERROR
- Log rotation: 7 days retained

### 8.3 Alerts (Future)

- Indexing failures
- Claude API errors
- Disk space warnings

---

## 9. Security Considerations

| Concern | Mitigation |
|---------|------------|
| API access | Bearer token authentication |
| Data at rest | NAS encryption (if enabled) |
| Data in transit | HTTPS for Claude API; internal Docker network for services |
| Sensitive content | Personal vault clearly separated; can exclude from Claude context |
| API key exposure | Environment variables, not in code |

---

## 10. Future Enhancements

| Enhancement | Complexity | Value |
|-------------|------------|-------|
| Web UI | Medium | High |
| Calendar integration | Medium | High |
| Slack bot | Low | Medium |
| Local LLM option | Low | Medium |
| Mobile app | High | Medium |
| Multi-user | High | Low |

---

## 11. Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| Use Ollama on NAS (CPU) | Always available, no wake-on-LAN complexity | 2026-02-01 |
| Use Claude for answers | Higher quality than local LLM, already available via Clawdbot | 2026-02-01 |
| **Route LLM via Clawdbot gateway** | Single API key, centralized logging, model flexibility — no separate Anthropic key needed | 2026-02-01 |
| Docker Compose deployment | Isolation, easy updates, consistent environment | 2026-02-01 |
| nomic-embed-text model | Good quality, fast on CPU, large context window | 2026-02-01 |
| **LanceDB for vectors** | Embedded (no server), file-based (easy backup), simpler architecture | 2026-02-01 |
| Incremental + weekly full reindex | Balance freshness with consistency, avoid daily full reindex overhead | 2026-02-01 |
| Exclude finance/ from Claude | Privacy for sensitive financial data | 2026-02-01 |
| Daily local backup | Simple cp of LanceDB folder, 7-day retention | 2026-02-01 |

---

*Document Version History:*
- v1.0 (2026-02-01): Initial architecture
