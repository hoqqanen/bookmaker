from __future__ import annotations

import os

import click

from .imposition import SHEET_SIZES_MM, impose_booklet


@click.command(name="impose")
@click.argument("input_pdf", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_pdf", type=click.Path(dir_okay=False))
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
    help="Target number of physical SHEETS of paper per signature (each sheet = "
    "4 content pages once folded, so the default is 32 content pages per "
    "signature). Signatures are balanced to be as equal-sized as possible "
    "(e.g. 44 sheets -> 8/8/7/7/7/7, not a lopsided last signature); only the "
    "very last signature is ever padded with trailing blank pages.",
)
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
def main(input_pdf, output_pdf, sheet_size, signature_size, sheet_order):
    """Impose a flat, sequentially-paginated INPUT_PDF into a single
    signature-imposed OUTPUT_PDF (2-up, front/back, all signatures
    concatenated in binding order), ready to be printed, folded, and bound
    together."""
    if signature_size < 1:
        raise click.BadParameter("--signature-size must be at least 1")

    impose_booklet(
        input_pdf,
        output_pdf,
        sheets_per_signature=signature_size,
        sheet_size=sheet_size,
        print_innermost_first=(sheet_order == "innermost-first"),
    )
    instructions_path = os.path.splitext(output_pdf)[0] + "_INSTRUCTIONS.txt"
    click.echo(f"Wrote {output_pdf}")
    click.echo(f"See {instructions_path} for folding/binding order.")


if __name__ == "__main__":
    main()
