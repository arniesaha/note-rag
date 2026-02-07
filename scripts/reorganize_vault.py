#!/usr/bin/env python3
"""
Reorganize Granola meeting notes into a structured folder hierarchy.
"""

import os
import re
import json
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict

VAULT_PATH = Path("/home/Arnab/clawd/projects/career-agent/obsidian/vault")
OUTPUT_PATH = Path("/home/Arnab/clawd/projects/career-agent/obsidian/organized")
ANALYSIS_PATH = Path("/home/Arnab/clawd/projects/career-agent/analysis")

# Load analysis
with open(ANALYSIS_PATH / "meetings_analysis.json") as f:
    analysis = json.load(f)


def slugify(text):
    """Convert text to a safe filename slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')[:50]


def extract_date_from_meeting(meeting):
    """Extract date from meeting created field or source file."""
    if meeting.get('created'):
        try:
            dt = datetime.fromisoformat(meeting['created'].replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except:
            pass
    
    # Try source file name
    source = meeting.get('source_file', '')
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', source)
    if date_match:
        return date_match.group(1)
    
    return 'unknown-date'


def extract_person_from_1on1(title):
    """Extract the other person's name from a 1:1 meeting title."""
    # Patterns: "Person / Arnab", "Person <> Arnab", "Arnab / Person"
    patterns = [
        r'^(.+?)\s*[/<>]+\s*Arnab',
        r'^Arnab\s*[/<>]+\s*(.+)',
        r'^\(W\)\s*Arnab[/<>]+(.+)',
        r'^\(W\)\s*(.+?)[/<>]+\s*Arnab',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, title, re.IGNORECASE)
        if match:
            person = match.group(1).strip()
            # Clean up
            person = re.sub(r'\s*[-–]\s*\d+.*$', '', person)  # Remove dates
            person = re.sub(r'\s*[-–]\s*H[12].*$', '', person)  # Remove H1/H2
            person = re.sub(r'\s*<>.*$', '', person)
            person = re.sub(r'\s*[/<].*$', '', person)
            return person.strip()
    
    return None


def get_output_path(meeting):
    """Determine the output path for a meeting."""
    category = meeting.get('category', 'other')
    title = meeting.get('title', 'untitled')
    date = extract_date_from_meeting(meeting)
    
    if category == '1on1':
        person = extract_person_from_1on1(title)
        if person:
            person_slug = slugify(person)
            return OUTPUT_PATH / 'people' / person_slug / f"{date}-{slugify(title)}.md"
    
    elif category == 'daily_standup':
        if 'metastore' in title.lower():
            return OUTPUT_PATH / 'team' / 'metastore-daily' / f"{date}.md"
        elif 'lakehouse' in title.lower() or 'mdlh' in title.lower():
            return OUTPUT_PATH / 'team' / 'lakehouse-daily' / f"{date}.md"
        else:
            return OUTPUT_PATH / 'team' / 'standups' / f"{date}-{slugify(title)}.md"
    
    elif category == 'weekly':
        return OUTPUT_PATH / 'team' / 'weekly' / f"{date}-{slugify(title)}.md"
    
    elif category == 'project':
        # Determine which project
        title_lower = title.lower()
        if 'bedrock' in title_lower:
            return OUTPUT_PATH / 'projects' / 'bedrock' / f"{date}-{slugify(title)}.md"
        elif 'lean' in title_lower or 'graph' in title_lower:
            return OUTPUT_PATH / 'projects' / 'lean-graph' / f"{date}-{slugify(title)}.md"
        elif 'polaris' in title_lower:
            return OUTPUT_PATH / 'projects' / 'polaris' / f"{date}-{slugify(title)}.md"
        elif 'migration' in title_lower:
            return OUTPUT_PATH / 'projects' / 'migrations' / f"{date}-{slugify(title)}.md"
        else:
            return OUTPUT_PATH / 'projects' / 'other' / f"{date}-{slugify(title)}.md"
    
    elif category == 'interview':
        return OUTPUT_PATH / 'interviews' / f"{date}-{slugify(title)}.md"
    
    elif category == 'incident':
        return OUTPUT_PATH / 'incidents' / f"{date}-{slugify(title)}.md"
    
    elif category == 'cross_team':
        return OUTPUT_PATH / 'cross-team' / f"{date}-{slugify(title)}.md"
    
    elif category == 'cost_review':
        return OUTPUT_PATH / 'projects' / 'cost-optimization' / f"{date}-{slugify(title)}.md"
    
    # Default: other
    return OUTPUT_PATH / 'other' / f"{date}-{slugify(title)}.md"


def read_meeting_content(meeting):
    """Read the full content of a meeting from its source file."""
    source_file = meeting.get('source_file')
    title = meeting.get('title')
    
    if not source_file or not os.path.exists(source_file):
        return None
    
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return None
    
    # Find this meeting's section in the file
    # Split by ## headers and find the matching section
    sections = re.split(r'\n(?=## )', content)
    
    for section in sections:
        if not section:
            continue
        # Get first line properly
        lines = section.split('\n')
        first_line = lines[0] if lines else ''
        section_title = first_line.lstrip('#').strip()
        
        if section_title == title:
            return section
        
        # Also try partial match for titles with special chars
        if title and section_title and (title in section_title or section_title in title):
            return section
    
    # Fallback: try regex with more flexible matching
    escaped_title = re.escape(title)
    pattern = rf'(## {escaped_title}.*?)(?=\n## (?!Granola)|\Z)'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        return match.group(1)
    
    return None


def add_frontmatter(content, meeting):
    """Add YAML frontmatter to meeting content."""
    date = extract_date_from_meeting(meeting)
    
    frontmatter = [
        "---",
        f"title: \"{meeting.get('title', 'Untitled')}\"",
        f"date: {date}",
        f"category: {meeting.get('category', 'other')}",
    ]
    
    if meeting.get('people'):
        people_list = ', '.join(f'"{p}"' for p in meeting['people'][:10])
        frontmatter.append(f"people: [{people_list}]")
    
    if meeting.get('projects'):
        projects_list = ', '.join(f'"{p}"' for p in meeting['projects'])
        frontmatter.append(f"projects: [{projects_list}]")
    
    if meeting.get('granola_id'):
        frontmatter.append(f"granola_id: {meeting['granola_id']}")
    
    if meeting.get('transcript_link'):
        frontmatter.append(f"transcript: {meeting['transcript_link']}")
    
    frontmatter.append("---\n")
    
    return '\n'.join(frontmatter) + content


def reorganize():
    """Main reorganization function."""
    meetings = analysis['meetings']
    print(f"Processing {len(meetings)} meetings...")
    
    # Create output directories
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    
    stats = defaultdict(int)
    errors = []
    
    for meeting in meetings:
        try:
            # Get output path
            output_path = get_output_path(meeting)
            
            # Read content
            content = read_meeting_content(meeting)
            if not content:
                errors.append(f"Could not read: {meeting.get('title')}")
                continue
            
            # Add frontmatter
            final_content = add_frontmatter(content, meeting)
            
            # Write file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            stats[meeting.get('category', 'other')] += 1
            
        except Exception as e:
            errors.append(f"Error processing {meeting.get('title')}: {e}")
    
    print(f"\nReorganization complete!")
    print(f"Stats: {dict(stats)}")
    print(f"Total processed: {sum(stats.values())}")
    print(f"Errors: {len(errors)}")
    
    if errors[:10]:
        print(f"\nFirst 10 errors:")
        for e in errors[:10]:
            print(f"  - {e}")
    
    return stats, errors


if __name__ == "__main__":
    stats, errors = reorganize()
    
    # Save reorganization report
    with open(ANALYSIS_PATH / "reorganization_report.json", 'w') as f:
        json.dump({
            "stats": dict(stats),
            "errors": errors,
            "output_path": str(OUTPUT_PATH),
        }, f, indent=2)
