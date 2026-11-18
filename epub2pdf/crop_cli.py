from __future__ import annotations

import click

from .crop import crop_pdf


@click.command(name="crop")
@click.argument("input_pdf", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_pdf", type=click.Path(dir_okay=False))
@click.option("--margin", type=float, default=0.0, show_default=True, help="Shorthand that sets all four margins at once, in inches.")
@click.option("--top", "top", type=float, default=None, help="Inches to remove from the top. Overrides --margin.")
@click.option("--right", "right", type=float, default=None, help="Inches to remove from the right. Overrides --margin.")
@click.option("--bottom", "bottom", type=float, default=None, help="Inches to remove from the bottom. Overrides --margin.")
@click.option("--left", "left", type=float, default=None, help="Inches to remove from the left. Overrides --margin.")
def main(input_pdf, output_pdf, margin, top, right, bottom, left):
    """Crop the margins of INPUT_PDF by insetting each page's visible area
    and write the result to OUTPUT_PDF. Cropping is done by shrinking each
    page's MediaBox/CropBox, so it's lossless and reversible (just recrop
    the original with different margins)."""
    top = margin if top is None else top
    right = margin if right is None else right
    bottom = margin if bottom is None else bottom
    left = margin if left is None else left

    if min(top, right, bottom, left) < 0:
        raise click.BadParameter("margins must be >= 0")

    crop_pdf(input_pdf, output_pdf, left=left, right=right, top=top, bottom=bottom, echo=click.echo)
    click.echo(f"Wrote {output_pdf}")


if __name__ == "__main__":
    main()
