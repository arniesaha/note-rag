# Recall TODO

## 🎉 Rebranded from note-rag → Recall (Feb 13, 2026)

---

## 🔴 Known Issues

### Sync Broken (Feb 11, 2026)
- Granola transcript sync stopped after Feb 6
- No meeting files from Feb 7-11 present
- **Action:** Check n8n workflow or daily_sync.py script

### Hybrid Search Bug
- FTS search failing with `sqlite3.OperationalError: no such column: 1`
- Happens when using `person` filter
- **Workaround:** Use `mode: "vector"` instead of `hybrid`
- **Fix:** Debug SQL query construction in `fts_index.py` search method

---

## ✅ Completed

### PDF Support (Feb 13, 2026)
- [x] PyMuPDF for text extraction
- [x] Page-aware chunking with `page_number` metadata
- [x] `source_type` field ("markdown" or "pdf")
- [x] Helm chart PDFs volume mount
- [x] 11 work PDFs added to `/data/pdfs/work/`

### API Documentation (Feb 13, 2026)
- [x] Full API reference at `/docs/API.md`
- [x] OpenAPI auto-generated at `/docs`, `/redoc`

---

## 🚀 UI Roadmap

### Phase 1 — Read & Search (MVP)
- [ ] Browse notes by folder tree
- [ ] Semantic + keyword search
- [ ] Note viewer (Markdown rendered)
- [ ] PDF viewer with page navigation
- [ ] 1:1 prep dashboard
- [ ] Mobile-responsive design
- [ ] Dark mode

**Tech stack:** React + Tailwind (or simple FastAPI templates)

### Phase 2 — Write & Capture
- [ ] Create new notes (web editor)
- [ ] Edit existing notes
- [ ] Quick capture (mobile-friendly input)
- [ ] Upload PDFs via UI
- [ ] Tag management

### Phase 3 — Intelligence
- [ ] Daily digest ("What happened today")
- [ ] Meeting prep auto-generation
- [ ] Action item extraction & tracking
- [ ] "Related notes" suggestions
- [ ] Timeline view

### Phase 4 — Collaboration (Future)
- [ ] Share notes/searches
- [ ] Team knowledge base mode
- [ ] Access controls

---

## 🔧 Backend Improvements

### Observability (P1)
- [ ] Prometheus metrics endpoint (already added)
- [ ] Grafana dashboard for latencies
- [ ] Index health monitoring

### Performance
- [ ] Batch embedding requests
- [ ] Incremental FTS updates
- [ ] Query caching

### Data Sources
- [ ] Auto-sync from Granola (fix broken sync)
- [ ] Calendar integration for meeting context
- [ ] Email ingestion (future)

---

## 📦 Deployment

**Docker Image:** `localhost:5000/recall-api:latest`
**Helm Release:** `recall`
**Domain:** `recall.arnabsaha.com`
**k8s Namespace:** `apps`

**Paths:**
- Obsidian vault: `/home/Arnab/clawd/projects/recall/obsidian`
- LanceDB: `/home/Arnab/clawd/projects/recall/lancedb`
- PDFs: `/home/Arnab/clawd/projects/recall/data/pdfs`
