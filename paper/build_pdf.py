"""Build paper/SUAY-whitepaper.pdf from paper/WHITEPAPER.md.

Pipeline: Markdown → print HTML → headless Edge → footer stamping (reportlab + pypdf).
Two passes: the first render locates every section heading, the second writes real page numbers into the TOC.

    python paper/build_pdf.py
"""
import io
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'paper' / 'WHITEPAPER.md'
OUT = ROOT / 'paper' / 'SUAY-whitepaper.pdf'
BUILD = ROOT / 'paper' / '_build'
EDGE = Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')

CSS = """
@page { size: A4; margin: 20mm 18mm 22mm 18mm; }
html { -webkit-print-color-adjust: exact; }
body { font-family: "Charter", "Georgia", "Times New Roman", serif; font-size: 10.4pt; line-height: 1.55;
       color: #1a1a1a; margin: 0; }
h1, h2, h3, h4 { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; color: #10233a; }
h1 { font-size: 27pt; line-height: 1.15; margin: 0 0 6mm; letter-spacing: -0.01em; }
h2 { font-size: 15.5pt; margin: 0 0 4mm; padding-top: 2mm; }
.doc h2 { break-before: auto; break-after: avoid; margin-top: 9mm; }
.doc > h2:first-child { break-before: page; margin-top: 0; }
.toc h2 { break-before: auto; }
h3 { font-size: 12pt; margin: 7mm 0 2mm; }
h4 { font-size: 10.5pt; margin: 5mm 0 1.5mm; }
p { margin: 0 0 3.2mm; text-align: justify; hyphens: auto; }
ul, ol { margin: 0 0 3.5mm 0; padding-left: 6mm; }
li { margin-bottom: 1.4mm; }
a { color: #1f4e79; text-decoration: none; }
code { font-family: "Cascadia Mono", "Consolas", monospace; font-size: 8.8pt; background: #f2f4f6;
       padding: 0.4mm 1.2mm; border-radius: 1mm; }
pre { background: #f6f8fa; border: 0.3mm solid #d8dee4; border-radius: 1.5mm; padding: 3mm 3.5mm;
      overflow-x: auto; break-inside: avoid; }
pre code { background: none; font-size: 8.4pt; line-height: 1.45; }
table { width: 100%; border-collapse: collapse; margin: 2mm 0 5mm; font-size: 8.6pt;
        font-family: "Segoe UI", Arial, sans-serif; break-inside: avoid; }
th { background: #eef2f6; text-align: left; font-weight: 600; }
th, td { border: 0.25mm solid #cfd6dd; padding: 1.6mm 2mm; vertical-align: top; }
tr:nth-child(even) td { background: #fafbfc; }
img { display: block; max-width: 100%; max-height: 108mm; margin: 4mm auto 2mm; }
hr { border: 0; border-top: 0.3mm solid #cfd6dd; margin: 6mm 0; }
blockquote { margin: 3mm 0 4mm 0; padding: 2mm 4mm; border-left: 1mm solid #1f4e79; color: #33414f;
             background: #f5f8fb; }

.cover { height: 245mm; display: flex; flex-direction: column; justify-content: space-between; }
.cover .kicker { font: 600 9pt "Segoe UI", sans-serif; letter-spacing: 0.18em; color: #1f4e79; }
.cover .meta { font: 9pt "Segoe UI", sans-serif; color: #4a5a68; line-height: 1.9; }
.cover .rule { height: 1.2mm; background: #1f4e79; width: 40mm; margin: 6mm 0; }
.abstract { background: #f4f7fa; border: 0.3mm solid #d7e0e8; border-radius: 2mm; padding: 5mm 6mm;
            font-size: 9.4pt; line-height: 1.6; }
.abstract h2 { font-size: 9pt; letter-spacing: 0.16em; color: #1f4e79; margin: 0 0 2.5mm;
               break-before: auto; padding: 0; }
.toc { break-before: page; }
.toc h2 { break-before: auto; padding: 0; }
.toc ol { list-style: none; padding: 0; margin: 6mm 0 0; counter-reset: toc; }
.toc li { display: flex; align-items: baseline; padding: 1.9mm 0; border-bottom: 0.2mm dotted #c9d2da;
          font: 10pt "Segoe UI", sans-serif; }
.toc .num { width: 11mm; color: #1f4e79; font-weight: 600; }
.toc .t { flex: 1; }
.toc .pg { color: #4a5a68; }
figure { margin: 4mm 0 3mm; break-inside: avoid; }
figcaption { font: 8.3pt "Segoe UI", sans-serif; color: #5a6a78; text-align: center; margin-top: 2mm; }
""".strip()

COVER_META = [
    'SUAY technical white paper · v1.1',
    'Published 22 October 2026',
    'Repository github.com/camponggogo/suay · MIT licence',
    'Measured on 50–100 simulated machines, one 8-vCPU host',
]

def headings_from(markdown_text):
    items = []
    for line in markdown_text.splitlines():
        match = re.match(r'^##\s+(\d+(?:\.\d+)?)\.?\s+(.*)$', line.strip())
        if match:
            items.append((match.group(1), match.group(2).strip()))
    return items


def split_document(markdown_text):
    """Cover title, the Abstract block, and the numbered body."""
    lines = markdown_text.splitlines()
    title = 'SUAY'
    body_start = 0
    for index, line in enumerate(lines):
        if line.startswith('# '):
            title = line[2:].strip()
            body_start = index + 1
            break

    abstract_lines = []
    for index, line in enumerate(lines):
        if line.strip().lower() == '## abstract':
            for follow in lines[index + 1:]:
                if follow.startswith('## '):
                    break
                abstract_lines.append(follow)
            break

    body_first = next((i for i, line in enumerate(lines)
                       if re.match(r'^##\s+\d', line)), len(lines))
    body = '\n'.join(lines[body_first:]).strip()
    return title, '\n'.join(abstract_lines).strip(), body


def to_html(text):
    return markdown.markdown(text, extensions=['tables', 'fenced_code', 'sane_lists', 'attr_list'])


def absolutise(html):
    def repl(match):
        src = match.group(1)
        if src.startswith('http'):
            return match.group(0)
        path = (ROOT / 'paper' / src).resolve()
        return f'src="{path.as_uri()}"'
    return re.sub(r'src="([^"]+)"', repl, html)


def build_html(title, abstract_md, body_html, toc_items, pages=None):
    toc_rows = []
    for index, (number, heading) in enumerate(toc_items):
        page = pages.get(number, '') if pages else ''
        toc_rows.append(f'<li><span class="num">{number}</span><span class="t">{heading}</span>'
                        f'<span class="pg">{page}</span></li>')
    abstract_html = to_html(abstract_md)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{title}</title><style>{CSS}</style></head><body>
<section class="cover">
  <div>
    <p class="kicker">SUAY / RESEARCH</p>
    <div class="rule"></div>
    <h1>{title}</h1>
  </div>
  <div class="abstract">{abstract_html}</div>
  <div class="meta">{'<br>'.join(COVER_META)}</div>
</section>
<section class="toc"><h2>Contents</h2><ol>{''.join(toc_rows)}</ol></section>
<section class="doc">{body_html}</section>
</body></html>"""


def render(html_path, pdf_path):
    command = [str(EDGE), '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
               '--virtual-time-budget=15000', f'--print-to-pdf={pdf_path}', html_path.as_uri()]
    result = subprocess.run(command, capture_output=True, text=True)
    if not Path(pdf_path).exists():
        print(result.stdout[-800:], result.stderr[-800:])
        sys.exit('edge did not produce a pdf')


def page_of_headings(pdf_path, toc_items):
    """Match the numbered heading at the start of a line, skipping cover and contents."""
    reader = PdfReader(pdf_path)
    found = {}
    for number, heading in toc_items:
        needle = re.escape(heading.split(':')[0][:24])
        pattern = re.compile(rf'(?m)^\s*{re.escape(number)}\.?\s+{needle}', re.IGNORECASE)
        for index, page in enumerate(reader.pages):
            if index < 2:
                continue
            text = page.extract_text() or ''
            if pattern.search(text):
                found[number] = index + 1
                break
    return found, len(reader.pages)


def stamp(pdf_path, out_path):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    total = len(reader.pages)
    for index, page in enumerate(reader.pages):
        if index > 0:
            buffer = io.BytesIO()
            width, height = float(page.mediabox.width), float(page.mediabox.height)
            layer = canvas.Canvas(buffer, pagesize=(width, height))
            layer.setStrokeColorRGB(0.80, 0.84, 0.88)
            layer.setLineWidth(0.4)
            layer.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
            layer.setFont('Helvetica', 7.4)
            layer.setFillColorRGB(0.35, 0.42, 0.48)
            layer.drawString(18 * mm, 10.4 * mm, 'SUAY white paper · v1.1 · 22 October 2026')
            layer.drawRightString(width - 18 * mm, 10.4 * mm, f'{index + 1} / {total}')
            layer.save()
            buffer.seek(0)
            page.merge_page(PdfReader(buffer).pages[0])
        writer.add_page(page)
    writer.add_metadata({
        '/Title': 'Serving LLMs on an Office Fleet: Control-Plane Limits, Prefix Reuse and Expert Routing at 50–500 Machines',
        '/Author': 'SUAY contributors',
        '/Subject': 'Distributed inference on office hardware: measurements, negative results and capacity models',
        '/Keywords': 'distributed inference, control plane, prefix caching, expert routing, capacity planning',
        '/Creator': 'SUAY paper build',
    })
    with open(out_path, 'wb') as handle:
        writer.write(handle)


def main():
    BUILD.mkdir(exist_ok=True)
    text = SOURCE.read_text(encoding='utf-8')
    title, abstract_md, body = split_document(text)
    toc_items = headings_from(body)
    body_html = absolutise(to_html(body))

    first = BUILD / 'pass1.html'
    first.write_text(build_html(title, abstract_md, body_html, toc_items), encoding='utf-8')
    first_pdf = BUILD / 'pass1.pdf'
    render(first, first_pdf)
    pages, total = page_of_headings(first_pdf, toc_items)
    print('pass 1:', total, 'pages,', len(pages), 'of', len(toc_items), 'headings located')

    second = BUILD / 'pass2.html'
    second.write_text(build_html(title, abstract_md, body_html, toc_items, pages), encoding='utf-8')
    second_pdf = BUILD / 'pass2.pdf'
    render(second, second_pdf)

    stamp(second_pdf, OUT)
    final = PdfReader(OUT)
    print('final:', len(final.pages), 'pages,', round(OUT.stat().st_size / 1024 / 1024, 2), 'MB')


if __name__ == '__main__':
    main()
