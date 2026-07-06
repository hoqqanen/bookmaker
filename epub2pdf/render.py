"""WeasyPrint invocation, isolated in its own module so the macOS dynamic
library path fix happens before weasyprint (and its cffi bindings to
Pango/cairo/gobject) gets imported anywhere else."""

from __future__ import annotations

import os
import sys

if sys.platform == "darwin":
    # Homebrew's Pango/cairo/gobject libs aren't on the default dyld search
    # path, and WeasyPrint loads them via ctypes at import time.
    for _prefix in ("/opt/homebrew/lib", "/usr/local/lib"):
        if os.path.isdir(_prefix):
            for _var in ("DYLD_LIBRARY_PATH", "DYLD_FALLBACK_LIBRARY_PATH"):
                existing = os.environ.get(_var, "")
                if _prefix not in existing.split(":"):
                    os.environ[_var] = f"{_prefix}:{existing}" if existing else _prefix

import weasyprint  # noqa: E402


def render_pdf(html_path: str, output_path: str) -> None:
    weasyprint.HTML(filename=html_path).write_pdf(output_path)
