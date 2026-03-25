"""Markdown sections module for document restructuring."""

import re
from collections.abc import Iterable
from dataclasses import dataclass


def normalize_heading(text: str) -> str:
    """Normalize a markdown heading title for stable comparisons."""
    text = text.replace("\u00A0", " ")
    text = re.sub(r"\s+", " ", text.strip())
    return text


def _fence_kind(line: str) -> str | None:
    """Return fence kind ('```' or '~~~') if the line starts a fenced code block."""
    stripped = line.lstrip()
    if stripped.startswith("```"):
        return "```"
    if stripped.startswith("~~~"):
        return "~~~"
    return None


def _heading_re(level: int) -> re.Pattern[str]:
    """Return compiled regex for heading at given level."""
    return re.compile(rf"^{'#' * level}\s+(.+?)\s*$")


@dataclass(frozen=True)
class HeadingOccurrence:
    """Represents a heading occurrence in markdown."""
    level: int
    title: str  # normalized
    start_line: int  # 0-based inclusive
    end_line: int  # 0-based exclusive


def iter_headings(markdown: str, *, levels: Iterable[int] = (1, 2, 3, 4, 5, 6)) -> Iterable[HeadingOccurrence]:
    """Yield heading occurrences outside fenced code blocks."""
    lines = markdown.splitlines(keepends=True)
    fenced = False
    fence_marker: str | None = None

    level_set = set(levels)
    heading_levels_sorted = sorted(level_set)

    for i, line in enumerate(lines):
        kind = _fence_kind(line)
        if kind is not None:
            if not fenced:
                fenced = True
                fence_marker = kind
            else:
                if fence_marker == kind:
                    fenced = False
                    fence_marker = None
            continue

        if fenced:
            continue

        for level in heading_levels_sorted:
            m = _heading_re(level).match(line)
            if not m:
                continue
            title_raw = m.group(1)
            title = normalize_heading(title_raw)
            yield HeadingOccurrence(level=level, title=title, start_line=i, end_line=i + 1)
            break


def extract_section_by_heading(
    markdown: str,
    heading_title: str,
    heading_level: int = 2,
) -> tuple[str, int, int]:
    """Extract a verbatim section starting at the first matching heading.

    The extracted range includes the matched heading line and all lines until (but not including)
    the next heading of the same `heading_level`, outside fenced code blocks.

    Returns:
        (section_text, start_line, end_line_exclusive)
    """
    wanted = normalize_heading(heading_title)
    lines = markdown.splitlines(keepends=True)
    fenced = False
    fence_marker: str | None = None

    start_idx: int | None = None
    end_idx: int | None = None

    for i, line in enumerate(lines):
        kind = _fence_kind(line)
        if kind is not None:
            if not fenced:
                # Entering fenced block - stop extraction here
                fenced = True
                fence_marker = kind
                if start_idx is not None:
                    end_idx = i
                    break
            else:
                if fence_marker == kind:
                    fenced = False
                    fence_marker = None
            continue

        if fenced:
            continue

        if start_idx is None:
            m = _heading_re(heading_level).match(line)
            if not m:
                continue
            title = normalize_heading(m.group(1))
            if title == wanted:
                start_idx = i
                continue

        if start_idx is not None:
            m = _heading_re(heading_level).match(line)
            if m:
                end_idx = i
                break

    if start_idx is None:
        raise ValueError(f"Heading not found (level={heading_level}): {heading_title!r}")

    if end_idx is None:
        end_idx = len(lines)

    section_text = "".join(lines[start_idx:end_idx]).strip("\n")
    return section_text, start_idx, end_idx


def coverage_check(markdown: str, mapped_headings: set[str]) -> dict[str, list[str]]:
    """Verify that all headings in the document are accounted for in a mapping.

    Returns:
        Dictionary with:
        - "covered": List of headings found in both document and mapping
        - "missing": List of headings in document but not in mapping
        - "extra": List of headings in mapping but not in document
    """
    document_headings = {h.title for h in iter_headings(markdown, levels=(1, 2, 3, 4, 5, 6))}

    covered = sorted(document_headings & mapped_headings)
    missing = sorted(document_headings - mapped_headings)
    extra = sorted(mapped_headings - document_headings)

    return {
        "covered": covered,
        "missing": missing,
        "extra": extra,
    }

def make_safe_slug(heading_title: str, max_length: int = 80) -> str:
    """Create a safe filename slug from a heading title.
    
    Args:
        heading_title: The heading title to convert
        max_length: Maximum length of the slug (default 80)
    
    Returns:
        A safe filename-compatible slug
    """
    slug = normalize_heading(heading_title)
    slug = "".join(ch if ch.isalnum() else "_" for ch in slug)[:max_length].strip("_")
    return slug


def extract_all_h2_section_ranges(markdown: str) -> list[tuple[str, int, int]]:
    """Extract all H2 section ranges from markdown.
    
    Returns list of (heading_title_normalized, start_line_idx, end_line_exclusive)
    sorted by start position.
    
    Args:
        markdown: The markdown content
    
    Returns:
        List of tuples (title, start_line, end_line) for each H2 section
    """
    lines = markdown.splitlines(keepends=True)
    occurrences = list(iter_headings(markdown, levels=(2,)))
    occurrences_sorted = sorted(occurrences, key=lambda x: x.start_line)
    
    ranges: list[tuple[str, int, int]] = []
    for idx, occ in enumerate(occurrences_sorted):
        start = occ.start_line
        end = occurrences_sorted[idx + 1].start_line if idx + 1 < len(occurrences_sorted) else len(lines)
        ranges.append((occ.title, start, end))
    return ranges
