"""Builds the print stylesheet: page geometry, typography, page-number
style/position, and table-of-contents leader/page-number formatting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_MARGIN_BOX = {
    "bottom-center": "@bottom-center",
    "bottom-left": "@bottom-left",
    "bottom-right": "@bottom-right",
    "top-center": "@top-center",
    "top-left": "@top-left",
    "top-right": "@top-right",
}

VALID_POSITIONS = ("none", *sorted(_MARGIN_BOX))
VALID_NUMBER_STYLES = (
    "none",
    "decimal",
    "decimal-leading-zero",
    "lower-roman",
    "upper-roman",
    "lower-alpha",
    "upper-alpha",
)


@dataclass
class PdfOptions:
    page_width: str = "6in"
    page_height: str = "9in"
    margin_top: str = "0.75in"
    margin_right: str = "0.75in"
    margin_bottom: str = "0.75in"
    margin_left: str = "0.75in"
    mirror_margins: bool = False
    font_family: str = "Georgia, 'Times New Roman', serif"
    font_file: str | None = None
    font_size: str = "11pt"
    line_height: str = "1.4"
    page_number_style: str = "decimal"
    page_number_position: str = "bottom-center"
    paragraph_indent: bool = True


def _font_face_and_family(opts: PdfOptions) -> tuple[str, str]:
    if opts.font_file:
        path = Path(opts.font_file).expanduser().resolve()
        font_face = f"""
@font-face {{
  font-family: "EmbeddedBookFont";
  src: url("file://{path}");
}}
"""
        return font_face, '"EmbeddedBookFont"'
    return "", opts.font_family


def _page_number_rule(opts: PdfOptions) -> str:
    if opts.page_number_position == "none" or opts.page_number_style == "none":
        return ""
    box = _MARGIN_BOX[opts.page_number_position]
    return f"""
  {box} {{
    content: counter(page, {opts.page_number_style});
    font-size: 0.85em;
  }}"""


def _mirror_margin_rules(opts: PdfOptions) -> str:
    if not opts.mirror_margins:
        return ""
    return f"""
@page :left {{
  margin-left: {opts.margin_right};
  margin-right: {opts.margin_left};
}}
@page :right {{
  margin-left: {opts.margin_left};
  margin-right: {opts.margin_right};
}}
"""


def build_css(opts: PdfOptions) -> str:
    font_face, font_family_css = _font_face_and_family(opts)
    page_number_rule = _page_number_rule(opts)
    mirror_rules = _mirror_margin_rules(opts)
    indent_rule = "1.3em" if opts.paragraph_indent else "0"

    return f"""
{font_face}
@page {{
  size: {opts.page_width} {opts.page_height};
  margin-top: {opts.margin_top};
  margin-right: {opts.margin_right};
  margin-bottom: {opts.margin_bottom};
  margin-left: {opts.margin_left};{page_number_rule}
}}
{mirror_rules}
html {{
  font-family: {font_family_css};
  font-size: {opts.font_size};
  line-height: {opts.line_height};
}}
body {{
  margin: 0;
  padding: 0;
  orphans: 2;
  widows: 2;
}}
p {{
  margin: 0;
  text-indent: {indent_rule};
}}
.epub-chapter > p:first-child,
h1 + p, h2 + p, h3 + p, h4 + p {{
  text-indent: 0;
}}
h1, h2, h3, h4 {{
  font-family: {font_family_css};
  break-after: avoid;
  margin: 1.2em 0 0.6em 0;
  text-indent: 0;
}}
img {{
  max-width: 100%;
  break-inside: avoid;
}}
blockquote {{
  margin: 1em 2em;
}}
.epub-chapter {{
  break-before: page;
}}

.title-page {{
  break-after: page;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 90vh;
  text-align: center;
}}
.title-page .title-main {{
  font-size: 2em;
  margin-bottom: 0.5em;
}}
.title-page .title-author {{
  font-size: 1.2em;
  font-style: italic;
}}

.toc-page {{
  break-after: page;
}}
.toc-page .toc-heading {{
  text-align: center;
  margin-bottom: 1em;
}}
.toc-page ol {{
  list-style: none;
  padding-left: 0;
  margin: 0;
}}
.toc-page li li {{
  padding-left: 1.2em;
  font-size: 0.95em;
}}
.toc-page li {{
  margin: 0.35em 0;
}}
.toc-page a {{
  display: flex;
  align-items: baseline;
  text-decoration: none;
  color: inherit;
}}
.toc-page a .toc-title {{
  order: 1;
}}
.toc-page a::before {{
  content: "";
  order: 2;
  flex: 1 1 auto;
  margin: 0 0.35em;
  border-bottom: 1px dotted #888;
}}
.toc-page a::after {{
  content: target-counter(attr(href), page);
  order: 3;
}}
.toc-page .toc-unlinked {{
  font-weight: bold;
}}
"""
