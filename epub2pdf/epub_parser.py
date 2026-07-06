"""Reads an EPUB file into the pieces we need: ordered chapter documents,
the nested table-of-contents tree, and top-level metadata."""

from __future__ import annotations

from dataclasses import dataclass, field

import ebooklib
from ebooklib import epub


@dataclass
class ParsedEpub:
    book: epub.EpubBook
    chapters: list  # ordered list of epub.EpubHtml (spine documents)
    toc: list  # nested list of epub.Link / (epub.Section, children) as produced by ebooklib
    title: str
    author: str


def _get_meta(book: epub.EpubBook, field_name: str) -> str:
    values = book.get_metadata("DC", field_name)
    if not values:
        return ""
    # ebooklib returns list of (value, attributes) tuples
    return values[0][0] or ""


def parse_epub(path: str) -> ParsedEpub:
    book = epub.read_epub(path, options={"ignore_ncx": False})

    id_to_item = {item.get_id(): item for item in book.get_items()}
    chapters = []
    for idref, linear in book.spine:
        item = id_to_item.get(idref)
        if item is None:
            continue
        if item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        chapters.append(item)

    toc = book.toc or []

    # Fall back to a flat TOC built from the spine if the epub has none at all.
    if not toc:
        toc = [epub.Link(item.get_name(), item.title or item.get_name()) for item in chapters]

    return ParsedEpub(
        book=book,
        chapters=chapters,
        toc=toc,
        title=_get_meta(book, "title") or "Untitled",
        author=_get_meta(book, "creator") or "",
    )
