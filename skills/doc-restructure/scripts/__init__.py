"""Doc Restructure Skill - Deterministic primitives for markdown document restructuring."""

from .markdown_sections import (
    normalize_heading,
    HeadingOccurrence,
    iter_headings,
    extract_section_by_heading,
    coverage_check,
    make_safe_slug,
    extract_all_h2_section_ranges,
)

__all__ = [
    "normalize_heading",
    "HeadingOccurrence",
    "iter_headings",
    "extract_section_by_heading",
    "coverage_check",
    "make_safe_slug",
    "extract_all_h2_section_ranges",
]
