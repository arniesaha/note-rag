#!/usr/bin/env python3
"""Remove processed source files from Granola/Transcripts folder."""

import json
from pathlib import Path

STATE_FILE = Path("/home/Arnab/clawd/projects/knowledge-graph/data/sync_state.json")
GRANOLA_PATH = Path("/home/Arnab/clawd/projects/knowledge-graph/obsidian/work/Granola/Transcripts")

def main():
    with open(STATE_FILE) as f:
        state = json.load(f)
    
    removed = 0
    skipped = 0
    
    for path_str, info in state.get('processed', {}).items():
        source = Path(path_str)
        output = Path(info.get('output', path_str))
        
        # Only remove if source != output and source exists
        if source.resolve() != output.resolve() and source.exists():
            # Verify output exists before removing source
            if output.exists():
                source.unlink()
                print(f"Removed: {source.name}")
                removed += 1
            else:
                print(f"SKIP (output missing): {source.name}")
                skipped += 1
    
    print(f"\nRemoved: {removed} files")
    print(f"Skipped: {skipped} files")

if __name__ == '__main__':
    main()
