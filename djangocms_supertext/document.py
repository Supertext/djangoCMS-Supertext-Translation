"""
Packs texts into one HTML document and splits the translated document apart.

Every text travels as ``<div data-st-id="N">…</div>``. Supertext translates each such
element as a unit and keeps markup and attributes, so a whole rich-text body (its
paragraphs, bold words and links) is translated in context. Plain texts are escaped and
their line breaks sent as ``<br>``.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, NavigableString, Tag


@dataclass
class Segment:
    text: str
    html: bool = False


def build(segments: list[Segment]) -> str:
    body = ""
    for index, segment in enumerate(segments):
        if segment.html:
            content = segment.text
        else:
            content = html.escape(segment.text.replace("\r\n", "\n").replace("\r", "\n"), quote=True).replace("\n", "<br>")
        body += f'<div data-st-id="{index}">{content}</div>\n'
    return f'<!DOCTYPE html>\n<html><head><meta charset="utf-8"></head><body>\n{body}</body></html>'


def parse(document: str, segments: list[Segment]) -> dict[int, str]:
    """Segment index -> translation (inner HTML for HTML segments, text for plain ones)."""
    soup = BeautifulSoup(document, "html.parser")
    out: dict[int, str] = {}
    for element in soup.find_all(attrs={"data-st-id": True}):
        try:
            index = int(element["data-st-id"])
        except (TypeError, ValueError):
            continue
        if index < 0 or index >= len(segments):
            continue
        out[index] = element.decode_contents().strip() if segments[index].html else _plain_text(element)
    return out


def _plain_text(element: Tag) -> str:
    parts: list[str] = []
    for node in element.descendants:
        if isinstance(node, NavigableString):
            parts.append(str(node))
        elif isinstance(node, Tag) and node.name == "br":
            parts.append("\ue000")
    text = re.sub(r"\s+", " ", "".join(parts))
    return re.sub(" ?\ue000 ?", "\n", text).strip(" ")


def chunks(segments: list[Segment], limit: int) -> list[list[int]]:
    """Indexes of ``segments`` grouped so each group's text stays below ``limit`` characters."""
    groups: list[list[int]] = [[]]
    size = 0
    for index, segment in enumerate(segments):
        if groups[-1] and size + len(segment.text) > limit:
            groups.append([])
            size = 0
        groups[-1].append(index)
        size += len(segment.text)
    return groups
