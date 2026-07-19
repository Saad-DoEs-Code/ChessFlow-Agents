"""
ROADMAP Step 1.1 — Corpus probe.

Runs each book in data/books/ through raw text extraction and reports per file:
  - filename, format, size
  - extracted character count
  - gibberish ratio  (control chars + mojibake heuristic)
  - embedded-image presence (candidate board diagrams in PDFs)
  - 3 evenly-spaced sample paragraphs

Prints a summary table classifying every book as CLEAN / OCR-NOISY / UNUSABLE.

DIAGNOSTIC ONLY — does not touch any agent, the constitution, or the KnowledgeAPI.

Usage:
    python scripts/corpus_probe.py
"""
from __future__ import annotations

import pathlib
import sys
import unicodedata
import warnings
from dataclasses import dataclass
from html.parser import HTMLParser

BOOKS_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "books"
SUPPORTED = {".pdf", ".epub"}

# Classification thresholds
_CLEAN_MAX = 0.02        # ≤ 2 % gibberish → CLEAN
_NOISY_MAX = 0.15        # ≤ 15 % → OCR-NOISY; above → UNUSABLE
_MIN_CH_PER_KB = 8       # fewer chars per KB → likely image-only scanned PDF


# ---------------------------------------------------------------------------
# Text-quality heuristic
# ---------------------------------------------------------------------------

def _gibberish_ratio(text: str) -> float:
    """Return the fraction of characters that look like extraction noise.

    Signals counted:
    - Control characters (U+0000–U+001F) except \\n \\r \\t
    - Unicode replacement character U+FFFD
    - Excess Latin-1 Supplement (U+0080–U+00FF): up to 5 % is normal for
      accented names and typographic symbols; above that it suggests bytes
      decoded with the wrong codec (mojibake).
    """
    if not text:
        return 1.0
    n = len(text)
    ctrl = 0
    latin_ext = 0
    for ch in text:
        cp = ord(ch)
        if (cp < 0x20 and ch not in "\n\r\t") or ch == "�":
            ctrl += 1
        elif 0x80 <= cp <= 0xFF:
            latin_ext += 1
    mojibake = max(0.0, latin_ext / n - 0.05) * 2.0
    return min(ctrl / n + mojibake, 1.0)


def _samples(text: str, n: int = 3) -> list[str]:
    """Return n evenly-spaced paragraphs of up to 300 chars each."""
    paras = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 80]
    if not paras:
        chunk = 300
        paras = [text[i : i + chunk].strip() for i in range(0, len(text), chunk)
                 if text[i : i + chunk].strip()]
    if not paras:
        return ["(no text extracted)"]
    step = max(1, len(paras) // n)
    chosen = [paras[min(i * step, len(paras) - 1)] for i in range(n)]
    return [p[:300] for p in chosen]


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def _extract_pdf(path: pathlib.Path) -> tuple[str, int, int]:
    """Returns (full_text, total_pages, image_page_count)."""
    import pdfplumber

    parts: list[str] = []
    image_pages = 0
    with pdfplumber.open(path) as pdf:
        total = len(pdf.pages)
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
            if page.images:
                image_pages += 1
    return "\n\n".join(parts), total, image_pages


# ---------------------------------------------------------------------------
# EPUB extraction
# ---------------------------------------------------------------------------

class _HTMLStripper(HTMLParser):
    _SKIP = {"script", "style"}

    def __init__(self) -> None:
        super().__init__()
        self._buf: list[str] = []
        self._depth = 0

    def handle_starttag(self, tag: str, _attrs) -> None:  # type: ignore[override]
        if tag in self._SKIP:
            self._depth += 1

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag in self._SKIP:
            self._depth = max(0, self._depth - 1)

    def handle_data(self, data: str) -> None:
        if not self._depth:
            s = data.strip()
            if s:
                self._buf.append(s)

    @property
    def text(self) -> str:
        return "\n".join(self._buf)


def _extract_epub(path: pathlib.Path) -> str:
    import ebooklib
    from ebooklib import epub

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        book = epub.read_epub(str(path))

    parts: list[str] = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        raw = item.get_content().decode("utf-8", errors="replace")
        stripper = _HTMLStripper()
        stripper.feed(raw)
        t = stripper.text.strip()
        if t:
            parts.append(t)
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Per-file report
# ---------------------------------------------------------------------------

@dataclass
class BookReport:
    filename: str
    fmt: str
    size_kb: float
    char_count: int
    gibberish: float
    has_images: bool
    image_page_count: int
    total_pages: int
    samples: list[str]
    classification: str
    notes: str
    error: str = ""


def _classify(char_count: int, size_kb: float, gibberish: float) -> tuple[str, str]:
    ch_per_kb = char_count / max(size_kb, 1.0)
    if char_count < 500 or ch_per_kb < _MIN_CH_PER_KB:
        return (
            "UNUSABLE",
            f"only {char_count:,} chars from {size_kb:.0f} KB "
            f"({ch_per_kb:.1f} ch/KB) — likely scanned / image-only",
        )
    if gibberish > _NOISY_MAX:
        return "UNUSABLE", f"gibberish {gibberish:.1%} exceeds {_NOISY_MAX:.0%} — too corrupted"
    if gibberish > _CLEAN_MAX:
        return "OCR-NOISY", f"gibberish {gibberish:.1%} — detectable noise, may need cleaning"
    return "CLEAN", f"gibberish {gibberish:.1%}, {ch_per_kb:.0f} ch/KB"


def probe(path: pathlib.Path) -> BookReport:
    size_kb = path.stat().st_size / 1024
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            text, total_pages, image_pages = _extract_pdf(path)
            fmt = f"PDF ({total_pages}pp)"
            has_images = image_pages > 0
        elif suffix == ".epub":
            text = _extract_epub(path)
            fmt, total_pages, image_pages, has_images = "EPUB", 0, 0, False
        else:
            return BookReport(path.name, suffix, size_kb, 0, 1.0,
                              False, 0, 0, ["(unsupported format)"],
                              "UNUSABLE", "unsupported format")

        gibberish = _gibberish_ratio(text)
        label, notes = _classify(len(text), size_kb, gibberish)
        return BookReport(
            filename=path.name,
            fmt=fmt,
            size_kb=size_kb,
            char_count=len(text),
            gibberish=gibberish,
            has_images=has_images,
            image_page_count=image_pages,
            total_pages=total_pages,
            samples=_samples(text),
            classification=label,
            notes=notes,
        )
    except Exception as exc:
        return BookReport(
            filename=path.name, fmt=suffix, size_kb=size_kb,
            char_count=0, gibberish=1.0, has_images=False,
            image_page_count=0, total_pages=0, samples=[],
            classification="UNUSABLE", notes="extraction error",
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

_W = 72
_NAME_COL = 40


def _print_detail(r: BookReport) -> None:
    print(f"\n{'=' * _W}")
    print(f"  {r.filename}")
    print(f"  Format    : {r.fmt}  |  Size: {r.size_kb:.1f} KB")
    print(f"  Chars     : {r.char_count:,}  |  Gibberish: {r.gibberish:.2%}")
    if r.fmt.startswith("PDF"):
        img_str = (
            f"{r.image_page_count}/{r.total_pages} pages contain embedded images"
            if r.has_images else "no embedded images detected"
        )
        print(f"  Images    : {img_str}")
    print(f"  CLASS     : [{r.classification}]  — {r.notes}")
    if r.error:
        print(f"  ERROR     : {r.error}")
    if r.samples:
        print(f"\n  — Sample paragraphs —")
        for i, s in enumerate(r.samples, 1):
            preview = " ".join(s.split())[:280]
            print(f"  [{i}] {preview}")


def _print_summary(reports: list[BookReport]) -> None:
    print(f"\n{'=' * _W}")
    print(f"  CORPUS SUMMARY  ({len(reports)} file{'s' if len(reports) != 1 else ''})")
    print(f"{'=' * _W}")
    print(f"  {'File':<{_NAME_COL}} {'Format':<10} {'KB':>6}  {'Chars':>9}  {'Gibber':>7}  Class")
    print(f"  {'-' * _NAME_COL} {'-'*10} {'-'*6}  {'-'*9}  {'-'*7}  {'-'*10}")
    for r in reports:
        name = r.filename if len(r.filename) <= _NAME_COL else r.filename[:_NAME_COL - 1] + "…"
        fmt_s = r.fmt.split("(")[0].strip()
        print(
            f"  {name:<{_NAME_COL}} {fmt_s:<10} {r.size_kb:>6.0f}"
            f"  {r.char_count:>9,}  {r.gibberish:>7.2%}  {r.classification}"
        )
    counts: dict[str, int] = {}
    for r in reports:
        counts[r.classification] = counts.get(r.classification, 0) + 1
    print(f"\n  Result: " + "  |  ".join(f"{k} ×{v}" for k, v in sorted(counts.items())))
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if not BOOKS_DIR.exists():
        print("[corpus_probe] data/books/ does not exist.")
        sys.exit(0)

    files = sorted(f for f in BOOKS_DIR.iterdir() if f.suffix.lower() in SUPPORTED)
    if not files:
        print("[corpus_probe] data/books/ is empty — drop your PDFs/EPUBs there and re-run.")
        sys.exit(0)

    print(f"[corpus_probe] Probing {len(files)} file(s) …\n")
    reports: list[BookReport] = []
    for f in files:
        print(f"  → {f.name}  ({f.stat().st_size // 1024} KB)", flush=True)
        reports.append(probe(f))

    for r in reports:
        _print_detail(r)

    _print_summary(reports)


if __name__ == "__main__":
    main()
