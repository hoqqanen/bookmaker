from __future__ import annotations

import click

from .imposition import SHEET_SIZES_MM, impose_booklet


@click.command(name="impose")
@click.argument("input_pdf", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_dir", type=click.Path(file_okay=False))
@click.option(
    "--sheet-size",
    type=click.Choice(sorted(SHEET_SIZES_MM)),
    default="a4",
    show_default=True,
    help="Physical sheet printed on (source pages are laid out 2-up per side).",
)
@click.option(
    "--signature-size",
    type=int,
    default=8,
    show_default=True,
    help="Target page count per signature. Signatures are balanced to be as "
    "equal-sized as possible (e.g. 22 pages -> 8/7/7, not 8/8/6), then each "
    "is padded with trailing blank pages up to a multiple of 4.",
)
@click.option("--output-prefix", default="signature", show_default=True)
def main(input_pdf, output_dir, sheet_size, signature_size, output_prefix):
    """Impose a flat, sequentially-paginated INPUT_PDF into signature
    booklets (2-up, front/back) written to OUTPUT_DIR, ready to be printed,
    folded, and bound together."""
    if signature_size < 1:
        raise click.BadParameter("--signature-size must be at least 1")

    paths = impose_booklet(
        input_pdf,
        output_dir,
        signature_size=signature_size,
        sheet_size=sheet_size,
        output_prefix=output_prefix,
    )
    for p in paths:
        click.echo(f"Wrote {p}")
    click.echo(f"See {output_dir}/PRINTING_INSTRUCTIONS.txt for folding/binding order.")


if __name__ == "__main__":
    main()
