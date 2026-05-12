"""Convert PDF pages to PNG images for review by Claude."""
import sys
from pathlib import Path
import fitz  # PyMuPDF

PDF = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else PDF.parent / "_pdf_pages"
OUT.mkdir(exist_ok=True, parents=True)

doc = fitz.open(PDF)
print(f"PDF has {len(doc)} pages")
for i, page in enumerate(doc, start=1):
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 150% zoom
    out = OUT / f"page_{i:02d}.png"
    pix.save(str(out))
    print(f"  -> {out}")
print("Done")
