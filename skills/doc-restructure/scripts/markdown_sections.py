"""Markdown sections module for document restructuring."""

import re
import os
from collections.abc import Iterable
from pathlib import Path
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


# IAL/Kramdown heading anchor patterns (from remap_20260325_anchors.py)
HEADING_IAL_RE = re.compile(
    r"^(#{1,6})\s+(.+?)\s+\{:\s*#([a-z0-9_]+)(?:\s+[^}]*)?\}\s*$"
)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def extract_ial_headings(markdown: str) -> list[dict]:
    """Extract headings with IAL (implicit anchor link) syntax.
    
    Finds headings like: ## Title {: #anchor-id }
    
    Args:
        markdown: The markdown text
    
    Returns:
        List of dicts with: level, title, anchor_id, line_number
    """
    results = []
    lines = markdown.splitlines()
    in_fence = False
    
    for i, line in enumerate(lines, start=1):
        if line.strip().startswith("```") or line.strip().startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
            
        m = HEADING_IAL_RE.match(line.rstrip())
        if m:
            results.append({
                "level": len(m.group(1)),
                "title": m.group(2).strip(),
                "anchor_id": m.group(3),
                "line_number": i,
            })
    return results


def apply_anchor_map(markdown: str, old_to_new: dict[str, str]) -> str:
    """Apply anchor ID remapping to markdown.
    
    Args:
        markdown: The markdown text
        old_to_new: Dict mapping old anchor IDs to new ones
    
    Returns:
        Text with anchor IDs remapped
    """
    # Sort by length descending to avoid partial replacements
    keys_desc = sorted(old_to_new.items(), key=lambda kv: len(kv[0]), reverse=True)
    
    for old_id, new_id in keys_desc:
        # Handle different IAL syntax variations
        patterns = [
            f"{{: #{old_id} }}",
            f"{{: #{old_id}}}",
            f"(#{old_id})",
            f"(#{old_id} ",
            f"#{old_id})",
            f"#{old_id}]",
        ]
        for p in patterns:
            markdown = markdown.replace(p, p.replace(old_id, new_id))
    
    return markdown


def find_orphaned_refs(markdown: str, defined_anchors: set[str]) -> list[dict]:
    """Find broken cross-references (anchors that don't exist).
    
    Args:
        markdown: The markdown text
        defined_anchors: Set of valid anchor IDs defined in the document
    
    Returns:
        List of dicts with: fragment, line_number, context
    """
    orphans = []
    lines = markdown.splitlines()
    
    # Match links like [text](#anchor-id) or just (#anchor-id)
    frag_ref = re.compile(r"\]\(([^)#]+)#([a-z0-9_]+)\)")
    self_ref = re.compile(r"\]\(#([a-z0-9_]+)\)")
    
    for i, line in enumerate(lines, start=1):
        # Cross-file references: [text](file.md#anchor)
        for m in frag_ref.finditer(line):
            frag = m.group(1).split("/")[-1]  # get filename
            anchor = m.group(2)
            if frag.endswith(".md") and anchor not in defined_anchors:
                orphans.append({
                    "fragment": f"{frag}#{anchor}",
                    "line_number": i,
                    "context": line.strip()[:80],
                })
        
        # Self-references: [text](#anchor) within same file
        for m in self_ref.finditer(line):
            anchor = m.group(1)
            if anchor not in defined_anchors:
                orphans.append({
                    "fragment": f"#{anchor}",
                    "line_number": i,
                    "context": line.strip()[:80],
                })
    
    return orphans


def make_slug(title: str, max_length: int = 48) -> str:
    """Create URL-safe slug from heading title.
    
    Args:
        title: The heading title
        max_length: Maximum slug length
    
    Returns:
        Slug string (lowercase, hyphens)
    """
    # Remove existing IAL if present
    text = re.sub(r"\{:[^}]+\}", "", title)
    # Convert to ASCII-friendly (strips Cyrillic)
    text = re.sub(r"[^a-zA-Z0-9\s]+", "", text)
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower())
    text = text.strip("-")
    text = re.sub(r"-+", "-", text)
    return text[:max_length].rstrip("-") or "section"


def demote_headings(markdown: str, levels: int = 1) -> str:
    """Demote headings by one (or more) level outside fenced code blocks.
    
    Args:
        markdown: The markdown text
        levels: How many levels to demote (default: 1)
    
    Returns:
        Text with headings demoted
    
    Example:
        ## H2 becomes ### H3 with levels=1
    """
    lines = markdown.splitlines()
    in_fence = False
    fence_pattern = re.compile(r"^\s*(```|~~~)")
    out = []
    
    for line in lines:
        if fence_pattern.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        
        # Demote heading
        if line.startswith("#"):
            m = re.match(r"^(#+)(\s*)(.*)$", line)
            if m:
                hashes, space, rest = m.groups()
                new_hashes = hashes + ("#" * levels)
                out.append(new_hashes + space + rest)
            else:
                out.append(line)
        else:
            out.append(line)
    
    return "\n".join(out)


def promote_headings(markdown: str, levels: int = 1) -> str:
    """Promote headings by one (or more) level outside fenced code blocks.
    
    Args:
        markdown: The markdown text
        levels: How many levels to promote (default: 1)
    
    Returns:
        Text with headings promoted
    """
    lines = markdown.splitlines()
    in_fence = False
    fence_pattern = re.compile(r"^\s*(```|~~~)")
    out = []
    
    for line in lines:
        if fence_pattern.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        
        # Promote heading
        if line.startswith("#"):
            m = re.match(r"^(#+)(\s*)(.*)$", line)
            if m:
                hashes, space, rest = m.groups()
                new_len = max(1, len(hashes) - levels)
                new_hashes = "#" * new_len
                out.append(new_hashes + space + rest)
            else:
                out.append(line)
        else:
            out.append(line)
    
    return "\n".join(out)


def extract_first_h1(markdown: str) -> str | None:
    """Extract the first H1 heading from markdown.
    
    Args:
        markdown: The markdown text
    
    Returns:
        The H1 title without the # prefix, or None if no H1 found
    """
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def slugify_anchor(text: str) -> str:
    """Create anchor-friendly slug (keeps Cyrillic).
    
    Args:
        text: The heading text
    
    Returns:
        Slug string for anchors
    """
    text = text.strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^\w\-]", "", text)
    return text


def build_combined_document(
    file_paths: list[str],
    title: str,
    add_toc: bool = False,
) -> str:
    """Combine multiple markdown files into one document.
    
    Each file becomes a section (H2). Headings inside are demoted by one level.
    
    Args:
        file_paths: List of markdown file paths to combine
        title: The document title (H1)
        add_toc: Whether to add a table of contents
    
    Returns:
        Combined markdown document
    """
    parts = [f"# {title}\n"]
    
    anchors_seen = {}
    toc_entries = []
    sections = []
    
    for path in file_paths:
        if not os.path.exists(path):
            continue
        try:
            content = open(path, encoding='utf-8').read()
        except:
            continue
        
        # Extract H1 from file or use filename
        h1 = extract_first_h1(content)
        if h1:
            section_title = h1
            # Remove H1 from body
            content = re.sub(r"^# .+\n", "", content, count=1, flags=re.MULTILINE)
        else:
            section_title = Path(path).stem
        
        # Demote headings in this file
        body = demote_headings(content)
        
        # Generate anchor
        anchor = slugify_anchor(section_title)
        if anchor in anchors_seen:
            anchors_seen[anchor] += 1
            anchor = f"{anchor}_{anchors_seen[anchor]}"
        else:
            anchors_seen[anchor] = 1
        
        toc_entries.append((section_title, anchor))
        sections.append((section_title, body))
    
    # Build TOC
    if add_toc and toc_entries:
        parts.append("\n## Оглавление\n")
        for title, anchor in toc_entries:
            parts.append(f"- [{title}](#{anchor})")
    
    # Build sections
    for section_title, body in sections:
        anchor = slugify_anchor(section_title)
        parts.append(f"\n## {section_title}\n")
        parts.append(body)
    
    return "\n".join(parts)


def extract_http_urls(text: str) -> set[str]:
    """Extract all HTTP/HTTPS URLs from text.
    
    Args:
        text: The text to extract URLs from
    
    Returns:
        Set of normalized URLs
    """
    return {normalize_url(m) for m in re.findall(r"https?://[^\s)>\]]+", text)}


def parse_section_buckets(markdown: str, heading_level: int = 2) -> dict:
    """Parse sections at given level into ordered buckets.
    
    Args:
        markdown: The markdown text
        heading_level: The heading level to parse (default: 4 for H4)
    
    Returns:
        Ordered dict: section_title -> {anchor, urls: {url: line}}
    """
    level_char = "#" * heading_level
    heading_re = re.compile(rf"^{level_char} (.+?) \{{: #([^}}]+) }}\s*$")
    link_re = re.compile(r"^- \[([^\]]*)\]\((https?://[^)]+)\)\s*(.*)$")
    # Reset on headings LOWER than target level (e.g., H1-H3 resets when parsing H4)
    lower_levels = "".join("#" for _ in range(1, heading_level))
    heading_reset = re.compile(rf"^[{lower_levels}][^{level_char}]")
    
    lines = markdown.splitlines()
    buckets = {}
    order = []
    current = None
    
    for line in lines:
        if heading_reset.match(line):
            current = None
            continue
        
        m = heading_re.match(line)
        if m:
            title = m.group(1).strip()
            anchor = m.group(2).strip()
            if title not in buckets:
                buckets[title] = {"anchor": anchor, "urls": {}}
                order.append(title)
            current = title
            continue
        
        if current is None:
            continue
        
        lm = link_re.match(line)
        if lm:
            label, url = lm.group(1), lm.group(2)
            nu = normalize_url(url)
            full_line = line.rstrip()
            existing = buckets[current]["urls"].get(nu)
            if existing is None or len(label) > len(existing.get("label", "")):
                buckets[current]["urls"][nu] = {"label": label, "line": full_line}
    
    # Return in order
    return {k: buckets[k] for k in order if k in buckets}


def deduplicate_urls_across_sections(
    buckets: dict,
    section_order: list[str] = None,
) -> dict:
    """Deduplicate URLs - each URL appears in exactly one section.
    
    Args:
        buckets: Dict from parse_section_buckets()
        section_order: Preferred order (earlier = higher priority)
    
    Returns:
        Cleaned buckets with deduplicated URLs
    """
    if section_order is None:
        section_order = list(buckets.keys())
    
    unknown = [t for t in buckets if t not in section_order]
    
    def priority(title: str) -> tuple[int, int]:
        if title in section_order:
            return (0, section_order.index(title))
        return (1, unknown.index(title))
    
    assignment = {}
    for title, data in buckets.items():
        for url, info in data["urls"].items():
            pri = priority(title)
            cur = assignment.get(url)
            if cur is None or pri < cur[0]:
                assignment[url] = (pri, title, info["line"])
            elif pri == cur[0] and len(info["label"]) > len(cur[2].get("label", "")):
                assignment[url] = (pri, title, info["line"])
    
    fresh = {}
    for t in buckets:
        fresh[t] = {"anchor": buckets[t]["anchor"], "urls": {}}
    
    for url, (_pri, title, line) in assignment.items():
        fresh[title]["urls"][url] = {"label": "", "line": line}
    
    return {t: d for t, d in fresh.items() if d["urls"]}


def find_duplicate_urls_in_section(markdown: str, section_start: str) -> list[str]:
    """Find URLs that appear more than once in a section.
    
    Args:
        markdown: The markdown text
        section_start: Heading that marks start of section to check
    
    Returns:
        List of duplicate URLs (sorted)
    """
    if section_start in markdown:
        section = markdown.split(section_start, 1)[1]
    else:
        section = markdown
    
    urls = extract_http_urls(section)
    counts = {}
    for u in urls:
        counts[u] = counts.get(u, 0) + 1
    
    return sorted(u for u, c in counts.items() if c > 1)
