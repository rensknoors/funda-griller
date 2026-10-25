"""PDF fixtures: small generated PDFs, and the real funda brochure from the prototype when present.

The brochure is a third party's document, so it is not committed: put a copy at
`tests/fixtures/local/brochure.pdf` (gitignored), or point `FG_BROCHURE_FIXTURE` at one. Tests that
need it skip without it.
"""

import os
from pathlib import Path

import pytest

BROCHURE_PATH = Path(os.environ.get("FG_BROCHURE_FIXTURE", Path(__file__).parent / "fixtures" / "local" / "brochure.pdf"))
BROCHURE_PAGES = 32


def make_pdf(pages: list[str]) -> bytes:
    """A minimal valid PDF with one line of text per page."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # Pages, filled in below
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    kids = []
    for text in pages:
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1")
        objects.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
        content_number = len(objects)
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>" % content_number
        )
        kids.append(f"{len(objects)} 0 R")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>".encode()
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


VRAGENLIJST = make_pdf(
    [
        "Vragenlijst voor de verkoop van een woning",
        "Is er asbest aanwezig? Ja, in de dakplaten van de schuur.",
        "Zijn er lekkages geweest? Nee.",
    ]
)


def real_brochure() -> bytes:
    if not BROCHURE_PATH.is_file():
        pytest.skip(f"real brochure fixture missing at {BROCHURE_PATH}")
    return BROCHURE_PATH.read_bytes()
