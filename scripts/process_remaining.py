#!/usr/bin/env python3
"""
Process remaining vault content (non-Granola daily files).
- Work content → organized vault
- Personal content → personal vault
- Skip outdated/partial content
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict

VAULT_PATH = Path("/home/Arnab/clawd/projects/career-agent/obsidian/vault")
ORGANIZED_PATH = Path("/home/Arnab/clawd/projects/career-agent/obsidian/organized")
PERSONAL_PATH = Path("/home/Arnab/clawd/projects/career-agent/obsidian/personal")

# Content classification keywords
PERSONAL_KEYWORDS = [
    'richie', 'daycare', 'pet', 'grocery', 'medical claim', 'health',
    'retinal', 'ffa', 'oct', 'bridal', 'kamloops', 'vacation', 'trip',
    'pr card', 'immigration', 'driving license', 'passport', 'visa',
    'investment', 'portfolio', 'stocks', 'rrsp', 'tfsa', 'tax',
    'apartment', 'rent', 'lease', 'furniture', 'ikea',
    'books to read', 'meditat', 'personal', 'family', 'wedding',
    'rogers', 'telus', 'shaw', 'hydro', 'utilities', 'insurance',
    'doctor', 'dentist', 'clinic', 'prescription', 'pharmacy',
]

WORK_KEYWORDS = [
    'atlan', 'metastore', 'lakehouse', 'bedrock', 'polaris', 'phoenix',
    'kubernetes', 'k8s', 'argocd', 'helm', 'terraform', 'aws', 'gcp', 'azure',
    'cassandra', 'elasticsearch', 'kafka', 'redis', 'postgres',
    '1 on 1', '1:1', 'standup', 'sprint', 'roadmap', 'okr', 'kpi',
    'customer', 'tenant', 'enterprise', 'saas', 'production', 'staging',
    'incident', 'oncall', 'on-call', 'pagerduty', 'alert', 'outage',
    'engineering', 'platform', 'infrastructure', 'devops', 'sre',
    'pr review', 'code review', 'deploy', 'release', 'rollout',
    'jira', 'linear', 'github', 'gitlab', 'confluence',
    'interview', 'hiring', 'candidate', 'performance review',
    'manager', 'leadership', 'team', 'epd', 'product',
]

SKIP_PATTERNS = [
    r'^\.', r'\.DS_Store', r'_index\.md$', r'^Media$',
]

stats = defaultdict(int)
processed_files = []
skipped_files = []


def slugify(text):
    """Convert text to safe filename."""
    text = str(text).lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')[:60]


def should_skip(filepath):
    """Check if file should be skipped."""
    name = filepath.name
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, name):
            return True
    return False


def get_file_content(filepath):
    """Read file content safely."""
    try:
        return filepath.read_text(encoding='utf-8')
    except Exception as e:
        return None


def classify_content(filepath, content):
    """Classify content as 'work', 'personal', or 'skip'."""
    name = filepath.name.lower()
    path_str = str(filepath).lower()
    content_lower = (content or '').lower()[:5000]  # First 5k chars
    
    # Check path-based hints first
    if '/atlan/' in path_str and '/apple notes/' not in path_str:
        return 'work'
    if '/lakehouse/' in path_str:
        return 'work'
    if '/metastore/' in path_str:
        return 'work'
    if '/project bedrock/' in path_str:
        return 'work'
    if '/team - 2026/' in path_str:
        return 'work'
    if '/performance review/' in path_str:
        return 'work'
    
    # Check for personal content in Apple Notes
    if '/apple notes/' in path_str:
        # Check subfolders
        if '/health/' in path_str or '/medical/' in path_str:
            return 'personal'
        if '/canada/' in path_str:
            # Canada folder has mixed content
            for kw in ['pr card', 'immigration', 'driving', 'richie', 'pet', 'address']:
                if kw in name or kw in content_lower:
                    return 'personal'
            for kw in ['interview prep', 'job apply', 'tetrate']:
                if kw in name or kw in content_lower:
                    return 'work'
            return 'personal'  # Default Canada stuff to personal
        if '/accounts/' in path_str:
            return 'personal'
        if '/imported notes/' in path_str:
            return 'skip'  # Often duplicates or fragments
        
        # Check content for Apple Notes/Atlan subfolder
        if '/atlan/' in path_str:
            return 'work'
    
    # Score based on keywords
    work_score = 0
    personal_score = 0
    
    text_to_check = name + ' ' + content_lower
    
    for kw in WORK_KEYWORDS:
        if kw in text_to_check:
            work_score += 1
    
    for kw in PERSONAL_KEYWORDS:
        if kw in text_to_check:
            personal_score += 1
    
    # Content length check - very short content might be outdated/partial
    if content and len(content.strip()) < 50:
        return 'skip'
    
    if personal_score > work_score:
        return 'personal'
    elif work_score > 0:
        return 'work'
    else:
        # Default: check path
        if '/apple notes/' in path_str:
            return 'personal'
        return 'work'


def get_work_category(filepath, content):
    """Determine work subcategory."""
    name = filepath.name.lower()
    path_str = str(filepath).lower()
    content_lower = (content or '').lower()[:3000]
    
    # Path-based categorization
    if '/1 on 1/' in path_str or '/1on1/' in path_str:
        return 'people'
    if '/incidents/' in path_str:
        return 'incidents'
    if '/cross team/' in path_str:
        return 'cross-team'
    if '/manager training/' in path_str:
        return 'learning'
    if '/engineering guild/' in path_str:
        return 'cross-team'
    if '/platform em/' in path_str:
        return 'team'
    if '/ai observability/' in path_str:
        return 'projects'
    if '/cassandra/' in path_str or '/rate limiting/' in path_str:
        return 'projects'
    if '/polaris/' in path_str:
        return 'projects'
    if '/lakehouse/' in path_str:
        return 'projects'
    if '/bedrock/' in path_str:
        return 'projects'
    if '/performance review/' in path_str:
        return 'reviews'
    
    # Content-based
    if '1:1' in name or ' <> ' in name or ' / ' in name:
        return 'people'
    if 'incident' in name or 'outage' in name or 'rca' in content_lower:
        return 'incidents'
    if 'interview' in name or 'candidate' in name:
        return 'interviews'
    
    return 'reference'


def get_personal_category(filepath, content):
    """Determine personal subcategory."""
    name = filepath.name.lower()
    path_str = str(filepath).lower()
    
    if '/health/' in path_str or 'retinal' in name or 'medical' in name:
        return 'health'
    if '/canada/' in path_str or 'pr card' in name or 'immigration' in name:
        return 'immigration'
    if 'richie' in name or 'pet' in name or 'daycare' in name:
        return 'richie'
    if 'invest' in name or 'stock' in name or 'portfolio' in name:
        return 'finance'
    if 'book' in name or 'read' in name:
        return 'reading'
    if 'trip' in name or 'travel' in name or 'vacation' in name:
        return 'travel'
    
    return 'misc'


def extract_person_from_filename(filename):
    """Extract person name from 1:1 filename."""
    # Patterns: "Person <> Arnab", "Person / Arnab", etc.
    patterns = [
        r'^(.+?)\s*<>\s*Arnab',
        r'^(.+?)\s*/\s*Arnab',
        r'^Arnab\s*<>\s*(.+)',
        r'^Arnab\s*/\s*(.+)',
    ]
    
    name = filename.replace('.md', '')
    for pattern in patterns:
        match = re.match(pattern, name, re.IGNORECASE)
        if match:
            person = match.group(1).strip()
            # Remove date suffixes
            person = re.sub(r'\s*[-–]\s*\d+.*$', '', person)
            return person
    return None


def extract_date_from_filename(filename):
    """Try to extract date from filename."""
    # Try various date patterns
    patterns = [
        r'(\d{1,2})(?:st|nd|rd|th)?\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s*(\d{2,4})',
        r'(\d{4})-(\d{2})-(\d{2})',
        r'(\d{1,2})/(\d{1,2})/(\d{2,4})',
    ]
    
    months = {'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
              'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'}
    
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                if groups[1].lower()[:3] in months:
                    # Format: "1st May 25"
                    day = groups[0].zfill(2)
                    month = months[groups[1].lower()[:3]]
                    year = groups[2]
                    if len(year) == 2:
                        year = '20' + year
                    return f"{year}-{month}-{day}"
                else:
                    # Try YYYY-MM-DD or similar
                    try:
                        return f"{groups[0]}-{groups[1].zfill(2)}-{groups[2].zfill(2)}"
                    except:
                        pass
    
    return None


def add_frontmatter(content, metadata):
    """Add YAML frontmatter to content."""
    if content.startswith('---'):
        # Already has frontmatter, skip
        return content
    
    fm_lines = ['---']
    for key, value in metadata.items():
        if value:
            if isinstance(value, list):
                fm_lines.append(f'{key}: {value}')
            else:
                fm_lines.append(f'{key}: "{value}"')
    fm_lines.append('---\n')
    
    return '\n'.join(fm_lines) + content


def process_file(filepath):
    """Process a single file."""
    if should_skip(filepath):
        stats['skipped_pattern'] += 1
        return
    
    content = get_file_content(filepath)
    if content is None:
        stats['read_error'] += 1
        return
    
    classification = classify_content(filepath, content)
    
    if classification == 'skip':
        stats['skipped_content'] += 1
        skipped_files.append(str(filepath))
        return
    
    if classification == 'personal':
        category = get_personal_category(filepath, content)
        output_dir = PERSONAL_PATH / category
        output_name = slugify(filepath.stem) + '.md'
        
        metadata = {
            'title': filepath.stem,
            'category': category,
            'source': str(filepath.relative_to(VAULT_PATH)),
        }
        
    else:  # work
        category = get_work_category(filepath, content)
        
        if category == 'people':
            person = extract_person_from_filename(filepath.name)
            if person:
                person_slug = slugify(person)
                date = extract_date_from_filename(filepath.name) or 'undated'
                output_dir = ORGANIZED_PATH / 'people' / person_slug
                output_name = f"{date}-{slugify(filepath.stem)}.md"
            else:
                output_dir = ORGANIZED_PATH / 'people' / 'misc'
                output_name = slugify(filepath.stem) + '.md'
        elif category == 'projects':
            # Determine project
            name_lower = filepath.name.lower()
            path_lower = str(filepath).lower()
            if 'polaris' in name_lower or 'polaris' in path_lower:
                output_dir = ORGANIZED_PATH / 'projects' / 'polaris'
            elif 'lakehouse' in name_lower or 'lakehouse' in path_lower:
                output_dir = ORGANIZED_PATH / 'projects' / 'lakehouse'
            elif 'cassandra' in name_lower or 'cassandra' in path_lower:
                output_dir = ORGANIZED_PATH / 'projects' / 'cassandra'
            elif 'rate limit' in name_lower or 'rate limit' in path_lower:
                output_dir = ORGANIZED_PATH / 'projects' / 'rate-limiting'
            elif 'bedrock' in name_lower or 'bedrock' in path_lower:
                output_dir = ORGANIZED_PATH / 'projects' / 'bedrock'
            elif 'observability' in path_lower:
                output_dir = ORGANIZED_PATH / 'projects' / 'ai-observability'
            else:
                output_dir = ORGANIZED_PATH / 'projects' / 'other'
            output_name = slugify(filepath.stem) + '.md'
        elif category == 'reviews':
            output_dir = ORGANIZED_PATH / 'reviews'
            output_name = slugify(filepath.stem) + '.md'
        elif category == 'learning':
            output_dir = ORGANIZED_PATH / 'learning'
            output_name = slugify(filepath.stem) + '.md'
        else:
            output_dir = ORGANIZED_PATH / category
            output_name = slugify(filepath.stem) + '.md'
        
        metadata = {
            'title': filepath.stem,
            'category': category,
            'source': str(filepath.relative_to(VAULT_PATH)),
        }
        
        date = extract_date_from_filename(filepath.name)
        if date:
            metadata['date'] = date
    
    # Add frontmatter and write
    final_content = add_frontmatter(content, metadata)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_name
    
    # Handle duplicates
    counter = 1
    while output_path.exists():
        output_name = f"{slugify(filepath.stem)}-{counter}.md"
        output_path = output_dir / output_name
        counter += 1
    
    output_path.write_text(final_content, encoding='utf-8')
    
    stats[classification] += 1
    stats[f'{classification}_{category}'] += 1
    processed_files.append({
        'source': str(filepath),
        'dest': str(output_path),
        'classification': classification,
        'category': category,
    })


def process_directory(dirpath):
    """Process all markdown files in a directory."""
    for item in dirpath.iterdir():
        if item.is_dir():
            # Skip certain directories
            if item.name in ['Media', '.obsidian', '.trash']:
                continue
            process_directory(item)
        elif item.suffix == '.md':
            process_file(item)


def main():
    print("Processing remaining vault content...")
    print(f"Source: {VAULT_PATH}")
    print(f"Work output: {ORGANIZED_PATH}")
    print(f"Personal output: {PERSONAL_PATH}")
    print()
    
    # Directories to process (excluding date-based files we already processed)
    dirs_to_process = [
        'Atlan',
        'Apple Notes',
        'Lakehouse',
        'Metastore',
        'Performance Review - 2026',
        'Project Bedrock',
        'Team - 2026',
        'AI',
    ]
    
    for dirname in dirs_to_process:
        dirpath = VAULT_PATH / dirname
        if dirpath.exists():
            print(f"Processing {dirname}...")
            process_directory(dirpath)
    
    print()
    print("=== Results ===")
    print(f"Work files: {stats['work']}")
    print(f"Personal files: {stats['personal']}")
    print(f"Skipped (content): {stats['skipped_content']}")
    print(f"Skipped (pattern): {stats['skipped_pattern']}")
    print(f"Read errors: {stats['read_error']}")
    print()
    
    print("=== Work breakdown ===")
    for key, val in sorted(stats.items()):
        if key.startswith('work_'):
            print(f"  {key.replace('work_', '')}: {val}")
    
    print()
    print("=== Personal breakdown ===")
    for key, val in sorted(stats.items()):
        if key.startswith('personal_'):
            print(f"  {key.replace('personal_', '')}: {val}")
    
    # Save processing log
    log_path = Path("/home/Arnab/clawd/projects/career-agent/analysis/remaining_processing.log")
    with open(log_path, 'w') as f:
        f.write(f"Processed: {datetime.now().isoformat()}\n\n")
        f.write(f"Stats: {dict(stats)}\n\n")
        f.write("Skipped files:\n")
        for sf in skipped_files[:50]:
            f.write(f"  {sf}\n")
    
    print(f"\nLog saved to: {log_path}")


if __name__ == "__main__":
    main()
