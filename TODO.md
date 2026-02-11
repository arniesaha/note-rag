# note-rag TODO

## 🔴 URGENT: Sync Broken (Feb 11, 2026)
- Granola transcript sync stopped after Feb 6
- No meeting files from Feb 7-11 present
- **Action:** Check n8n workflow or daily_sync.py script

## 🔴 BUG: Hybrid Search Broken
- FTS search failing with `sqlite3.OperationalError: no such column: 1`
- Happens when using `person` filter
- **Workaround:** Use `mode: "vector"` instead of `hybrid`
- **Fix:** Debug SQL query construction in `fts_index.py` search method

---

## Observability Dashboard (P1)

Build dedicated monitoring for note-rag tracking P50/P95/P99 latencies.

### Metrics to Track
- **Latency (P50/P95/P99)** per endpoint:
  - `/search` (by mode: vector, bm25, hybrid, query)
  - `/query` (RAG)
  - `/prep/{person}`
  - `/index/start`
- **Request count** per endpoint
- **Error rate** per endpoint
- **Index stats:**
  - Vector count (work/personal)
  - FTS count (work/personal)
  - Last index time
  - Index job duration

### Implementation: Prometheus + Grafana

```python
# Add to requirements.txt
prometheus-fastapi-instrumentator==6.1.0

# Add to main.py
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

Then:
1. Scrape `/metrics` endpoint with Prometheus
2. Build Grafana dashboard with:
   - Request rate panel
   - Latency histogram (P50/P95/P99)
   - Error rate panel
   - Index health panel

---

## PDF Support (Planned)
- [ ] Add separate PDF paths alongside vaults
  - `vault_work_pdfs_path: str = "/data/pdfs/work"`
  - `vault_personal_pdfs_path: str = "/data/pdfs/personal"`
- [ ] Add PyMuPDF (fitz) for PDF extraction
- [ ] Page-aware chunking with page number metadata
- [ ] Update indexer to handle both `.md` and `.pdf`

## Google Workspace Docs (Manual Export Approach)
- [ ] Export Google Docs/Sheets as PDF from work laptop
- [ ] Place in `/data/pdfs/work/` folder
- [ ] Index via PDF loader (once implemented)

**Workflow:**
1. Open Google Doc/Sheet
2. File → Download → PDF
3. Save to `pdfs/work/` folder (synced to NAS)
4. Trigger reindex

*Simpler than full API integration — no auth setup needed*
