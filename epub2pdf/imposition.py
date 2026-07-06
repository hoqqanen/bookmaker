"""Booklet imposition: takes a flat, sequentially-paginated PDF and lays it
out 2-up, front/back, as a set of saddle-stitched signatures meant to be
folded, nested, and then bound together (perfect-bound / Smyth-sewn style),
rather than one single giant saddle-stitch booklet.

Each signature must have a page count divisible by 4 (every physical sheet,
once folded, contributes 4 pages). Content is padded with blank pages at the
end of a signature when it doesn't divide evenly.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

from pypdf import PdfReader, PdfWriter, Transformation
from pypdf._page import PageObject

MM_TO_PT = 72 / 25.4

# (width_mm, height_mm) in portrait orientation
SHEET_SIZES_MM = {
    "a3": (297, 420),
    "a4": (210, 297),
    "a5": (148, 210),
    "letter": (215.9, 279.4),
    "legal": (215.9, 355.6),
}


def sheet_size_pt(name: str, landscape: bool = True) -> tuple[float, float]:
    try:
        w_mm, h_mm = SHEET_SIZES_MM[name]
    except KeyError:
        raise ValueError(f"Unknown sheet size {name!r}; choices: {sorted(SHEET_SIZES_MM)}") from None
    w, h = w_mm * MM_TO_PT, h_mm * MM_TO_PT
    return (h, w) if landscape else (w, h)


def balanced_signature_sizes(total_pages: int, target_size: int) -> list[int]:
    """Split total_pages into as-equal-as-possible groups near target_size.

    e.g. 22 pages at target 8 -> [8, 7, 7], not the lopsided [8, 8, 6] you'd
    get from greedily filling each signature to target_size.
    """
    if total_pages <= 0:
        return []
    num_signatures = max(1, math.ceil(total_pages / target_size))
    base, remainder = divmod(total_pages, num_signatures)
    return [base + 1] * remainder + [base] * (num_signatures - remainder)


def _pad_to_multiple(n: int, multiple: int = 4) -> int:
    return math.ceil(n / multiple) * multiple if n > 0 else 0


def saddle_stitch_layout(n: int) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """For n pages (must be a multiple of 4), return the print-order list of
    sheets: [((front_left, front_right), (back_left, back_right)), ...],
    using 0-indexed page positions. This is the standard imposition used for
    saddle-stitched booklets/signatures."""
    if n % 4 != 0:
        raise ValueError(f"signature page count must be a multiple of 4, got {n}")
    sheets = []
    for s in range(n // 4):
        front_left = n - 2 * s
        front_right = 1 + 2 * s
        back_left = 2 + 2 * s
        back_right = n - 1 - 2 * s
        sheets.append(((front_left - 1, front_right - 1), (back_left - 1, back_right - 1)))
    return sheets


@dataclass
class Signature:
    index: int
    start_page: int  # 0-indexed, inclusive, into the source document
    content_page_count: int
    padded_page_count: int


def plan_signatures(total_pages: int, target_size: int) -> list[Signature]:
    sizes = balanced_signature_sizes(total_pages, target_size)
    signatures = []
    cursor = 0
    for i, size in enumerate(sizes):
        signatures.append(
            Signature(
                index=i + 1,
                start_page=cursor,
                content_page_count=size,
                padded_page_count=_pad_to_multiple(size, 4),
            )
        )
        cursor += size
    return signatures


def _place(dest_page: PageObject, src_page: PageObject, cell_w: float, cell_h: float, slot: int) -> None:
    src_w = float(src_page.mediabox.width)
    src_h = float(src_page.mediabox.height)
    scale = min(cell_w / src_w, cell_h / src_h)
    draw_w, draw_h = src_w * scale, src_h * scale
    offset_x = slot * cell_w + (cell_w - draw_w) / 2
    offset_y = (cell_h - draw_h) / 2
    transform = Transformation().scale(scale, scale).translate(offset_x, offset_y)
    dest_page.merge_transformed_page(src_page, transform)


def compose_signature(
    reader: PdfReader,
    signature: Signature,
    sheet_w: float,
    sheet_h: float,
) -> PdfWriter:
    """Builds one signature's imposed PDF (all sheets, front then back, in
    print order) as a PdfWriter ready to be saved."""
    src_pages = reader.pages
    first_real = src_pages[signature.start_page]
    blank_w = float(first_real.mediabox.width)
    blank_h = float(first_real.mediabox.height)

    pages: list[PageObject] = []
    for i in range(signature.content_page_count):
        pages.append(src_pages[signature.start_page + i])
    for _ in range(signature.padded_page_count - signature.content_page_count):
        pages.append(PageObject.create_blank_page(width=blank_w, height=blank_h))

    layout = saddle_stitch_layout(signature.padded_page_count)
    cell_w, cell_h = sheet_w / 2, sheet_h

    writer = PdfWriter()
    for front_pair, back_pair in layout:
        for left_idx, right_idx in (front_pair, back_pair):
            dest = PageObject.create_blank_page(width=sheet_w, height=sheet_h)
            _place(dest, pages[left_idx], cell_w, cell_h, slot=0)
            _place(dest, pages[right_idx], cell_w, cell_h, slot=1)
            writer.add_page(dest)
    return writer


def impose_booklet(
    input_pdf: str,
    output_dir: str,
    signature_size: int = 8,
    sheet_size: str = "a4",
    output_prefix: str = "signature",
) -> list[str]:
    """Reads input_pdf and writes one imposed PDF per signature into
    output_dir, plus a PRINTING_INSTRUCTIONS.txt. Returns the list of
    signature PDF paths written, in binding order."""
    os.makedirs(output_dir, exist_ok=True)
    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)
    signatures = plan_signatures(total_pages, signature_size)
    sheet_w, sheet_h = sheet_size_pt(sheet_size, landscape=True)

    digits = max(2, len(str(len(signatures))))
    out_paths = []
    for sig in signatures:
        writer = compose_signature(reader, sig, sheet_w, sheet_h)
        out_path = os.path.join(output_dir, f"{output_prefix}_{sig.index:0{digits}d}.pdf")
        with open(out_path, "wb") as f:
            writer.write(f)
        out_paths.append(out_path)

    _write_instructions(output_dir, signatures, sheet_size)
    return out_paths


def _write_instructions(output_dir: str, signatures: list[Signature], sheet_size: str) -> None:
    lines = [
        f"{len(signatures)} signature(s) from this book, for {sheet_size.upper()} sheets, "
        "2-up, double-sided.",
        "",
        "Printing:",
        f"  - Print each signature_*.pdf double-sided, flipping on the SHORT edge",
        "    (sometimes called 'tumble' duplex) -- the sheets are landscape, and",
        "    short-edge flip is what keeps front/back aligned once folded.",
        "  - Print signatures in order (signature_01, signature_02, ...).",
        "",
        "Folding & binding:",
        "  - Fold each signature's printed sheets in half together (nested, like",
        "    a saddle-stitched booklet) to form one signature block.",
        "  - Stack the folded signatures in order and bind (glue/sew) along the",
        "    folded edge.",
        "",
        "Signature detail:",
    ]
    for sig in signatures:
        pad = sig.padded_page_count - sig.content_page_count
        pad_note = f" (+{pad} blank page{'s' if pad != 1 else ''} at the end)" if pad else ""
        lines.append(
            f"  - signature_{sig.index:02d}: {sig.content_page_count} content pages"
            f"{pad_note}, {sig.padded_page_count // 4} sheet(s)"
        )
    with open(os.path.join(output_dir, "PRINTING_INSTRUCTIONS.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
