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
