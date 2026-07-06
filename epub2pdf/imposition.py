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


def plan_signatures(total_pages: int, target_sheets_per_signature: int) -> list[Signature]:
    """Plans signatures in terms of physical SHEETS of paper (each sheet =
    4 content pages once folded), not content pages directly. e.g. with the
    default of 8 sheets per signature, each signature is 32 content pages.

    Sheets are balanced across signatures the same way pages are balanced
    within a sheet count (e.g. 44 sheets at target 8 -> 8/8/7/7/7/7, not a
    lopsided last signature). Any shortfall (total_pages not a multiple of 4)
    is padded with blank pages at the very end, i.e. only the last signature
    is ever padded.
    """
    if total_pages <= 0:
        return []
    total_sheets = math.ceil(total_pages / 4)
    sheet_counts = balanced_signature_sizes(total_sheets, target_sheets_per_signature)

    signatures = []
    cursor = 0
    for i, sheets in enumerate(sheet_counts):
        padded = sheets * 4
        content = min(padded, total_pages - cursor)
        signatures.append(
            Signature(
                index=i + 1,
                start_page=cursor,
                content_page_count=content,
                padded_page_count=padded,
            )
        )
        cursor += content
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
    print_innermost_first: bool = True,
) -> PdfWriter:
    """Builds one signature's imposed PDF (all sheets, front then back, in
    print order) as a PdfWriter ready to be saved.

    print_innermost_first controls the order sheets are emitted in. Most
    printers deposit each newly-printed sheet on top of the previous ones,
    so printing the innermost sheet first and the outermost sheet last means
    the finished stack comes off the printer already correctly nested for
    folding -- no manual reshuffling needed. Set to False if your printer/
    workflow stacks the other way and you'd rather have the outermost sheet
    (the one with the signature's first and last pages) print first.
    """
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
    if print_innermost_first:
        layout = list(reversed(layout))
    cell_w, cell_h = sheet_w / 2, sheet_h

    writer = PdfWriter()
    for front_pair, back_pair in layout:
        # Back emitted before front within each sheet, matching the duplex
        # side order that keeps a short-edge-flip print physically correct.
        for left_idx, right_idx in (back_pair, front_pair):
            dest = PageObject.create_blank_page(width=sheet_w, height=sheet_h)
            _place(dest, pages[left_idx], cell_w, cell_h, slot=0)
            _place(dest, pages[right_idx], cell_w, cell_h, slot=1)
            writer.add_page(dest)
    return writer


def impose_booklet(
    input_pdf: str,
    output_path: str,
    sheets_per_signature: int = 8,
    sheet_size: str = "a4",
    print_innermost_first: bool = True,
) -> str:
    """Reads input_pdf and writes a single imposed PDF to output_path,
    containing every signature's sheets concatenated in binding order (all
    of signature 1's sheets, then all of signature 2's, ...), plus a
    PRINTING_INSTRUCTIONS.txt next to it. Returns output_path.

    sheets_per_signature is a target physical-sheet count (each sheet = 4
    content pages once folded), not a content-page count -- the default of
    8 means each signature is 8 sheets, i.e. 32 content pages."""
    output_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(output_dir, exist_ok=True)
    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)
    signatures = plan_signatures(total_pages, sheets_per_signature)
    sheet_w, sheet_h = sheet_size_pt(sheet_size, landscape=True)

    combined = PdfWriter()
    sheet_ranges = []  # (signature, first_sheet_side_number, last_sheet_side_number), 1-indexed
    for sig in signatures:
        writer = compose_signature(reader, sig, sheet_w, sheet_h, print_innermost_first=print_innermost_first)
        first_side = len(combined.pages) + 1
        for page in writer.pages:
            combined.add_page(page)
        sheet_ranges.append((sig, first_side, len(combined.pages)))

    with open(output_path, "wb") as f:
        combined.write(f)

    instructions_path = os.path.splitext(output_path)[0] + "_INSTRUCTIONS.txt"
    _write_instructions(instructions_path, output_path, sheet_ranges, sheet_size, print_innermost_first)
    return output_path


def _write_instructions(
    instructions_path: str,
    output_path: str,
    sheet_ranges: list[tuple[Signature, int, int]],
    sheet_size: str,
    print_innermost_first: bool,
) -> None:
    order_note = (
        "innermost sheet first, outermost sheet last -- sheets come off the "
        "printer pre-nested for folding, no reshuffling needed (assuming your "
        "printer stacks each new sheet on top of the last)"
        if print_innermost_first
        else "outermost sheet first, innermost sheet last"
    )
    lines = [
        f"{len(sheet_ranges)} signature(s) from this book, imposed into "
        f"{os.path.basename(output_path)}, for {sheet_size.upper()} sheets, 2-up, double-sided.",
        "",
        "Printing:",
        f"  - Print {os.path.basename(output_path)} double-sided, flipping on the SHORT edge",
        "    (sometimes called 'tumble' duplex) -- the sheets are landscape, and",
        "    short-edge flip is what keeps front/back aligned once folded.",
        f"  - Sheet order within each signature is {order_note}.",
        "  - Signatures are concatenated in order; print the whole file as one job,",
        "    then split the output stack into the sheet-count groups listed below",
        "    (in order) before folding.",
        "",
        "Folding & binding:",
        "  - Fold each signature's printed sheets in half together (nested, like",
        "    a saddle-stitched booklet) to form one signature block.",
        "  - Stack the folded signatures in order and bind (glue/sew) along the",
        "    folded edge.",
        "",
        "Signature detail (page numbers below refer to sides within the imposed PDF):",
    ]
    for sig, first_side, last_side in sheet_ranges:
        pad = sig.padded_page_count - sig.content_page_count
        pad_note = f" (+{pad} blank page{'s' if pad != 1 else ''} at the end)" if pad else ""
        lines.append(
            f"  - signature_{sig.index:02d}: PDF sides {first_side}-{last_side}"
            f" ({sig.padded_page_count // 4} sheets), {sig.content_page_count} content pages{pad_note}"
        )
    with open(instructions_path, "w") as f:
        f.write("\n".join(lines) + "\n")
