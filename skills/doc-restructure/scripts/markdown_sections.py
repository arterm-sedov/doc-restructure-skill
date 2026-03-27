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
    title: str
    start_line: int
    end_line: int


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
    """Extract a verbatim section starting at the first matching heading."""
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
    """Verify that all headings in the document are accounted for."""
    document_headings = {h.title for h in iter_headings(markdown, levels=(1, 2, 3, 4, 5, 6))}

    return {
        "covered": sorted(document_headings & mapped_headings),
        "missing": sorted(document_headings - mapped_headings),
        "extra": sorted(mapped_headings - document_headings),
    }


def make_safe_slug(heading_title: str, max_length: int = 80) -> str:
    """Create a safe filename slug from a heading title."""
    slug = normalize_heading(heading_title)
    slug = "".join(ch if ch.isalnum() else "_" for ch in slug)[:max_length].strip("_")
    return slug


def extract_all_h2_section_ranges(markdown: str) -> list[tuple[str, int, int]]:
    """Extract all H2 section ranges from markdown."""
    lines = markdown.splitlines(keepends=True)
    occurrences = list(iter_headings(markdown, levels=(2,)))
    occurrences_sorted = sorted(occurrences, key=lambda x: x.start_line)
    
    ranges: list[tuple[str, int, int]] = []
    for idx, occ in enumerate(occurrences_sorted):
        start = occ.start_line
        end = occurrences_sorted[idx + 1].start_line if idx + 1 < len(occurrences_sorted) else len(lines)
        ranges.append((occ.title, start, end))
    return ranges


def normalize_url(url: str) -> str:
    """Normalize URL by stripping trailing punctuation."""
    return url.rstrip(").,;\"'")


def body_urls(text: str) -> dict[str, str]:
    """Extract all URLs from markdown body text."""
    out: dict[str, str] = {}
    for m in re.finditer(r"\[([^\]]*)\]\((https?://[^)\s]+)\)", text):
        u = normalize_url(m.group(2))
        label = m.group(1).strip().replace("\n", " ")
        if u not in out and label:
            out[u] = label
        elif u not in out:
            out[u] = u
    for m in re.finditer(r"(?<![(\[])(https?://[^\s\)\]>'\"]+)", text):
        u = normalize_url(m.group(1))
        if u not in out:
            out[u] = u
    return out


def sources_urls(sources_block: str) -> set[str]:
    """Extract all URLs from a Sources section."""
    found: set[str] = set()
    for m in re.finditer(r"- \[([^\]]*)\]\((https?://[^)\s]+)\)", sources_block):
        found.add(normalize_url(m.group(2)))
    for m in re.finditer(r"(?<![(\[])(https?://[^\s\)\]>'\"]+)", sources_block):
        found.add(normalize_url(m.group(1)))
    return found


def suggest_url_category(url: str) -> str:
    """Suggest category heading based on URL domain patterns."""
    u = url.lower()
    if "genai.owasp.org" in u or "owasp.org" in u or "github.com/owasp" in u:
        return "OWASP / security standards"
    if "kaspersky.com" in u or "securelist.com" in u:
        return "Threats / Kaspersky"
    if "huggingface.co" in u:
        return "Hugging Face"
    if "arxiv.org" in u or "research.nvidia.com" in u or "research.yandex.com" in u:
        return "Research / preprints"
    if "t.me/" in u:
        return "Telegram"
    if "github.com" in u:
        return "GitHub / open projects"
    if "habr.com" in u:
        return "Habr"
    if "cloud.ru" in u or "aistudio.yandex.ru" in u or "developers.sber.ru" in u:
        return "Cloud RU / tariffs"
    return "Review manually"


def audit_links(body: str, sources_block: str) -> dict[str, list[str]]:
    """Audit links between body and sources sections."""
    bu = body_urls(body)
    su = sources_urls(sources_block)
    
    return {
        "covered": sorted(set(bu) - (set(bu) - su)),
        "missing": sorted(set(bu) - su),
        "extra": sorted(su - set(bu)),
    }


def add_heading_anchors(text: str, prefix: str = "") -> str:
    """Add markdown anchor links to all headings.
    
    Args:
        text: The markdown text
        prefix: Optional prefix for anchor IDs (e.g., "ch1" -> "ch1_intro")
    
    Returns:
        Text with anchors added to headings
    
    Example:
        ## My Section -> ## My Section {: #my-section }
    """
    used: set[str] = set()
    out: list[str] = []
    for line in text.split("\n"):
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if not m or "{: #" in line:
            out.append(line)
            continue
        level, raw = m.group(1), m.group(2)
        base = re.sub(r"[^a-zA-Z0-9]+", "-", raw.lower()).strip("-")
        if not base:
            base = "section"
        if prefix and level == "#":
            hid = prefix
        elif prefix:
            hid = f"{prefix}_{base}"
        else:
            hid = base
        n = 2
        while hid in used:
            if prefix:
                hid = f"{prefix}_{base}_{n}"
            else:
                hid = f"{base}_{n}"
            n += 1
        used.add(hid)
        out.append(f"{level} {raw} {{: #{hid} }}")
    return "\n".join(out)


def strip_front_matter(text: str) -> tuple[str, str]:
    """Strip YAML front matter from markdown.
    
    Returns:
        Tuple of (front_matter, body)
    """
    if text.startswith("---\n"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[1], parts[2].lstrip("\n")
    return "", text


def add_front_matter(body: str, title: str, date: str = "", status: str = "", tags: list[str] = None) -> str:
    """Add YAML front matter to markdown body."""
    lines = ["---", f"title: '{title}'"]
    if date:
        lines.append(f"date: {date}")
    if status:
        lines.append(f"status: '{status}'")
    if tags:
        lines.append("tags:")
        for tag in sorted(tags):
            lines.append(f"  - {tag}")
    lines.append("---", "")
    return "\n".join(lines) + body
