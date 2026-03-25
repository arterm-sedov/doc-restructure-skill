---
name: doc-restructure
description: Provides deterministic primitives for restructuring markdown documents with 100% reliability and coverage verification.
---

# Doc Restructure Skill

This skill provides deterministic, LLM-free primitives for extracting and restructuring markdown documents with guaranteed coverage. Unlike LLM-based approaches, these functions provide bit-exact extraction and verification capabilities.

## Core Primitives

The skill exposes core functions that agents can use directly:

### iter_headings(markdown, levels=(1,2,3,4,5,6))

Yield heading occurrences outside fenced code blocks.

**Parameters:**
- `markdown`: The markdown content as a string
- `levels`: Iterable of heading levels to consider (default: all levels 1-6)

**Returns:**
- Iterable of `HeadingOccurrence` objects with:
  - `level`: int (heading level)
  - `title`: str (normalized heading text)
  - `start_line`: int (0-based inclusive)
  - `end_line`: int (0-based exclusive)

### extract_section_by_heading(markdown, heading_title, heading_level=2)

Extract a verbatim section starting at the first matching heading.

**Parameters:**
- `markdown`: The markdown content as a string
- `heading_title`: The heading title to match (will be normalized)
- `heading_level`: The heading level to match (default: 2)

**Returns:**
- Tuple of `(section_text, start_line, end_line_exclusive)`

**Notes:**
- Extraction stops at fenced code blocks (does not include their content)
- Section includes the matched heading line and all lines until the next heading of the same level or a fenced block
- Returns exact verbatim content (no modification)

### coverage_check(markdown, mapped_headings)

Verify that all headings in the document are accounted for in a mapping.

**Parameters:**
- `markdown`: The markdown content as a string
- `mapped_headings`: Set of normalized heading titles that should be present

**Returns:**
- Dictionary with:
  - `"covered"`: List of headings found in both document and mapping
  - `"missing"`: List of headings in document but not in mapping
  - `"extra"`: List of headings in mapping but not in document

### make_safe_slug(heading_title, max_length=80)

Create a safe filename slug from a heading title.

**Parameters:**
- `heading_title`: The heading title to convert
- `max_length`: Maximum length of the slug (default 80)

**Returns:**
- A safe filename-compatible slug string

### extract_all_h2_section_ranges(markdown)

Extract all H2 section ranges from markdown.

**Parameters:**
- `markdown`: The markdown content

**Returns:**
- List of tuples `(title, start_line, end_line)` for each H2 section, sorted by position

## Usage Example

```python
import sys
sys.path.insert(0, 'skills/doc-restructure')

from doc_restructure.scripts import (
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

## Deterministic Guarantees

1. **Bit-exact extraction**: Returns content byte-for-byte identical to source
2. **Fenced code block awareness**: Never extracts content from within code fences
3. **Heading normalization**: Handles Unicode whitespace (NBSP) and repeated spaces consistently
4. **Coverage verification**: Provides mathematical guarantee that all content is accounted for

## Design Philosophy

This skill intentionally avoids:
- LLM dependencies (for determinism and speed)
- File I/O operations (agents handle their own persistence)
- Complex mapping parsers (agents provide their own mapping data)

Agents orchestrate the workflow using these primitives, maintaining full control over:
- What gets mapped where
- How extracted content is stored
- When/if to use LLMs for disambiguation
