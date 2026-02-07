#!/bin/bash
# Daily Sync for Knowledge Graph
# Cron: 0 6 * * * /home/Arnab/clawd/projects/knowledge-graph/scripts/run_daily_sync.sh

cd /home/Arnab/clawd/projects/knowledge-graph

# Run sync
/usr/bin/python3 scripts/daily_sync.py >> logs/daily_sync.log 2>&1

# Check exit status
if [ $? -eq 0 ]; then
    echo "$(date): Daily sync completed successfully" >> logs/cron.log
else
    echo "$(date): Daily sync failed" >> logs/cron.log
fi
