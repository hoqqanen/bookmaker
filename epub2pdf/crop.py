"""Crop a PDF's margins by shrinking each page's visible box (MediaBox and
CropBox) inward by fixed amounts on each side. Non-destructive: the content
stream is untouched, so a strip that goes slightly wrong can be redone by
adjusting the margins and re-running, without any quality loss.
"""

from __future__ import annotations

from pypdf import PdfWriter
from pypdf.generic import RectangleObject

POINTS_PER_INCH = 72.0


def crop_pdf(
    input_pdf: str,
    output_pdf: str,
    left: float,
    right: float,
    top: float,
    bottom: float,
    echo=lambda msg: None,
) -> None:
    """Insets every page of `input_pdf` by `left`/`right`/`top`/`bottom`
    inches and writes the result to `output_pdf`."""
    left_pt = left * POINTS_PER_INCH
    right_pt = right * POINTS_PER_INCH
    top_pt = top * POINTS_PER_INCH
    bottom_pt = bottom * POINTS_PER_INCH

    writer = PdfWriter(clone_from=input_pdf)

    for page_num, page in enumerate(writer.pages, start=1):
        box = page.mediabox
        new_box = RectangleObject(
            (
                float(box.left) + left_pt,
                float(box.bottom) + bottom_pt,
                float(box.right) - right_pt,
                float(box.top) - top_pt,
            )
        )
        if new_box.width <= 0 or new_box.height <= 0:
            raise ValueError(
                f"page {page_num}: margins ({left}in + {right}in horizontal, "
                f"{top}in + {bottom}in vertical) exceed the page size "
                f"({float(box.width) / POINTS_PER_INCH:.2f}in x "
                f"{float(box.height) / POINTS_PER_INCH:.2f}in)"
            )
        page.mediabox = new_box
        page.cropbox = new_box

    writer.write(output_pdf)
    echo(f"Cropped {len(writer.pages)} page(s)")
