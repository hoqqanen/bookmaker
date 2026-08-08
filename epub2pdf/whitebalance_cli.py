from __future__ import annotations

import click

from .whitebalance import METHODS, WhiteBalanceOptions, adjust_pdf_white_balance


@click.command(name="whitebalance")
@click.argument("input_pdf", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_pdf", type=click.Path(dir_okay=False))
@click.option(
    "--method",
    type=click.Choice(METHODS),
    default="gray-world",
    show_default=True,
    help="'gray-world' scales each color channel so the page's average color is "
    "neutral gray (gentle, general-purpose). 'white-patch' scales channels so "
    "the brightest pixels (e.g. paper background) become pure white (stronger, "
    "best for visibly tinted/sepia scans).",
)
@click.option(
    "--percentile",
    type=float,
    default=99.5,
    show_default=True,
    help="Brightness percentile treated as the white point. Only used by --method white-patch.",
)
@click.option(
    "--strength",
    type=float,
    default=1.0,
    show_default=True,
    help="Correction strength from 0 (no change) to 1 (full correction).",
)
@click.option(
    "--quality",
    type=int,
    default=90,
    show_default=True,
    help="Re-encode quality for JPEG-backed page images.",
)
def main(input_pdf, output_pdf, method, percentile, strength, quality):
    """Adjust the white balance of every raster page image in INPUT_PDF
    (e.g. a scanned/photographed book with a color cast) and write the
    result to OUTPUT_PDF. Pages with no embedded images, or images with no
    color channels (grayscale/1-bit), are left unchanged."""
    if not 0.0 <= strength <= 1.0:
        raise click.BadParameter("--strength must be between 0 and 1")

    opts = WhiteBalanceOptions(method=method, percentile=percentile, strength=strength, quality=quality)
    adjust_pdf_white_balance(input_pdf, output_pdf, opts, echo=click.echo)
    click.echo(f"Wrote {output_pdf}")


if __name__ == "__main__":
    main()
