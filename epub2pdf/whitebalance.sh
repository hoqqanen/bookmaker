#!/bin/bash
# Adjust the white balance of every page in a scanned/photographed PDF and
# write a new PDF, using only macOS `sips` and ImageMagick's `magick`
# (which needs Ghostscript on PATH to read/write PDF pages).
#
# Pipeline per page:
#   1. magick + gs rasterizes the page to PNG at --density DPI
#   2. sips strips any embedded ICC profile, so the white-balance step below
#      operates on consistent raw RGB instead of whatever profile the
#      scanner/camera tagged the image with
#   3. magick's -white-balance auto-corrects the color cast
#   4. magick's -brightness-contrast optionally brightens the page
# All corrected pages are then reassembled into a single output PDF.
#
# Usage: whitebalance.sh INPUT_PDF OUTPUT_PDF [DENSITY] [BRIGHTNESS]
#   DENSITY: rasterization DPI, default 300
#   BRIGHTNESS: -100 to 100, default 0 (no change); e.g. 15 for a modest lift

set -euo pipefail

if [[ $# -lt 2 || $# -gt 4 ]]; then
    echo "Usage: $0 INPUT_PDF OUTPUT_PDF [DENSITY] [BRIGHTNESS]" >&2
    exit 1
fi

input_pdf=$1
output_pdf=$2
density=${3:-300}
brightness=${4:-0}

for cmd in magick sips; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "error: '$cmd' not found on PATH" >&2; exit 1; }
done
[[ -f "$input_pdf" ]] || { echo "error: no such file: $input_pdf" >&2; exit 1; }

workdir=$(mktemp -d "${TMPDIR:-/tmp}/whitebalance.XXXXXX")
trap 'rm -rf "$workdir"' EXIT

page_count=$(magick identify "$input_pdf" 2>/dev/null | wc -l | tr -d ' ')
echo "Pages: $page_count"

corrected_pages=()
for ((i = 0; i < page_count; i++)); do
    page_num=$(printf "%04d" "$i")
    raw_png="$workdir/page_${page_num}.png"
    corrected_png="$workdir/page_${page_num}_wb.png"

    echo "  page $((i + 1))/$page_count ..."
    magick -density "$density" "${input_pdf}[$i]" "$raw_png"
    sips --deleteColorManagementProperties "$raw_png" >/dev/null 2>&1
    if [[ "$brightness" -ne 0 ]]; then
        magick "$raw_png" -white-balance -brightness-contrast "${brightness}x0" "$corrected_png"
    else
        magick "$raw_png" -white-balance "$corrected_png"
    fi

    corrected_pages+=("$corrected_png")
done

magick "${corrected_pages[@]}" "$output_pdf"
echo "Wrote $output_pdf"
