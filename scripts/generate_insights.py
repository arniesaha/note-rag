#!/usr/bin/env python3
"""
Generate derived insight documents for RAG from organized meeting notes.
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

ORGANIZED_PATH = Path("/home/Arnab/clawd/projects/career-agent/obsidian/organized")
INSIGHTS_PATH = ORGANIZED_PATH / "insights"
ANALYSIS_PATH = Path("/home/Arnab/clawd/projects/career-agent/analysis")

# Load analysis
with open(ANALYSIS_PATH / "meetings_analysis.json") as f:
    analysis = json.load(f)


def generate_people_profiles():
    """Generate a profile document for each person with meeting history."""
    people_path = ORGANIZED_PATH / "people"
    profiles = []
    
    if not people_path.exists():
        return
    
    for person_dir in sorted(people_path.iterdir()):
        if not person_dir.is_dir():
            continue
            
        person_name = person_dir.name.replace('-', ' ').title()
        meetings = list(person_dir.glob("*.md"))
        
        if not meetings:
            continue
        
        # Get date range
        dates = []
        topics = []
        action_items = []
        
        for meeting_file in sorted(meetings):
            # Extract date from filename
            date_match = re.match(r'(\d{4}-\d{2}-\d{2})', meeting_file.name)
            if date_match:
                dates.append(date_match.group(1))
            
            # Read content for topics
            try:
                content = meeting_file.read_text()
                
                # Extract section headers as topics
                headers = re.findall(r'^### (.+)$', content, re.MULTILINE)
                topics.extend(headers[:5])
                
                # Extract action items
                action_section = re.search(
                    r'(?:Action Items|Next Steps)[:\s]*\n((?:[-*•]\s*.+\n?)+)',
                    content, re.IGNORECASE
                )
                if action_section:
                    items = re.findall(r'[-*•]\s*(.+)', action_section.group(1))
                    action_items.extend(items[:3])
            except:
                pass
        
        # Build profile
        profile = {
            "name": person_name,
            "slug": person_dir.name,
            "meeting_count": len(meetings),
            "first_meeting": min(dates) if dates else "unknown",
            "last_meeting": max(dates) if dates else "unknown",
            "common_topics": list(set(topics))[:10],
            "recent_action_items": action_items[-5:],
        }
        profiles.append(profile)
    
    # Write profiles document
    INSIGHTS_PATH.mkdir(parents=True, exist_ok=True)
    
    output = ["# People Profiles\n"]
    output.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d')}*\n")
    output.append("Quick reference for 1:1s and team context.\n")
    
    # Sort by meeting count
    profiles.sort(key=lambda x: -x['meeting_count'])
    
    for p in profiles[:50]:  # Top 50 people
        output.append(f"\n## {p['name']}\n")
        output.append(f"- **Meetings:** {p['meeting_count']}")
        output.append(f"- **Active:** {p['first_meeting']} to {p['last_meeting']}")
        
        if p['common_topics']:
            output.append(f"- **Topics:** {', '.join(p['common_topics'][:5])}")
        
        if p['recent_action_items']:
            output.append(f"- **Recent Actions:**")
            for item in p['recent_action_items'][:3]:
                output.append(f"  - {item[:100]}")
        
        output.append(f"- **Notes:** [[people/{p['slug']}]]")
    
    with open(INSIGHTS_PATH / "people-profiles.md", 'w') as f:
        f.write('\n'.join(output))
    
    print(f"Generated profiles for {len(profiles)} people")
    return profiles


def generate_project_status():
    """Generate project status summary from recent meetings."""
    projects_path = ORGANIZED_PATH / "projects"
    
    output = ["# Project Status\n"]
    output.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d')}*\n")
    
    project_info = {
        "bedrock": {
            "name": "Project Bedrock",
            "description": "Enterprise scale/performance initiative - 1B assets, 100k users, right-sizing",
        },
        "lean-graph": {
            "name": "Lean Graph",
            "description": "ID graph optimization - database reliability, shadow deployment",
        },
        "cost-optimization": {
            "name": "Cost Optimization",
            "description": "Right-sizing, GCP/AWS/Azure cost reduction initiatives",
        },
        "polaris": {
            "name": "Polaris",
            "description": "Platform initiative",
        },
        "migrations": {
            "name": "Migrations",
            "description": "Data and system migrations",
        },
    }
    
    if projects_path.exists():
        for project_dir in sorted(projects_path.iterdir()):
            if not project_dir.is_dir():
                continue
            
            project_slug = project_dir.name
            info = project_info.get(project_slug, {"name": project_slug.title(), "description": ""})
            
            meetings = sorted(project_dir.glob("*.md"), reverse=True)
            
            output.append(f"\n## {info['name']}\n")
            output.append(f"{info['description']}\n")
            output.append(f"**Meeting Count:** {len(meetings)}")
            
            if meetings:
                # Get most recent meeting summary
                recent = meetings[0]
                date_match = re.match(r'(\d{4}-\d{2}-\d{2})', recent.name)
                if date_match:
                    output.append(f"**Last Update:** {date_match.group(1)}")
                
                try:
                    content = recent.read_text()
                    # Extract key points
                    headers = re.findall(r'^### (.+)$', content, re.MULTILINE)
                    if headers:
                        output.append(f"**Recent Topics:** {', '.join(headers[:5])}")
                except:
                    pass
            
            output.append(f"**Notes:** [[projects/{project_slug}]]")
    
    with open(INSIGHTS_PATH / "project-status.md", 'w') as f:
        f.write('\n'.join(output))
    
    print("Generated project status")


def generate_recent_decisions():
    """Extract recent decisions from meetings."""
    output = ["# Decisions Log\n"]
    output.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d')}*\n")
    output.append("Key decisions extracted from recent meetings.\n")
    
    decisions = []
    
    # Scan recent files for decision-like content
    for md_file in ORGANIZED_PATH.rglob("*.md"):
        if 'insights' in str(md_file):
            continue
            
        try:
            content = md_file.read_text()
            
            # Look for decision patterns
            decision_patterns = [
                r'(?:decided|decision|agreed|approved)[:\s]+(.+?)(?:\n|$)',
                r'(?:will|going to)\s+(?:proceed|move forward)\s+with\s+(.+?)(?:\n|$)',
            ]
            
            for pattern in decision_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if len(match) > 20 and len(match) < 200:
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', str(md_file))
                        date = date_match.group(1) if date_match else 'unknown'
                        decisions.append({
                            "date": date,
                            "decision": match.strip(),
                            "source": md_file.name,
                        })
        except:
            pass
    
    # Sort by date, most recent first
    decisions.sort(key=lambda x: x['date'], reverse=True)
    
    # Group by month
    by_month = defaultdict(list)
    for d in decisions[:100]:
        month = d['date'][:7] if d['date'] != 'unknown' else 'unknown'
        by_month[month].append(d)
    
    for month in sorted(by_month.keys(), reverse=True)[:6]:
        output.append(f"\n## {month}\n")
        for d in by_month[month][:10]:
            output.append(f"- **{d['date']}:** {d['decision']}")
            output.append(f"  - Source: {d['source']}")
    
    with open(INSIGHTS_PATH / "decisions-log.md", 'w') as f:
        f.write('\n'.join(output))
    
    print(f"Extracted {len(decisions)} decisions")


def generate_action_items():
    """Extract open action items from recent meetings."""
    output = ["# Action Items\n"]
    output.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d')}*\n")
    output.append("Action items from recent meetings (may include completed items).\n")
    
    all_actions = []
    
    # Scan recent files
    for md_file in ORGANIZED_PATH.rglob("*.md"):
        if 'insights' in str(md_file):
            continue
            
        try:
            content = md_file.read_text()
            
            # Find action items sections
            action_section = re.search(
                r'(?:Action Items|Next Steps|Follow.?ups?)[:\s]*\n((?:[-*•]\s*.+\n?)+)',
                content, re.IGNORECASE
            )
            
            if action_section:
                items = re.findall(r'[-*•]\s*(.+)', action_section.group(1))
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', str(md_file))
                date = date_match.group(1) if date_match else 'unknown'
                
                for item in items:
                    # Extract owner if mentioned
                    owner_match = re.match(r'^([A-Z][a-z]+)[:\s]', item)
                    owner = owner_match.group(1) if owner_match else None
                    
                    all_actions.append({
                        "date": date,
                        "item": item.strip()[:150],
                        "owner": owner,
                        "source": md_file.name,
                    })
        except:
            pass
    
    # Sort by date
    all_actions.sort(key=lambda x: x['date'], reverse=True)
    
    # Recent actions (last 30 days worth)
    output.append("\n## Recent Action Items\n")
    
    by_owner = defaultdict(list)
    for a in all_actions[:200]:
        owner = a['owner'] or 'Unassigned'
        by_owner[owner].append(a)
    
    for owner in sorted(by_owner.keys()):
        items = by_owner[owner][:10]
        if items:
            output.append(f"\n### {owner}\n")
            for a in items:
                output.append(f"- [{a['date']}] {a['item']}")
    
    with open(INSIGHTS_PATH / "action-items.md", 'w') as f:
        f.write('\n'.join(output))
    
    print(f"Extracted {len(all_actions)} action items")


def generate_topics_index():
    """Generate an index of common topics."""
    output = ["# Topics Index\n"]
    output.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d')}*\n")
    
    topics = defaultdict(int)
    
    for md_file in ORGANIZED_PATH.rglob("*.md"):
        if 'insights' in str(md_file):
            continue
            
        try:
            content = md_file.read_text()
            headers = re.findall(r'^### (.+)$', content, re.MULTILINE)
            for h in headers:
                # Normalize
                h_clean = h.strip().lower()
                if len(h_clean) > 5 and len(h_clean) < 50:
                    topics[h_clean] += 1
        except:
            pass
    
    # Sort by frequency
    sorted_topics = sorted(topics.items(), key=lambda x: -x[1])
    
    output.append("## Most Common Topics\n")
    output.append("| Topic | Occurrences |")
    output.append("|-------|-------------|")
    for topic, count in sorted_topics[:50]:
        output.append(f"| {topic.title()} | {count} |")
    
    with open(INSIGHTS_PATH / "topics-index.md", 'w') as f:
        f.write('\n'.join(output))
    
    print(f"Indexed {len(topics)} unique topics")


if __name__ == "__main__":
    print("Generating insights...")
    
    generate_people_profiles()
    generate_project_status()
    generate_recent_decisions()
    generate_action_items()
    generate_topics_index()
    
    print(f"\nInsights saved to: {INSIGHTS_PATH}")
