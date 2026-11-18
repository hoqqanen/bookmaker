# Bookmaker.app

A native macOS front end for the two epub2pdf commands:

- **EPUB** → `python -m epub2pdf.book` (typeset + impose)
- **PDF** → `python -m epub2pdf.impose_cli` (impose only)

Drag files into the window (or onto the Dock icon). Each one is copied into
the library (`~/Documents/Bookmaker Library` by default, one folder per book)
and built with your default settings. Select a book to preview the imposed PDF
or the reading copy, change its margins, font, and imposition settings in the
inspector, then Rebuild. ⌘P prints at actual size with short-edge duplex
pre-selected.

Defaults for new books, the library folder, and the repo location are in
Settings (⌘,).

## Build

    ./build_app.sh        # -> build/Bookmaker.app

The app runs the Python code from this repo using `.venv/bin/python`, so keep
the venv set up (`pip install -r requirements.txt`). Copy the app into
/Applications if you like; it still points back at this repo.
