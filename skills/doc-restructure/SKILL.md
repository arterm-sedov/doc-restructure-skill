---
name: doc-restructure
description: Provides deterministic primitives for restructuring markdown documents with 100% reliability and coverage verification.
---

# Doc Restructure Skill

This skill provides deterministic, LLM-free primitives for extracting and restructuring markdown documents with guaranteed coverage. Unlike LLM-based approaches, these functions provide bit-exact extraction and verification capabilities.

## Build Ad-Hoc Harnesses for Complex Jobs

**For complex transformations, don't do interactive work—build a harness.**

An **agent harness** is a small, purpose-built system that wraps your work with:
- Structure (configuration, not hardcoding)
- Idempotency (safe to re-run)
- Clear artifacts (markers for next session)
- Verification (coverage checks)

Instead of doing 50 interactive edits, build a harness that:
1. Loads configuration (files, transforms, expected outputs)
2. Applies deterministic transforms using this skill's primitives
3. Verifies coverage/results
4. Logs progress

Example pattern:
```python
# harness.py - one-off script for this job
from pathlib import Path
from doc_restructure import iter_headings, coverage_check

CONFIG = [
    {"file": "doc1.md", "expected_sections": ["Intro", "Method", "Results"]},
    {"file": "doc2.md", "expected_sections": ["Overview", "Details"]},
]

def transform_one(path, expected):
    content = path.read_text()
    # Use skill primitives here
    headings = {h.title for h in iter_headings(content, levels=(2,))}
    # Verify
    missing = coverage_check(content, set(expected))["missing"]
    if missing:
        raise ValueError(f"Missing sections: {missing}")
    # Transform...

for cfg in CONFIG:
    transform_one(Path(cfg["file"]), cfg["expected_sections"])
```

**Why this beats pure interactive work:**
- Saves context length (one script vs 50 back-and-forth turns)
- Deterministic—same input = same output
- Idempotent—re-run to pick up where you left off
- Verifiable—coverage checks catch drift

## Use Code for Complex Tasks

**Don't overengineer, but don't shy away from code either.**

For complex bulk operations, use the right tool:
- **Python**: Complex text parsing, multi-file processing, link auditing
- **grep/sed**: Quick find-and-replace across many files
- **bash/PowerShell**: Batch renaming, file organization

Example - bulk fix broken links:
```bash
# Find all markdown files with broken reference
grep -r "old-section-name" --include="*.md" -l
```

Example - extract all URLs from multiple files:
```python
from pathlib import Path
from doc_restructure import body_urls

for md in Path("docs").glob("**/*.md"):
    urls = body_urls(md.read_text())
    print(f"{md}: {len(urls)} URLs")
```

## Core Primitives

### iter_headings(markdown, levels=(1,2,3,4,5,6))

Yield heading occurrences outside fenced code blocks.

**Returns:** Iterable of `HeadingOccurrence` objects with:
- `level`: int
- `title`: str (normalized)
- `start_line`: int (0-based inclusive)
- `end_line`: int (0-based exclusive)

### extract_section_by_heading(markdown, heading_title, heading_level=2)

Extract a verbatim section starting at the first matching heading.

**Returns:** Tuple of `(section_text, start_line, end_line_exclusive)`

### coverage_check(markdown, mapped_headings)

Verify that all headings in the document are accounted for.

**Returns:** Dict with `"covered"`, `"missing"`, `"extra"` lists

### make_safe_slug(heading_title, max_length=80)

Create a safe filename slug from a heading title.

### extract_all_h2_section_ranges(markdown)

Extract all H2 section ranges.

**Returns:** List of `(title, start_line, end_line)` tuples

### normalize_url(url)

Strip trailing punctuation from URLs.

### body_urls(text)

Extract all URLs from markdown (markdown links + bare URLs).

**Returns:** Dict mapping URL -> preferred label

### sources_urls(sources_block)

Extract URLs from Sources section (`- [label](url)` format).

**Returns:** Set of URLs

### suggest_url_category(url)

Suggest category heading based on URL domain.

### audit_links(body, sources_block)

Audit links between body and sources.

**Returns:** Dict with `"covered"`, `"missing"`, `"extra"` URL lists

### add_heading_anchors(text, prefix="")

Add markdown anchor links to all headings.

**Example:** `## My Section` → `## My Section {: #my-section }`

### strip_front_matter(text)

Strip YAML front matter from markdown.

**Returns:** Tuple of `(front_matter, body)`

### add_front_matter(body, title, date="", status="", tags=None)

Add YAML front matter to markdown body.

### extract_ial_headings(markdown)

Extract headings with IAL (Kramdown) syntax: `## Title {: #anchor-id }`

**Returns:** List of dicts with `level`, `title`, `anchor_id`, `line_number`

### apply_anchor_map(markdown, old_to_new)

Apply anchor ID remapping to markdown.

**Example:** `{: #old_id }` → `{: #new_id }`

### find_orphaned_refs(markdown, defined_anchors)

Find broken cross-references (links to non-existent anchors).

**Returns:** List of dicts with `fragment`, `line_number`, `context`

### make_slug(title, max_length=48)

Create URL-safe slug from heading title (ASCII-only).

### demote_headings(markdown, levels=1)

Demote headings by one level outside fenced code blocks.

**Example:** `## H2` → `### H3`

### promote_headings(markdown, levels=1)

Promote headings by one level outside fenced code blocks.

**Example:** `### H3` → `## H2`

### extract_first_h1(markdown)

Extract the first H1 heading from markdown.

**Returns:** H1 title without # prefix, or None

### slugify_anchor(text)

Create anchor-friendly slug (keeps Cyrillic).

### build_combined_document(file_paths, title, add_toc=False)

Combine multiple markdown files into one document.

Each file becomes an H2 section, headings inside are demoted by one level.

### extract_http_urls(text)

Extract all HTTP/HTTPS URLs from text.

**Returns:** Set of normalized URLs

### parse_section_buckets(markdown, heading_level=2)

Parse sections at given level into ordered buckets with URLs.

**Returns:** Dict: section_title -> {anchor, urls: {url: info}}

### deduplicate_urls_across_sections(buckets, section_order=None)

Deduplicate URLs - each URL appears in exactly one section.

Useful for merging source lists.

### find_duplicate_urls_in_section(markdown, section_start)

Find URLs appearing more than once in a section.

**Returns:** List of duplicate URLs

## Usage Example

```python
import sys
sys.path.insert(0, 'skills/doc-restructure')

from doc_restructure.scripts import (
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

## Deterministic Guarantees

1. **Bit-exact extraction**: Returns content byte-for-byte identical to source
2. **Fenced code block awareness**: Never extracts content from within code fences
3. **Heading normalization**: Handles Unicode whitespace (NBSP) consistently
4. **Coverage verification**: Mathematical guarantee that all content is accounted for

## Design Philosophy

This skill intentionally avoids:
- LLM dependencies (for determinism and speed)
- File I/O operations (agents handle their own persistence)
- Complex mapping parsers (agents provide their own mapping data)

Agents orchestrate the workflow using these primitives + ad-hoc harnesses, maintaining full control over:
- What gets mapped where
- How extracted content is stored
- When/if to use LLMs for disambiguation
