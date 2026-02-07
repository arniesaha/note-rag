# Scripts

Utility scripts for managing the knowledge graph.

## ⚠️ Configuration Required

These scripts contain hardcoded paths that you'll need to update for your environment:

- `VAULT_PATH` — Path to your Obsidian vault
- `OUTPUT_PATH` — Path for organized output
- Log file paths

Search for `/home/` or your username and update accordingly.

## Available Scripts

### daily_sync.py

Main synchronization script. Processes new transcripts and organizes them:

- Categorizes by person, project, or team
- Handles deduplication (multiple recordings of same meeting)
- Triggers reindexing via API

```bash
python3 scripts/daily_sync.py
python3 scripts/daily_sync.py --full  # Full rescan
```

### cleanup_sources.py

Removes processed source files after successful sync.

```bash
python3 scripts/cleanup_sources.py
```

### analyze_meetings.py

Analyzes meeting patterns and generates reports.

### generate_insights.py

Extracts insights and action items from meetings.

### reorganize_vault.py

One-time reorganization of existing vault structure.

### process_remaining.py

Processes any files that weren't handled by daily_sync.

## Automation

### Cron

```bash
# Daily at 6 AM
0 6 * * * cd /path/to/knowledge-graph && python3 scripts/daily_sync.py
```

### n8n

See `n8n/README.md` for workflow-based automation.
