# Doc Restructure Skill

Deterministic primitives for markdown document restructuring with 100% reliability and coverage verification.

## Why This Skill Exists

LLMs are great for creative writing, but unreliable for structural document edits. When you need to:

- **Extract sections exactly** (byte-for-byte identical to source)
- **Split one document into many** with guaranteed coverage
- **Audit links** between body text and sources section
- **Rename headings** across many files

...LLMs drift. They miss headings, skip content, or hallucinate structure.

This skill provides **deterministic primitives** that agents call directly. No LLM in the loop means:
- 100% coverage guarantee
- Bit-exact extraction
- Fast (no API calls)
- Repeatable results

## Overview

This skill provides LLM-free, bit-exact functions for extracting and restructuring markdown documents. Unlike LLM-based approaches, these functions guarantee deterministic results and provide mathematical coverage verification.

## Features

- **Heading Detection**: Find all headings outside fenced code blocks
- **Section Extraction**: Extract verbatim sections by heading title
- **Coverage Verification**: Verify all document headings are accounted for
- **Safe Filename Slugs**: Generate safe filenames from headings
- **H2 Range Extraction**: Get all H2 section ranges with line numbers
- **Link Auditing**: Extract and verify URLs between body and sources

## Installation

```bash
git clone https://github.com/arterm-sedov/doc-restructure-skill ~/.agents/skills/doc-restructure
```

Or for Claude Code/Cursor:
```bash
npx skills add arterm-sedov/doc-restructure
```

## Usage

```python
import sys
sys.path.insert(0, '~/.agents/skills/doc-restructure/scripts')

from doc_restructure import (
    iter_headings, 
    extract_section_by_heading, 
    coverage_check,
    make_safe_slug,
    extract_all_h2_section_ranges,
    body_urls,
    sources_urls,
    audit_links,
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

# Audit links in document with Sources section
if "## Sources" in document_md:
    body, sources = document_md.split("## Sources", 1)
    link_audit = audit_links(body, sources)
    print(f"Missing from sources: {link_audit['missing']}")
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
