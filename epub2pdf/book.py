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
    help="Target page count per signature; see `impose --help` for how balancing works.",
)
@click.option("--output-prefix", default="signature", show_default=True)
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
    output_prefix,
    keep_flat_pdf,
):
    """Convert EPUB_PATH straight to signature booklets in OUTPUT_DIR: runs
    the epub->pdf conversion (defaulting to A5 pages, since that's what
    tiles exactly 2-up onto A4), then imposes the result into signatures
    ready to print, fold, and bind.
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
    paths = impose_booklet(
        flat_pdf_path,
        output_dir,
        signature_size=signature_size,
        sheet_size=sheet_size,
        output_prefix=output_prefix,
    )
    for p in paths:
        click.echo(f"Wrote {p}")
    click.echo(f"See {output_dir}/PRINTING_INSTRUCTIONS.txt for folding/binding order.")

    if not keep_flat_pdf:
        os.remove(flat_pdf_path)


if __name__ == "__main__":
    main()
