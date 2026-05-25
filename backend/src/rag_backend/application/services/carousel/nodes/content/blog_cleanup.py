"""Blog markdown cleanup pipeline for LLM-generated content.

Strips leading H1, removes backtick-wrapped duplicates, HTML fragment
artifacts, indented duplicates, emoji-only indented lines, indented
paragraph lookalikes, duplicate paragraphs, and collapses excessive
whitespace.
"""

from __future__ import annotations

import re

BACKTICK_PAIR_COUNT = 2


def _strip_leading_h1(markdown: str) -> str:
    lines = markdown.split("\n")
    if not lines:
        return markdown
    first = lines[0].strip()
    if first.startswith("# "):
        idx = 1
        while idx < len(lines) and lines[idx].strip() == "":
            idx += 1
        return "\n".join(lines[idx:])
    return markdown


def _remove_backtick_duplicates(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if (
            stripped.startswith("`")
            and stripped.endswith("`")
            and stripped.count("`") == BACKTICK_PAIR_COUNT
            and i + 1 < len(lines)
        ):
            inner = stripped[1:-1].strip()
            next_line = lines[i + 1].strip()
            if inner == next_line:
                i += 1
                continue
        result.append(line)
        i += 1
    return "\n".join(result)


def _strip_html_fragments(text: str) -> str:
    text = re.sub(r'"\s*/?>\s*$', "", text, flags=re.MULTILINE)
    text = re.sub(r"<img\s+[^>]*?/>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<\w+[^>]*?>", "", text)
    return re.sub(r"</\w+>", "", text)


def _collapse_whitespace(text: str) -> str:
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()


def _remove_indented_duplicates(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    recent_headings: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            recent_headings.add(stripped[3:].strip().lower())
        elif stripped.startswith("# "):
            recent_headings.add(stripped[2:].strip().lower())
        if line.startswith("    ") and stripped:
            lowered = stripped.lower()
            if any(lowered in h or h in lowered for h in recent_headings):
                continue
        result.append(line)
    return "\n".join(result)


def _remove_duplicate_paragraphs(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        result.append(line)
        if line.strip():
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].strip() == line.strip():
                i = j + 1
                continue
        i += 1
    return "\n".join(result)


def _remove_indented_emoji_lines(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    for line in lines:
        if line.startswith("    "):
            stripped = line.strip()
            if stripped and not any(c.isalnum() for c in stripped):
                continue
        result.append(line)
    return "\n".join(result)


def _remove_indented_paragraph_duplicates(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("    ") and i + 1 < len(lines):
            stripped = line.strip()
            next_line = lines[i + 1].strip()
            if (
                stripped
                and next_line
                and (stripped in next_line or next_line in stripped)
            ):
                i += 1
                continue
        result.append(line)
        i += 1
    return "\n".join(result)


def cleanup_blog_markdown(raw: str) -> str:
    text = raw
    text = _strip_leading_h1(text)
    text = _remove_backtick_duplicates(text)
    text = _remove_indented_duplicates(text)
    text = _remove_indented_emoji_lines(text)
    text = _remove_indented_paragraph_duplicates(text)
    text = _remove_duplicate_paragraphs(text)
    text = _strip_html_fragments(text)
    return _collapse_whitespace(text)
