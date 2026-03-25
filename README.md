# Doc Restructure Skill

Deterministic primitives for markdown document restructuring with 100% reliability and coverage verification.

## Overview

This skill provides LLM-free, bit-exact functions for extracting and restructuring markdown documents. Unlike LLM-based approaches, these functions guarantee deterministic results and provide mathematical coverage verification.

## Features

- **Heading Detection**: Find all headings outside fenced code blocks
- **Section Extraction**: Extract verbatim sections by heading title
- **Coverage Verification**: Verify all document headings are accounted for
- **Safe Filename Slugs**: Generate safe filenames from headings
- **H2 Range Extraction**: Get all H2 section ranges with line numbers

## Installation

```bash
pip install -e skills/doc-restructure
```

## Usage

```python
from doc_restructure import (
    iter_headings, 
    extract_section_by_heading, 
    coverage_check,
    make_safe_slug,
    extract_all_h2_section_ranges
)

# Extract all H2 headings from a document
headings = list(iter_headings(document_md, levels=(2,)))

# Extract a specific section
section_content, start, end = extract_section_by_heading(
    document_md, 
    heading_title="Methodology Overview", 
    heading_level=2
)

# Verify coverage
mapped_titles = {"Methodology Overview", "Implementation Details", "Results"}
coverage = coverage_check(document_md, mapped_titles)
if coverage["missing"]:
    print(f"Unmapped headings: {coverage['missing']}")

# Get all H2 section ranges
ranges = extract_all_h2_section_ranges(document_md)
for title, start, end in ranges:
    print(f"{title}: lines {start}-{end}")

# Create safe filename slug
slug = make_safe_slug("My Section Title")
```

## Project Structure

```
doc-restructure-skill/
├── LICENSE
├── README.md
└── skills/
    └── doc-restructure/
        ├── SKILL.md
        ├── scripts/
        │   ├── __init__.py
        │   └── markdown_sections.py
        └── tests/
            └── test_markdown_sections.py
```

## Testing

```bash
cd skills/doc-restructure
pytest tests/
```

## License

Apache License 2.0 - see LICENSE file
