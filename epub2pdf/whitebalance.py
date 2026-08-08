"""Per-page white balance correction for PDFs made of scanned/photographed
page images (each page is one embedded raster image, e.g. from a camera or
scanner with a color cast). Vector/text-only pages are left untouched since
there's no color cast to correct.

Two correction methods, both implemented as a per-channel lookup table built
from the image's histogram (no numpy/image-rendering dependency needed):

- "gray-world": assumes the average color of a page should be neutral gray.
  Scales each channel so its mean matches the overall mean. Gentle, good
  default for general color-cast removal.
- "white-patch": assumes the brightest pixels (e.g. the paper background)
  should be pure white. Scales each channel so a given brightness percentile
  maps to 255. Stronger correction, best when the paper itself is visibly
  tinted (e.g. sepia scans).
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image
from pypdf import PdfWriter

METHODS = ("gray-world", "white-patch")


@dataclass
class WhiteBalanceOptions:
    method: str = "gray-world"
    percentile: float = 99.5  # only used by "white-patch"
    strength: float = 1.0  # 0 = no change, 1 = full correction
    quality: int = 90  # re-encode quality for JPEG-backed images


def _channel_means(histograms: list[list[int]]) -> list[float]:
    means = []
    for hist in histograms:
        total = sum(hist)
        if total == 0:
            means.append(0.0)
            continue
        means.append(sum(v * count for v, count in enumerate(hist)) / total)
    return means


def _channel_percentile_values(histograms: list[list[int]], percentile: float) -> list[int]:
    values = []
    for hist in histograms:
        total = sum(hist)
        if total == 0:
            values.append(255)
            continue
        target = total * percentile / 100.0
        cumulative = 0
        value = 255
        for v, count in enumerate(hist):
            cumulative += count
            if cumulative >= target:
                value = v
                break
        values.append(max(value, 1))
    return values


def _channel_scales(rgb: Image.Image, method: str, percentile: float) -> list[float]:
    hist = rgb.histogram()
    histograms = [hist[i * 256 : (i + 1) * 256] for i in range(3)]

    if method == "gray-world":
        means = _channel_means(histograms)
        target = sum(means) / 3
        return [target / m if m > 0 else 1.0 for m in means]
    elif method == "white-patch":
        white_points = _channel_percentile_values(histograms, percentile)
        return [255.0 / wp for wp in white_points]
    else:
        raise ValueError(f"Unknown method {method!r}; choices: {METHODS}")


def apply_white_balance(image: Image.Image, opts: WhiteBalanceOptions) -> Image.Image | None:
    """Returns a color-corrected copy of `image`, or None if the image's mode
    has no color channels to correct (e.g. grayscale, 1-bit line art)."""
    if image.mode in ("L", "1", "LA", "P"):
        return None
    if image.mode == "RGBA":
        rgb = image.convert("RGB")
        alpha = image.getchannel("A")
    elif image.mode == "RGB":
        rgb = image
        alpha = None
    else:
        # CMYK and other exotic modes: skip rather than risk a bad color
        # conversion round-trip.
        return None

    scales = _channel_scales(rgb, opts.method, opts.percentile)
    bands = rgb.split()
    out_bands = []
    for band, scale in zip(bands, scales):
        effective_scale = 1.0 + opts.strength * (scale - 1.0)
        lut = [min(255, max(0, round(v * effective_scale))) for v in range(256)]
        out_bands.append(band.point(lut))
    corrected = Image.merge("RGB", out_bands)

    if alpha is not None:
        corrected = corrected.convert("RGBA")
        corrected.putalpha(alpha)
    return corrected


def adjust_pdf_white_balance(
    input_pdf: str,
    output_pdf: str,
    opts: WhiteBalanceOptions,
    echo=lambda msg: None,
) -> None:
    writer = PdfWriter(clone_from=input_pdf)

    adjusted_count = 0
    skipped_count = 0
    for page_num, page in enumerate(writer.pages, start=1):
        images = page.images
        if not images:
            continue
        for image in images:
            corrected = apply_white_balance(image.image, opts)
            if corrected is None:
                skipped_count += 1
                continue
            image.replace(corrected, quality=opts.quality)
            adjusted_count += 1
        echo(f"  page {page_num}: {len(images)} image(s)")

    writer.write(output_pdf)
    echo(f"Adjusted {adjusted_count} image(s), skipped {skipped_count} (no color channels to correct)")
