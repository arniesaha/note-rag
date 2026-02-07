# n8n Workflows

This directory contains n8n workflow configurations for automating knowledge graph tasks.

## Available Workflows

### Transcript Sync

Automatically processes and organizes meeting transcripts:

1. **Organize** — Categorize transcripts by person/project
2. **Cleanup** — Remove processed files from source
3. **Deduplication** — Handle duplicate recordings

### Reindex Trigger

Webhook to trigger knowledge graph reindexing after new files are added.

## Setup

1. Import workflows into your n8n instance
2. Configure credentials:
   - Knowledge Graph API token
   - (Optional) Notification webhook
3. Set schedule triggers as needed

## Workflow Files

Workflow JSON files are not committed (may contain tokens). Export from your n8n instance.

## Endpoints Used

```
POST /index/start      — Trigger async reindex
GET  /index/jobs       — Check job status
GET  /health           — Health check
```
