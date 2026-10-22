"""Build the PASADHI solution paper as a PDF (A4, cover, page numbers).

    python scripts/build_solution_pdf.py
"""
from __future__ import annotations

import io
import re
import subprocess
from pathlib import Path

import markdown
from pypdf import PdfReader, PdfWriter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'pasadhi' / 'paper' / 'SOLUTION.md'
OUTPUT = ROOT / 'landing-pasadhi' / 'download' / 'PASADHI-solution.pdf'
BUILD = ROOT / 'pasadhi' / 'paper' / '_build'
EDGE = Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')

CSS = """
@page { size: A4; margin: 20mm 18mm 22mm 18mm; }
body { font-family: "Charter", Georgia, "Times New Roman", serif; font-size: 10.6pt; line-height: 1.58; color: #14302a; }
h1, h2, h3 { font-family: "Segoe UI", Arial, sans-serif; color: #0f4f3c; }
h1 { font-size: 24pt; line-height: 1.16; margin: 0 0 6mm; letter-spacing: -0.01em; }
h2 { font-size: 14.5pt; margin: 8mm 0 3mm; break-after: avoid; }
h3 { font-size: 11.5pt; margin: 6mm 0 2mm; }
p { margin: 0 0 3mm; text-align: justify; }
table { width: 100%; border-collapse: collapse; font-size: 8.9pt; margin: 3mm 0 5mm; break-inside: avoid; }
th { background: #e9f5ef; text-align: left; }
th, td { border: 0.25mm solid #cfded6; padding: 1.6mm 2mm; vertical-align: top; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #f2f6f4; padding: 0.3mm 1mm; }
pre { background: #f5f9f7; border: 0.3mm solid #d9e7e0; border-radius: 1.5mm; padding: 4mm; break-inside: avoid; }
pre code { font-size: 8.6pt; line-height: 1.45; background: none; }
ul { margin: 0 0 3mm 0; padding-left: 6mm; }
li { margin-bottom: 1.4mm; }
.cover { height: 244mm; display: flex; flex-direction: column; justify-content: space-between; }
.cover .kicker { font: 700 9pt "Segoe UI", sans-serif; letter-spacing: 0.18em; color: #159a72; }
.cover .rule { width: 44mm; height: 1.4mm; background: #159a72; margin: 6mm 0; }
.cover .meta { font: 9pt "Segoe UI", sans-serif; color: #4a675c; line-height: 1.9; }
.toc { break-before: page; }
.toc ol { list-style: none; padding: 0; }
.toc li { border-bottom: 0.2mm dotted #c8d8d0; padding: 2mm 0; font: 10pt "Segoe UI", sans-serif; display: flex; gap: 8mm; }
.toc .num { color: #159a72; font-weight: 700; width: 10mm; }
"""


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    (OUTPUT.parent).mkdir(parents=True, exist_ok=True)
    text = SOURCE.read_text(encoding='utf-8')

    lines = text.splitlines()
    title = next(line[2:].strip() for line in lines if line.startswith('# '))
    body_md = '\n'.join(lines[1:])
    body_html = markdown.markdown(body_md, extensions=['tables', 'fenced_code', 'sane_lists'])

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<style>{CSS}</style></head><body>
<section class="cover">
  <div><p class="kicker">PASADHI · SOLUTION PAPER</p><div class="rule"></div><h1>{title}</h1></div>
  <div class="meta">PASADHI contributors · v1.0<br>23 October 2026 · MIT for the open core<br>
    github.com/camponggogo/pasadhi · pasadhi.tech</div>
</section>
{body_html}
</body></html>"""
    html_path = BUILD / 'solution.html'
    html_path.write_text(html, encoding='utf-8')

    raw_pdf = BUILD / 'solution-raw.pdf'
    command = [str(EDGE), '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
               '--virtual-time-budget=8000', f'--print-to-pdf={raw_pdf}', html_path.as_uri()]
    subprocess.run(command, capture_output=True, text=True)
    if not raw_pdf.exists():
        raise SystemExit('edge produced no pdf')

    reader = PdfReader(raw_pdf)
    writer = PdfWriter()
    total = len(reader.pages)
    for index, page in enumerate(reader.pages):
        if index > 0:
            buffer = io.BytesIO()
            width, height = float(page.mediabox.width), float(page.mediabox.height)
            layer = canvas.Canvas(buffer, pagesize=(width, height))
            layer.setStrokeColorRGB(0.82, 0.87, 0.84)
            layer.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
            layer.setFont('Helvetica', 7.2)
            layer.setFillColorRGB(0.33, 0.42, 0.38)
            layer.drawString(18 * mm, 10.4 * mm, 'PASADHI solution paper · v1.0 · 23 October 2026')
            layer.drawRightString(width - 18 * mm, 10.4 * mm, f'{index + 1} / {total}')
            layer.save()
            buffer.seek(0)
            page.merge_page(PdfReader(buffer).pages[0])
        writer.add_page(page)
    writer.add_metadata({'/Title': 'PASADHI: one pool from the machines you already own',
                         '/Author': 'PASADHI contributors',
                         '/Subject': 'Solution paper: measured architecture, pricing and roadmap',
                         '/Keywords': 'distributed inference, office hardware, matrix compute, pricing'})
    with open(OUTPUT, 'wb') as handle:
        writer.write(handle)
    print('pages', total, 'size', round(OUTPUT.stat().st_size / 1024, 1), 'KB', OUTPUT)


if __name__ == '__main__':
    main()
