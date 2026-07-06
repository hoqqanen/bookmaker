"""Merges an EPUB's spine documents into a single HTML file suitable for
paginated printing, with a generated table of contents whose page numbers
are resolved for real at render time via CSS target-counter()."""

from __future__ import annotations

import html
import os
import posixpath
from urllib.parse import unquote

from bs4 import BeautifulSoup
from ebooklib.epub import Link, Section

from .epub_parser import ParsedEpub

_EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "data:", "#", "javascript:")


def _norm(path_part: str) -> str:
    return posixpath.normpath(unquote(path_part))


def _split_href(href: str):
    if "#" in href:
        file_part, frag = href.split("#", 1)
    else:
        file_part, frag = href, ""
    return _norm(file_part), frag


def build_chapter_index(chapters) -> dict:
    """Map each spine document's manifest-relative filename to its position."""
    return {_norm(item.get_name()): idx for idx, item in enumerate(chapters)}


def resolve_href(href: str, file_to_idx: dict):
    """Turn an epub-internal href into the anchor id used in the merged document,
    or None if it points outside what we merged in (external link, missing doc, etc)."""
    if not href or href.startswith(_EXTERNAL_PREFIXES):
        return None
    file_part, frag = _split_href(href)
    idx = file_to_idx.get(file_part)
    if idx is None:
        return None
    return f"c{idx}_{frag}" if frag else f"c{idx}"


def write_resources(book, workdir: str) -> None:
    """Write every non-chapter manifest item (images, fonts, stray css, etc.)
    to workdir at its original manifest-relative path, so relative references
    from chapter markup keep resolving correctly."""
    import ebooklib

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            continue
        name = item.get_name()
        if not name:
            continue
        dest = os.path.join(workdir, name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(item.get_content())


def _resolve_resource_src(chapter_name: str, src: str) -> str:
    if not src or src.startswith(_EXTERNAL_PREFIXES):
        return src
    base_dir = posixpath.dirname(chapter_name)
    return posixpath.normpath(posixpath.join(base_dir, unquote(src)))


def _process_chapter(item, idx: int, file_to_idx: dict) -> str:
    raw = item.get_content()
    soup = BeautifulSoup(raw, "lxml")
    body = soup.body or soup

    for tag in body.find_all(id=True):
        tag["id"] = f"c{idx}_{tag['id']}"

    for a in body.find_all("a", href=True):
        new_id = resolve_href(a["href"], file_to_idx)
        if new_id:
            a["href"] = f"#{new_id}"

    for img in body.find_all("img", src=True):
        img["src"] = _resolve_resource_src(item.get_name(), img["src"])

    for tag in body.find_all("script"):
        tag.decompose()

    inner = body.decode_contents()
    return f'<section class="epub-chapter" id="c{idx}">{inner}</section>'


def _render_toc_nodes(nodes, file_to_idx: dict, depth: int, max_depth) -> str:
    if max_depth is not None and depth >= max_depth:
        return ""
    items = []
    for node in nodes:
        children = None
        if isinstance(node, tuple):
            head, children = node
        else:
            head = node
        title = html.escape(head.title or "")
        href = getattr(head, "href", "") or ""
        anchor_id = resolve_href(href, file_to_idx)
        if anchor_id:
            label = f'<a href="#{anchor_id}"><span class="toc-title">{title}</span></a>'
        else:
            label = f'<span class="toc-title toc-unlinked">{title}</span>'
        sub = _render_toc_nodes(children, file_to_idx, depth + 1, max_depth) if children else ""
        items.append(f"<li>{label}{sub}</li>")
    return "<ol>" + "".join(items) + "</ol>" if items else ""


def build_toc_html(toc, file_to_idx: dict, toc_title: str, max_depth=None) -> str:
    body = _render_toc_nodes(toc, file_to_idx, 0, max_depth)
    return f'<nav class="toc-page"><h1 class="toc-heading">{html.escape(toc_title)}</h1>{body}</nav>'


def build_title_page_html(title: str, author: str) -> str:
    author_html = f'<p class="title-author">{html.escape(author)}</p>' if author else ""
    return (
        '<section class="title-page">'
        f'<h1 class="title-main">{html.escape(title)}</h1>'
        f"{author_html}"
        "</section>"
    )


def build_merged_html(
    parsed: ParsedEpub,
    workdir: str,
    css_text: str,
    toc_title: str = "Contents",
    toc_depth=None,
    include_title_page: bool = True,
) -> str:
    """Writes merged.html (and all supporting resources) into workdir, returns its path."""
    write_resources(parsed.book, workdir)

    file_to_idx = build_chapter_index(parsed.chapters)

    chapter_html = "\n".join(
        _process_chapter(item, idx, file_to_idx) for idx, item in enumerate(parsed.chapters)
    )

    title_page_html = build_title_page_html(parsed.title, parsed.author) if include_title_page else ""
    toc_html = build_toc_html(parsed.toc, file_to_idx, toc_title, toc_depth)

    doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{html.escape(parsed.title)}</title>
<style>
{css_text}
</style>
</head>
<body>
{title_page_html}
{toc_html}
<div class="chapters">
{chapter_html}
</div>
</body>
</html>
"""
    out_path = os.path.join(workdir, "merged.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return out_path
