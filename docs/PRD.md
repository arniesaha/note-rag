# Knowledge Graph — Product Requirements Document

**Version:** 1.0
**Author:** Arnab + Nix
**Date:** 2026-02-01
**Status:** Draft — Pending Review

---

## 1. Overview

### 1.1 Problem Statement

As an Engineering Manager with 300+ meetings per year, valuable context is scattered across:
- Meeting notes (Granola transcripts)
- 1:1 documentation
- Project updates
- Decision records
- Personal notes

Finding relevant information requires manually searching through files, leading to:
- Lost context before 1:1s
- Forgotten decisions
- Repeated discussions
- Missed action items

### 1.2 Solution

Build a **personal knowledge system** that:
1. Automatically organizes incoming meeting notes
2. Provides intelligent search across all content
3. Surfaces relevant context proactively
4. Works across both work and personal vaults

### 1.3 Success Metrics

| Metric | Target |
|--------|--------|
| Time to find context for 1:1 | < 30 seconds |
| Query response time | < 5 seconds |
| New file auto-categorization accuracy | > 90% |
| Daily active usage | Used before every 1:1 |

---

## 2. User Stories

### 2.1 Core User Stories

**US-1: Pre-meeting Context**
> As an EM, I want to quickly get context on a person before our 1:1, so I can have a more productive conversation.

Acceptance Criteria:
- Query "prep for 1:1 with Hitesh" returns recent topics, open action items, and discussion history
- Response includes links to source notes
- Works within 5 seconds

**US-2: Decision Recall**
> As an EM, I want to recall past decisions on a topic, so I don't repeat discussions or contradict prior choices.

Acceptance Criteria:
- Query "what did we decide about the migration timeline?" returns relevant decisions with dates
- Includes context of who was involved and why

**US-3: Action Item Tracking**
> As an EM, I want to see open action items for my team, so nothing falls through the cracks.

Acceptance Criteria:
- Query "open action items for Suman" returns pending tasks
- Grouped by date/meeting
- Can filter by project

**US-4: Automatic Organization**
> As a user, I want new Granola notes to be automatically categorized, so I don't have to manually organize files.

Acceptance Criteria:
- New files detected within 5 minutes
- Correctly categorized to people/, projects/, team/, etc.
- Frontmatter added automatically

**US-5: Cross-Vault Search**
> As a user, I want to search across both work and personal vaults, so I have one interface for all my knowledge.

Acceptance Criteria:
- Single search endpoint queries both vaults
- Results indicate source vault
- Can filter by vault if needed

### 2.2 Future User Stories (v2)

- **US-6:** Weekly digest of themes and patterns
- **US-7:** Meeting prep suggestions based on calendar
- **US-8:** Integration with Slack for quick queries
- **US-9:** Voice query via mobile

---

## 3. Functional Requirements

### 3.1 File Watcher & Restructurer

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | Watch work/ and personal/ folders for new/modified files | P0 |
| FR-1.2 | Categorize files based on content and filename | P0 |
| FR-1.3 | Move files to appropriate subfolders | P0 |
| FR-1.4 | Add/update YAML frontmatter | P0 |
| FR-1.5 | Extract entities (people, projects) from content | P1 |
| FR-1.6 | Configurable watch interval (default: 5 min) | P1 |

### 3.2 Indexing Pipeline

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | Chunk documents by section/paragraph | P0 |
| FR-2.2 | Generate embeddings using nomic-embed-text | P0 |
| FR-2.3 | Store vectors in Qdrant with metadata | P0 |
| FR-2.4 | Incremental indexing (only new/changed files) | P0 |
| FR-2.5 | Full reindex capability | P1 |
| FR-2.6 | Track indexing status per file | P1 |

### 3.3 Query API

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | Semantic search across indexed content | P0 |
| FR-3.2 | Filter by vault (work/personal) | P0 |
| FR-3.3 | Filter by category (people, projects, etc.) | P0 |
| FR-3.4 | Filter by date range | P1 |
| FR-3.5 | Filter by person | P1 |
| FR-3.6 | Return source file links | P0 |

### 3.4 RAG Answers

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | Generate natural language answers using Claude | P0 |
| FR-4.2 | Include source citations in response | P0 |
| FR-4.3 | Support follow-up questions (context retention) | P2 |
| FR-4.4 | Configurable LLM (Claude/local) | P2 |

### 3.5 Specialized Endpoints

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | `/prep/{person}` — 1:1 preparation context | P0 |
| FR-5.2 | `/actions/{person}` — Open action items | P1 |
| FR-5.3 | `/decisions` — Recent decisions log | P1 |
| FR-5.4 | `/focus` — Weekly focus areas | P2 |

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1.1 | Query response time | < 5 seconds |
| NFR-1.2 | File categorization time | < 2 seconds/file |
| NFR-1.3 | Embedding generation | < 3 seconds/file |
| NFR-1.4 | Concurrent queries supported | 5 |

### 4.2 Availability

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-2.1 | Service uptime | 99% (NAS uptime) |
| NFR-2.2 | Auto-restart on failure | Yes |
| NFR-2.3 | Graceful degradation if Ollama unavailable | Yes (search-only mode) |

### 4.3 Security & Privacy

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-3.1 | All data stays on NAS | Yes |
| NFR-3.2 | No external API for embeddings | Yes (Ollama local) |
| NFR-3.3 | Claude API only for answer generation | Configurable |
| NFR-3.4 | API authentication | Bearer token |

### 4.4 Maintainability

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-4.1 | Containerized deployment | Yes |
| NFR-4.2 | Configuration via environment variables | Yes |
| NFR-4.3 | Structured logging | Yes |
| NFR-4.4 | Health check endpoint | Yes |

---

## 5. Out of Scope (v1)

- Mobile app
- Real-time sync (polling-based is fine)
- Multi-user support
- Calendar integration
- Slack bot
- Voice interface

---

## 6. Dependencies

| Dependency | Purpose | Status |
|------------|---------|--------|
| Obsidian vault on NAS | Content source | ✅ Ready |
| Granola → Obsidian sync | Work content | ✅ Working |
| Docker on NAS | Container runtime | ⬜ To verify |
| Ollama | Embeddings | ⬜ To install |
| LanceDB | Vector storage (embedded) | ⬜ To install (pip) |
| Claude API (Clawdbot) | Answer generation | ✅ Available |

---

## 7. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| NAS CPU too slow for embeddings | Slow indexing | Medium | Batch process overnight; optimize chunk size |
| Qdrant memory usage too high | NAS instability | Low | Limit collection size; use disk-backed storage |
| Poor categorization accuracy | Manual cleanup needed | Medium | Improve classification rules; add manual override |
| Granola sync breaks | Missing new notes | Low | Monitor sync; alert on failures |

---

## 8. Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Infrastructure | 1 week | Docker setup, Qdrant, Ollama on NAS |
| Phase 2: Indexing | 1 week | Embedding pipeline, file watcher |
| Phase 3: Query API | 1 week | Search endpoints, RAG integration |
| Phase 4: Polish | 1 week | Specialized endpoints, error handling |

**Total: ~4 weeks** (part-time, evenings/weekends)

---

## 9. Decisions Made

| Question | Decision |
|----------|----------|
| **UI needed for v1?** | No — API-only first, UI after APIs are stable |
| **Reindex frequency?** | Incremental on file change + weekly full reindex (Sunday 3 AM) |
| **Personal vault sensitivity?** | Exclude `personal/finance/` from Claude context |
| **Backup strategy?** | Daily local backup of LanceDB folder, 7-day retention |
| **Vector DB?** | LanceDB (embedded, file-based, easy backup) |

## 10. Open Questions

1. **Clawdbot integration** — Direct tool call or HTTP API?
2. **Authentication** — Bearer token sufficient or need more?
3. **Rate limiting** — Needed for single-user system?

---

## 10. Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Product Owner | Arnab | | ⬜ Pending |
| Developer | Nix | 2026-02-01 | ✅ Ready |

---

*Document Version History:*
- v1.0 (2026-02-01): Initial draft
