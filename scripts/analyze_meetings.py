#!/usr/bin/env python3
"""
Analyze Granola meeting notes and categorize them.
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

VAULT_PATH = Path("/home/Arnab/clawd/projects/career-agent/obsidian/vault")
OUTPUT_PATH = Path("/home/Arnab/clawd/projects/career-agent/analysis")

# Patterns to identify meeting types
PATTERNS = {
    "1on1": [
        r"^(.+?)\s*[/<>]\s*Arnab",  # "Hitesh / Arnab" or "Hitesh <> Arnab"
        r"^Arnab\s*[/<>]\s*(.+)",   # "Arnab / Hitesh"
    ],
    "daily_standup": [
        r"(?:Metastore|Lakehouse|Platform)\s*[-–]\s*Daily",
        r"Daily\s+(?:Standup|Sync|Cadence)",
    ],
    "weekly": [
        r"Weekly",
        r"Project Bedrock\s*[-–]\s*Weekly",
    ],
    "cost_review": [
        r"Cost",
        r"Right.?sizing",
    ],
    "cross_team": [
        r"Support\s*<>",
        r"EPD\s+(?:Brain|Town|Sync)",
        r"Cross\s*Team",
        r"Platform\s+EM",
    ],
    "interview": [
        r"Work Experience.*Deep Dive",
        r"Challenge.*Deep Dive",
        r"Standard.*Deep Dive",
        r"Interview",
    ],
    "incident": [
        r"Incident",
        r"Outage",
        r"P[0-2]\s",
    ],
    "project": [
        r"Project\s+Bedrock",
        r"Lean\s*Graph",
        r"Polaris",
        r"Migration",
    ],
}

# Known people (will be expanded dynamically)
KNOWN_PEOPLE = set([
    "Hitesh", "Mohit", "Sriram", "Suman", "Suraj", "Sameer", "Krishna",
    "Nikhil", "Pratham", "Daniel", "Vijay", "Anshul", "Dhanya", "Mukund",
    "Chandru", "Gopi", "Mani", "Aarshi", "Aayush", "Birendra", "Kunal",
    "Muni", "Muniraju", "Rajat", "Rittik", "Suchit", "Nobal"
])


def extract_meetings_from_file(filepath):
    """Extract individual meetings from a daily file."""
    meetings = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return meetings
    
    # Split by meeting headers (## Title)
    # Pattern: ## Meeting Title followed by metadata
    meeting_pattern = r'^## (.+?)$\n(?:\*\*Granola ID:\*\* ([a-f0-9-]+))?'
    
    # Split content into sections
    sections = re.split(r'\n(?=## (?!Granola Notes))', content)
    
    for section in sections:
        if not section.strip() or section.strip().startswith("## Granola Notes"):
            continue
            
        # Extract title
        title_match = re.match(r'^## (.+?)$', section, re.MULTILINE)
        if not title_match:
            continue
            
        title = title_match.group(1).strip()
        
        # Extract Granola ID
        id_match = re.search(r'\*\*Granola ID:\*\* ([a-f0-9-]+)', section)
        granola_id = id_match.group(1) if id_match else None
        
        # Extract dates
        created_match = re.search(r'\*\*Created:\*\* ([^\n]+)', section)
        created = created_match.group(1) if created_match else None
        
        # Extract transcript link
        link_match = re.search(r'https://notes\.granola\.ai/t/([a-f0-9-]+)', section)
        transcript_link = link_match.group(0) if link_match else None
        
        meetings.append({
            "title": title,
            "granola_id": granola_id,
            "created": created,
            "transcript_link": transcript_link,
            "content": section,
            "source_file": str(filepath),
        })
    
    return meetings


def categorize_meeting(title):
    """Categorize a meeting based on its title."""
    title_lower = title.lower()
    
    # Check each pattern category
    for category, patterns in PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, title, re.IGNORECASE):
                return category
    
    return "other"


def extract_people(title, content):
    """Extract people mentioned in meeting."""
    people = set()
    
    # Check title for 1:1 pattern
    for pattern in PATTERNS["1on1"]:
        match = re.match(pattern, title, re.IGNORECASE)
        if match:
            person = match.group(1).strip()
            # Clean up common suffixes
            person = re.sub(r'\s*[-–]\s*\d+.*$', '', person)
            person = re.sub(r'\s*<>.*$', '', person)
            people.add(person)
    
    # Check for known people in content
    for person in KNOWN_PEOPLE:
        if re.search(rf'\b{person}\b', content, re.IGNORECASE):
            people.add(person)
    
    return list(people)


def extract_action_items(content):
    """Extract action items from meeting content."""
    actions = []
    
    # Look for action items section
    action_section = re.search(
        r'(?:Action Items|Next Steps|Follow.?ups?)[:\s]*\n((?:[-*•]\s*.+\n?)+)',
        content, re.IGNORECASE
    )
    
    if action_section:
        items = re.findall(r'[-*•]\s*(.+)', action_section.group(1))
        actions.extend(items)
    
    return actions


def extract_projects(content):
    """Extract project references from content."""
    projects = set()
    
    project_patterns = [
        (r'Project\s+Bedrock', 'Project Bedrock'),
        (r'Lean\s*Graph', 'Lean Graph'),
        (r'Metastore', 'Metastore'),
        (r'Lake\s*house', 'Lakehouse'),
        (r'Context\s*Store', 'Context Store'),
        (r'Polaris', 'Polaris'),
        (r'Cassandra\s+Operator', 'Cassandra Operator'),
    ]
    
    for pattern, name in project_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            projects.add(name)
    
    return list(projects)


def analyze_vault():
    """Analyze all meetings in the vault."""
    all_meetings = []
    stats = defaultdict(int)
    people_meetings = defaultdict(list)
    project_meetings = defaultdict(list)
    
    # Process all markdown files
    for md_file in VAULT_PATH.rglob("*.md"):
        # Skip hidden files and special files
        if md_file.name.startswith('.') or md_file.name.startswith('_'):
            continue
            
        meetings = extract_meetings_from_file(md_file)
        
        for meeting in meetings:
            # Categorize
            category = categorize_meeting(meeting["title"])
            meeting["category"] = category
            stats[category] += 1
            
            # Extract people
            people = extract_people(meeting["title"], meeting["content"])
            meeting["people"] = people
            for person in people:
                people_meetings[person].append(meeting["title"])
            
            # Extract projects
            projects = extract_projects(meeting["content"])
            meeting["projects"] = projects
            for project in projects:
                project_meetings[project].append(meeting["title"])
            
            # Extract action items
            actions = extract_action_items(meeting["content"])
            meeting["action_items"] = actions
            
            all_meetings.append(meeting)
    
    return {
        "meetings": all_meetings,
        "stats": dict(stats),
        "people": {k: len(v) for k, v in people_meetings.items()},
        "people_details": dict(people_meetings),
        "projects": {k: len(v) for k, v in project_meetings.items()},
        "total": len(all_meetings),
    }


def generate_report(analysis):
    """Generate a markdown report of the analysis."""
    report = []
    report.append("# Meeting Analysis Report\n")
    report.append(f"**Generated:** {datetime.now().isoformat()}\n")
    report.append(f"**Total Meetings:** {analysis['total']}\n")
    
    # Category breakdown
    report.append("\n## Meeting Categories\n")
    report.append("| Category | Count |")
    report.append("|----------|-------|")
    for cat, count in sorted(analysis['stats'].items(), key=lambda x: -x[1]):
        report.append(f"| {cat} | {count} |")
    
    # People breakdown
    report.append("\n## People (by meeting count)\n")
    report.append("| Person | Meetings |")
    report.append("|--------|----------|")
    for person, count in sorted(analysis['people'].items(), key=lambda x: -x[1])[:30]:
        report.append(f"| {person} | {count} |")
    
    # Projects breakdown
    report.append("\n## Projects (by mention count)\n")
    report.append("| Project | Mentions |")
    report.append("|---------|----------|")
    for project, count in sorted(analysis['projects'].items(), key=lambda x: -x[1]):
        report.append(f"| {project} | {count} |")
    
    # Sample meetings by category
    report.append("\n## Sample Meetings by Category\n")
    by_category = defaultdict(list)
    for m in analysis['meetings']:
        by_category[m['category']].append(m['title'])
    
    for cat in sorted(by_category.keys()):
        report.append(f"\n### {cat}\n")
        for title in by_category[cat][:5]:
            report.append(f"- {title}")
    
    return "\n".join(report)


if __name__ == "__main__":
    print("Analyzing vault...")
    OUTPUT_PATH.mkdir(exist_ok=True)
    
    analysis = analyze_vault()
    
    # Save raw analysis
    with open(OUTPUT_PATH / "meetings_analysis.json", 'w') as f:
        # Don't include full content in JSON (too large)
        export = {
            "stats": analysis["stats"],
            "people": analysis["people"],
            "projects": analysis["projects"],
            "total": analysis["total"],
            "meetings": [
                {k: v for k, v in m.items() if k != "content"}
                for m in analysis["meetings"]
            ]
        }
        json.dump(export, f, indent=2, default=str)
    
    # Generate report
    report = generate_report(analysis)
    with open(OUTPUT_PATH / "ANALYSIS_REPORT.md", 'w') as f:
        f.write(report)
    
    print(f"Analysis complete!")
    print(f"Total meetings: {analysis['total']}")
    print(f"Categories: {analysis['stats']}")
    print(f"\nReport saved to: {OUTPUT_PATH / 'ANALYSIS_REPORT.md'}")
