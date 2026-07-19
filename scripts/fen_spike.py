"""
ROADMAP Step 1.2 — Board-diagram → FEN spike.

Extracts 5 board-diagram images from the first PDF in data/books/,
sends each to Gemini via cfaios/infra/llm_google.py, validates the
returned FEN with python-chess, and reports the hit rate.

A "hit" = Gemini returned a parseable FEN that python-chess accepts
as a legal position (board.is_valid()).

DIAGNOSTIC ONLY — does not touch any agent, the constitution, or the
KnowledgeAPI. No writes to any store.

Usage:
    python scripts/fen_spike.py [--pdf path/to/file.pdf] [--n 5]
"""
from __future__ import annotations

import argparse
import io
import pathlib
import re
import sys

BOOKS_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "books"
N_SAMPLES = 5

# Pages to skip at the start and end of the PDF (cover, catalog, index).
SKIP_FRONT = 5
SKIP_BACK = 5
# Render resolution in DPI — 120 is crisp enough for Gemini to read a board.
RENDER_DPI = 120


# ---------------------------------------------------------------------------
# Image extraction from PDF
# ---------------------------------------------------------------------------

def _page_to_png(page) -> bytes:
    """Render a full PDF page to PNG bytes."""
    pil_img = page.to_image(resolution=RENDER_DPI).original
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


def extract_board_images(pdf_path: pathlib.Path, n: int) -> list[tuple[int, bytes]]:
    """Return up to n (page_number, png_bytes) tuples from evenly-spaced pages.

    Chess boards in this corpus are vector graphics drawn with PDF drawing
    commands — not embedded bitmap images — so pdfplumber's page.images only
    finds tiny decorative bitmaps.  Rendering the full page and letting Gemini
    locate the board is the correct approach.
    """
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        # Exclude likely cover/catalog pages at front and back
        start = min(SKIP_FRONT, total - 1)
        end = max(start + 1, total - SKIP_BACK)
        interior = list(range(start, end))

        if not interior:
            return []

        # Pick n evenly spaced page indices
        step = max(1, len(interior) // n)
        chosen = [interior[min(i * step, len(interior) - 1)] for i in range(n)]

        results = []
        for page_idx in chosen:
            page = pdf.pages[page_idx]
            try:
                png = _page_to_png(page)
                results.append((page_idx + 1, png))  # 1-indexed
            except Exception as exc:
                print(f"  [warn] page {page_idx+1}: render failed — {exc}")
    return results


# ---------------------------------------------------------------------------
# FEN parsing and validation
# ---------------------------------------------------------------------------

# Matches the piece-placement part of a FEN (8 ranks separated by /)
_FEN_RE = re.compile(
    r"[rnbqkpRNBQKP1-8]{1,8}"
    r"(?:/[rnbqkpRNBQKP1-8]{1,8}){7}"
)


def parse_fen_from_text(text: str) -> str | None:
    """Extract the first FEN-like substring from Gemini's response."""
    text = text.strip()
    m = _FEN_RE.search(text)
    if m:
        return m.group(0)
    # Last-resort: if response is a single line with 7 slashes
    line = text.splitlines()[0].strip()
    if line.count("/") == 7:
        return line
    return None


def validate_fen(placement: str) -> tuple[bool, str]:
    """Return (is_legal, message). Tries piece-placement + default move fields."""
    import chess

    full_fen = placement + " w - - 0 1"
    try:
        board = chess.Board(full_fen)
        if board.is_valid():
            return True, "legal position"
        return False, "position is parseable but invalid (kings/check)"
    except ValueError as exc:
        return False, f"FEN parse error: {exc}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="FEN spike — board diagram → Gemini → python-chess")
    parser.add_argument("--pdf", type=pathlib.Path, default=None,
                        help="PDF to use (default: first PDF in data/books/)")
    parser.add_argument("--n", type=int, default=N_SAMPLES,
                        help=f"Number of diagrams to sample (default {N_SAMPLES})")
    parser.add_argument("--model", type=str, default=None,
                        help="Gemini model override (e.g. gemini-1.5-flash)")
    args = parser.parse_args()

    # Resolve PDF
    if args.pdf:
        pdf_path = args.pdf
    else:
        pdfs = sorted(BOOKS_DIR.glob("*.pdf"))
        if not pdfs:
            print("[fen_spike] No PDFs found in data/books/. Add a PDF and re-run.")
            sys.exit(1)
        pdf_path = pdfs[0]

    print(f"[fen_spike] PDF      : {pdf_path.name}")
    print(f"[fen_spike] Samples  : {args.n}")
    print()

    # Initialise Gemini client (fails fast if API key not set)
    from cfaios.infra.llm_google import GoogleClient
    client = GoogleClient(model=args.model)
    print(f"[fen_spike] Model    : {client.model}")
    try:
        client.connect()
    except RuntimeError as exc:
        print(f"[fen_spike] ERROR: {exc}")
        sys.exit(1)

    # Extract board diagram images
    print(f"[fen_spike] Extracting board-diagram images …")
    images = extract_board_images(pdf_path, args.n)
    if not images:
        print("[fen_spike] No board-diagram images found. Check MIN_AREA_FRACTION / aspect filters.")
        sys.exit(1)
    print(f"[fen_spike] Found {len(images)} candidate diagram(s). Querying Gemini …\n")

    # Per-image results
    hits = 0
    rows: list[dict] = []

    for page_num, png_bytes in images:
        print(f"  Page {page_num:>3}  ({len(png_bytes)//1024} KB PNG)  … ", end="", flush=True)
        try:
            raw = client.vision_to_fen(png_bytes)
        except Exception as exc:
            print(f"API ERROR: {exc}")
            rows.append({"page": page_num, "raw": "", "fen": None, "legal": False, "note": str(exc)})
            continue

        fen = parse_fen_from_text(raw)
        if fen is None:
            print(f"PARSE FAIL  (response: {raw[:80]!r})")
            rows.append({"page": page_num, "raw": raw, "fen": None, "legal": False, "note": "could not extract FEN pattern"})
            continue

        legal, note = validate_fen(fen)
        tag = "HIT ✓" if legal else "MISS ✗"
        print(f"{tag}  {fen[:60]}")
        if legal:
            hits += 1
        rows.append({"page": page_num, "raw": raw, "fen": fen, "legal": legal, "note": note})

    # Summary
    total = len(rows)
    print(f"\n{'='*68}")
    print(f"  FEN SPIKE RESULTS  —  {pdf_path.name}")
    print(f"{'='*68}")
    print(f"  {'Page':>5}  {'FEN (truncated)':<50}  Result")
    print(f"  {'-'*5}  {'-'*50}  {'-'*10}")
    for r in rows:
        fen_disp = (r["fen"] or r["raw"])[:50] if (r["fen"] or r["raw"]) else "(no output)"
        result = "HIT" if r["legal"] else ("PARSE FAIL" if r["fen"] is None else "INVALID")
        print(f"  {r['page']:>5}  {fen_disp:<50}  {result}")

    hit_rate = hits / total if total else 0.0
    print(f"\n  Hit rate: {hits}/{total}  ({hit_rate:.0%})  — "
          f"'hit' = Gemini returned a legal chess position per python-chess")

    if hit_rate == 1.0:
        verdict = "EXCELLENT — vision FEN extraction is reliable for this corpus."
    elif hit_rate >= 0.6:
        verdict = "ACCEPTABLE — most diagrams convert; spot-check the misses."
    elif hit_rate >= 0.4:
        verdict = "MARGINAL — significant failure rate; Agent 1 needs a fallback strategy."
    else:
        verdict = "POOR — vision FEN extraction is unreliable for this corpus; rethink Agent 1 design."

    print(f"  Verdict : {verdict}")
    print()


if __name__ == "__main__":
    main()
