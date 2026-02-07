# note-rag Services

Docker-based services for the note-rag system.

## Quick Start

### 1. Setup Environment

```bash
# Copy and edit environment file
cp .env.example .env
# Edit .env with your settings
```

### 2. Configure Vault Paths

Edit `docker-compose.yml` or set environment variables:

```bash
export OBSIDIAN_PATH=/path/to/your/obsidian/vault
export LANCEDB_PATH=/path/to/lancedb/storage
```

### 3. Start Services

```bash
docker compose up -d

# Pull embedding models (first time)
docker exec kg-ollama ollama pull nomic-embed-text
docker exec kg-ollama ollama pull qwen2.5:0.5b  # For reranking
```

### 4. Initialize & Index

```bash
# Run full index
curl -X POST http://localhost:8080/index/start \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"vault": "all", "full": true}'

# Check status
curl http://localhost:8080/index/jobs \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

### 5. Test

```bash
# Health check
curl http://localhost:8080/health

# Search (hybrid mode)
curl -X POST http://localhost:8080/search \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "project timeline", "mode": "hybrid", "limit": 5}'

# Query with LLM answer
curl -X POST http://localhost:8080/query \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What did we decide about the migration?"}'
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| `kg-ollama` | 11434 | Ollama (embeddings + reranking) |
| `kg-api` | 8080 | FastAPI application |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ping` | GET | Fast liveness check |
| `/health` | GET | Full health check |
| `/search` | POST | Hybrid search (BM25 + Vector) |
| `/query` | POST | RAG query with LLM answer |
| `/prep/{person}` | GET | 1:1 preparation context |
| `/actions` | GET | Open action items |
| `/index/start` | POST | Start async indexing |
| `/index/jobs` | GET | List indexing jobs |
| `/index/status/{job_id}` | GET | Job status |
| `/stats` | GET | Index statistics |

## Search Modes

| Mode | Description |
|------|-------------|
| `hybrid` | BM25 + Vector + RRF fusion (default, recommended) |
| `query` | Full pipeline with expansion + reranking |
| `vector` | Pure semantic search |
| `bm25` | Pure keyword search |

## Logs

```bash
docker logs -f kg-api
docker logs -f kg-ollama
```

## Troubleshooting

### Ollama not ready

```bash
docker exec kg-ollama ollama list
docker exec kg-ollama ollama pull nomic-embed-text
```

### API can't connect to Ollama

```bash
docker compose down && docker compose up -d
```

### Reindex needed

```bash
curl -X POST http://localhost:8080/index/start \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"vault": "all", "full": true}'
```
