from __future__ import annotations

import os

import click

from .cli import build_pdf_options, convert_epub_to_pdf, typography_options
from .imposition import SHEET_SIZES_MM, impose_booklet


@click.command(name="book")
@click.argument("epub_path", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_dir", type=click.Path(file_okay=False))
@typography_options(default_page_size="a5")
@click.option(
    "--sheet-size",
    type=click.Choice(sorted(SHEET_SIZES_MM)),
    default="a4",
    show_default=True,
    help="Physical sheet printed on (content pages are laid out 2-up per side).",
)
@click.option(
    "--signature-size",
    type=int,
    default=8,
    show_default=True,
    help="Target number of physical SHEETS of paper per signature (each sheet = "
    "4 content pages once folded, so the default is 32 content pages per "
    "signature); see `impose --help` for how balancing works.",
)
@click.option("--output-name", default="book_imposed.pdf", show_default=True, help="Filename for the imposed PDF.")
@click.option(
    "--sheet-order",
    type=click.Choice(["innermost-first", "outermost-first"]),
    default="innermost-first",
    show_default=True,
    help="Print order of sheets within a signature. 'innermost-first' means the "
    "sheets come off the printer already nested in fold order (correct for "
    "printers that stack each new sheet on top of the previous ones); use "
    "'outermost-first' if your printer/workflow stacks the other way.",
)
@click.option(
    "--keep-flat-pdf/--no-keep-flat-pdf",
    default=True,
    help="Also keep the pre-imposition, sequentially-paginated PDF in OUTPUT_DIR.",
)
def main(
    epub_path,
    output_dir,
    page_size,
    page_width,
    page_height,
    margin,
    margin_top,
    margin_right,
    margin_bottom,
    margin_left,
    mirror_margins,
    font_family,
    font_file,
    font_size,
    line_height,
    page_number_style,
    page_number_position,
    no_paragraph_indent,
    toc_title,
    toc_depth,
    title_page,
    sheet_size,
    signature_size,
    output_name,
    sheet_order,
    keep_flat_pdf,
):
    """Convert EPUB_PATH straight to a signature-imposed booklet PDF in
    OUTPUT_DIR: runs the epub->pdf conversion (defaulting to A5 pages, since
    that's what tiles exactly 2-up onto A4), then imposes the result into
    signatures ready to print, fold, and bind.
    """
    if signature_size < 1:
        raise click.BadParameter("--signature-size must be at least 1")

    os.makedirs(output_dir, exist_ok=True)

    opts = build_pdf_options(
        page_size,
        page_width,
        page_height,
        margin,
        margin_top,
        margin_right,
        margin_bottom,
        margin_left,
        mirror_margins,
        font_family,
        font_file,
        font_size,
        line_height,
        page_number_style,
        page_number_position,
        no_paragraph_indent,
    )

    flat_pdf_path = os.path.join(output_dir, "book_flat.pdf")
    convert_epub_to_pdf(
        epub_path,
        flat_pdf_path,
        opts,
        toc_title=toc_title,
        toc_depth=toc_depth,
        title_page=title_page,
        echo=click.echo,
    )

    click.echo("Imposing signatures ...")
    output_path = os.path.join(output_dir, output_name)
    impose_booklet(
        flat_pdf_path,
        output_path,
        sheets_per_signature=signature_size,
        sheet_size=sheet_size,
        print_innermost_first=(sheet_order == "innermost-first"),
    )
    instructions_path = os.path.splitext(output_path)[0] + "_INSTRUCTIONS.txt"
    click.echo(f"Wrote {output_path}")
    click.echo(f"See {instructions_path} for folding/binding order.")

    if not keep_flat_pdf:
        os.remove(flat_pdf_path)


if __name__ == "__main__":
    main()
