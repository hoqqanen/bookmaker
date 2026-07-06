from __future__ import annotations

import shutil
import tempfile

import click

from .css_builder import VALID_NUMBER_STYLES, VALID_POSITIONS, PdfOptions, build_css
from .epub_parser import parse_epub
from .html_builder import build_merged_html

PAGE_SIZE_PRESETS = {
    "6x9": ("6in", "9in"),
    "5x8": ("5in", "8in"),
    "5.5x8.5": ("5.5in", "8.5in"),
    "a4": ("210mm", "297mm"),
    "a5": ("148mm", "210mm"),
    "letter": ("8.5in", "11in"),
}


def convert_epub_to_pdf(
    epub_path: str,
    output_path: str,
    opts: PdfOptions,
    toc_title: str = "Contents",
    toc_depth=None,
    title_page: bool = True,
    keep_workdir: bool = False,
    echo=lambda msg: None,
) -> None:
    """Runs the full epub -> pdf pipeline. Shared by the `convert` command
    and the combined `book` command."""
    echo(f"Parsing {epub_path} ...")
    parsed = parse_epub(epub_path)
    echo(f"  title: {parsed.title!r}, {len(parsed.chapters)} chapters")

    workdir = tempfile.mkdtemp(prefix="epub2pdf_")
    try:
        css_text = build_css(opts)
        html_path = build_merged_html(
            parsed,
            workdir,
            css_text,
            toc_title=toc_title,
            toc_depth=toc_depth,
            include_title_page=title_page,
        )

        # Imported lazily so --help doesn't pay the WeasyPrint/Pango import cost.
        from .render import render_pdf

        echo("Rendering PDF ...")
        render_pdf(html_path, output_path)
        echo(f"Wrote {output_path}")
    finally:
        if keep_workdir:
            echo(f"Intermediate files kept at {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)


def typography_options(default_page_size="6x9"):
    """Shared CLI options for the `convert` and `book` commands."""

    def decorator(f):
        options = [
            click.option(
                "--page-size",
                type=click.Choice(sorted(PAGE_SIZE_PRESETS)),
                default=default_page_size,
                show_default=True,
                help="Named trim size preset (overridden by --page-width/--page-height).",
            ),
            click.option("--page-width", default=None, help="e.g. '6in' or '148mm'. Overrides --page-size."),
            click.option("--page-height", default=None, help="e.g. '9in' or '210mm'. Overrides --page-size."),
            click.option("--margin", default=None, help="Shorthand that sets all four margins at once."),
            click.option("--margin-top", default=None),
            click.option("--margin-right", default=None),
            click.option("--margin-bottom", default=None),
            click.option("--margin-left", default=None),
            click.option(
                "--mirror-margins/--no-mirror-margins",
                default=False,
                help="Swap left/right margins on even pages, for a book-style inside/outside gutter.",
            ),
            click.option("--font-family", default="Georgia, 'Times New Roman', serif", show_default=True),
            click.option(
                "--font-file",
                type=click.Path(exists=True, dir_okay=False),
                default=None,
                help="Path to a .ttf/.otf/.woff file to embed and use instead of --font-family.",
            ),
            click.option("--font-size", default="11pt", show_default=True),
            click.option("--line-height", default="1.4", show_default=True),
            click.option(
                "--page-number-style",
                type=click.Choice(VALID_NUMBER_STYLES),
                default="decimal",
                show_default=True,
            ),
            click.option(
                "--page-number-position",
                type=click.Choice(VALID_POSITIONS),
                default="bottom-center",
                show_default=True,
            ),
            click.option(
                "--no-paragraph-indent", is_flag=True, default=False, help="Disable first-line paragraph indent."
            ),
            click.option("--toc-title", default="Contents", show_default=True),
            click.option("--toc-depth", type=int, default=None, help="Max TOC nesting depth (default: unlimited)."),
            click.option("--title-page/--no-title-page", default=True, help="Include a generated title page."),
        ]
        for option in reversed(options):
            f = option(f)
        return f

    return decorator


def build_pdf_options(
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
) -> PdfOptions:
    preset_w, preset_h = PAGE_SIZE_PRESETS[page_size]
    base_margin = margin or "0.75in"
    return PdfOptions(
        page_width=page_width or preset_w,
        page_height=page_height or preset_h,
        margin_top=margin_top or base_margin,
        margin_right=margin_right or base_margin,
        margin_bottom=margin_bottom or base_margin,
        margin_left=margin_left or base_margin,
        mirror_margins=mirror_margins,
        font_family=font_family,
        font_file=font_file,
        font_size=font_size,
        line_height=line_height,
        page_number_style=page_number_style,
        page_number_position=page_number_position,
        paragraph_indent=not no_paragraph_indent,
    )


@click.command(name="convert")
@click.argument("epub_path", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_path", type=click.Path(dir_okay=False))
@typography_options()
@click.option(
    "--keep-workdir",
    is_flag=True,
    default=False,
    help="Don't delete the intermediate HTML/resources directory; path is printed for debugging.",
)
def main(
    epub_path,
    output_path,
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
    keep_workdir,
):
    """Convert EPUB_PATH to a paginated PDF at OUTPUT_PATH, with a real,
    page-accurate table of contents."""
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

    convert_epub_to_pdf(
        epub_path,
        output_path,
        opts,
        toc_title=toc_title,
        toc_depth=toc_depth,
        title_page=title_page,
        keep_workdir=keep_workdir,
        echo=click.echo,
    )


if __name__ == "__main__":
    main()
