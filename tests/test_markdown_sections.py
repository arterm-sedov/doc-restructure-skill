"""Tests for markdown_sections module - TDD approach."""

import pytest

# Import the module we're testing
from doc_restructure.markdown_sections import normalize_heading, iter_headings


class TestNormalizeHeading:
    """Tests for normalize_heading function."""

    def test_strips_whitespace(self):
        """Normalize heading should strip leading/trailing whitespace."""
        result = normalize_heading("  Hello World  ")
        assert result == "Hello World"

    def test_replaces_multiple_spaces_with_single(self):
        """Normalize heading should replace multiple spaces with single space."""
        result = normalize_heading("Hello    World")
        assert result == "Hello World"

    def test_replaces_nbsp_with_space(self):
        """Normalize heading should replace non-breaking space with regular space."""
        result = normalize_heading("Hello\u00A0World")
        assert result == "Hello World"

    def test_preserves_middle_spaces(self):
        """Normalize heading should preserve single middle spaces."""
        result = normalize_heading("Hello World")
        assert result == "Hello World"

    def test_empty_string_returns_empty(self):
        """Normalize heading should handle empty string."""
        result = normalize_heading("")
        assert result == ""

    def test_multiple_nbsp_replaced(self):
        """Multiple NBSP characters should all be replaced."""
        result = normalize_heading("Test\u00A0\u00A0Value")
        assert result == "Test Value"


class TestIterHeadings:
    """Tests for iter_headings function."""

    def test_finds_all_h2_headings(self):
        """iter_headings should find all H2 headings in markdown."""
        md = """# Title

## Heading 1

Some content

## Heading 2

More content
"""
        headings = list(iter_headings(md, levels=(2,)))
        assert len(headings) == 2
        assert headings[0].title == "Heading 1"
        assert headings[1].title == "Heading 2"

    def test_skips_headings_in_fenced_blocks(self):
        """iter_headings should not find headings inside fenced code blocks."""
        md = """## Visible Heading

```
## Hidden Heading
```

## Another Visible
"""
        headings = list(iter_headings(md, levels=(2,)))
        assert len(headings) == 2
        titles = [h.title for h in headings]
        assert "Visible Heading" in titles
        assert "Hidden Heading" not in titles
        assert "Another Visible" in titles

    def test_respects_level_filter(self):
        """iter_headings should only return headings of specified levels."""
        md = """# H1
## H2
### H3
"""
        h1_only = list(iter_headings(md, levels=(1,)))
        h2_only = list(iter_headings(md, levels=(2,)))
        h1_h2 = list(iter_headings(md, levels=(1, 2)))

        assert len(h1_only) == 1
        assert h1_only[0].title == "H1"

        assert len(h2_only) == 1
        assert h2_only[0].title == "H2"

        assert len(h1_h2) == 2

    def test_returns_line_numbers(self):
        """iter_headings should return correct line numbers."""
        md = """## First
content
## Second
"""
        headings = list(iter_headings(md, levels=(2,)))
        assert headings[0].start_line == 0
        assert headings[0].end_line == 1
        assert headings[1].start_line == 2
        assert headings[1].end_line == 3

    def test_handles_tilde_fenced_blocks(self):
        """iter_headings should handle ~~~ fenced blocks correctly."""
        md = """## Visible

~~~markdown
## Hidden in tilde fence
~~~

## After
"""
        headings = list(iter_headings(md, levels=(2,)))
        titles = [h.title for h in headings]
        assert "Visible" in titles
        assert "Hidden in tilde fence" not in titles
        assert "After" in titles


class TestExtractSectionByHeading:
    """Tests for extract_section_by_heading function."""

    def test_extracts_section_by_title(self):
        """extract_section_by_heading should extract section content."""
        from doc_restructure.markdown_sections import extract_section_by_heading
        md = """## First Section

Content of first

## Second Section

Content of second
"""
        section, start, end = extract_section_by_heading(md, heading_title="Second Section", heading_level=2)
        assert "## Second Section" in section
        assert "Content of second" in section
        assert "First Section" not in section

    def test_raises_error_for_missing_heading(self):
        """extract_section_by_heading should raise error for missing heading."""
        from doc_restructure.markdown_sections import extract_section_by_heading
        md = """## Existing

Content
"""
        with pytest.raises(ValueError, match="Heading not found"):
            extract_section_by_heading(md, heading_title="Non-existent", heading_level=2)

    def test_respects_fenced_code_blocks(self):
        """extract_section_by_heading should not cross into fenced code blocks."""
        from doc_restructure.markdown_sections import extract_section_by_heading
        md = """## Section One

Some content

```python
## Should not be included
```

## Section Two
"""
        section, _, _ = extract_section_by_heading(md, heading_title="Section One", heading_level=2)
        assert "## Section One" in section
        assert "Some content" in section
        assert "## Should not be included" not in section
        assert "## Section Two" not in section

    def test_returns_line_numbers(self):
        """extract_section_by_heading should return correct line numbers."""
        from doc_restructure.markdown_sections import extract_section_by_heading
        md = """## First
content
## Second
more content
## Third
"""
        section, start, end = extract_section_by_heading(md, "Second", heading_level=2)
        assert start == 2
        assert end == 4

    def test_handles_normalized_heading_matching(self):
        """extract_section_by_heading should handle heading normalization."""
        from doc_restructure.markdown_sections import extract_section_by_heading
        md = """## Heading  With  Spaces

Content here
"""
        section, _, _ = extract_section_by_heading(md, "Heading With Spaces", heading_level=2)
        assert "## Heading  With  Spaces" in section


class TestCoverageCheck:
    """Tests for coverage_check function."""

    def test_identifies_covered_headings(self):
        """coverage_check should identify covered headings."""
        from doc_restructure.markdown_sections import coverage_check
        md = """## A
## B
## C
"""
        result = coverage_check(md, {"A", "B", "C"})
        assert result["covered"] == ["A", "B", "C"]
        assert result["missing"] == []
        assert result["extra"] == []

    def test_identifies_missing_headings(self):
        """coverage_check should identify missing headings."""
        from doc_restructure.markdown_sections import coverage_check
        md = """## A
## B
"""
        result = coverage_check(md, {"A"})  # Only mapping A, not B
        assert result["covered"] == ["A"]
        assert result["missing"] == ["B"]

    def test_identifies_extra_mappings(self):
        """coverage_check should identify extra mappings."""
        from doc_restructure.markdown_sections import coverage_check
        md = """## A
"""
        result = coverage_check(md, {"A", "B"})  # Mapping includes B but B not in doc
        assert result["covered"] == ["A"]
        assert result["missing"] == []
        assert result["extra"] == ["B"]