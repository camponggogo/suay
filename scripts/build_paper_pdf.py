"""Build a PASADHI paper (markdown + figures) into an A4 PDF with cover, figures and page numbers.

    python scripts/build_paper_pdf.py --md pasadhi/paper/SOLUTION.md \
        --out landing-pasadhi/download/PASADHI-solution.pdf --kind solution
"""
from __future__ import annotations

import argparse
import io
import re
import subprocess
from pathlib import Path
from statistics import median

import markdown
from PIL import Image, ImageChops, ImageOps
from pypdf import PdfReader, PdfWriter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'pasadhi' / 'paper' / '_build'
EDGE = Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')

CSS = """
@page { size: A4; margin: 18mm 17mm 20mm 17mm; }
body { font-family: "Charter", Georgia, "Times New Roman", serif; font-size: 10.2pt; line-height: 1.55; color: #14302a; }
h1, h2, h3 { font-family: "Segoe UI", Arial, sans-serif; color: #0f4f3c; }
h1 { font-size: 23pt; line-height: 1.14; margin: 0 0 5mm; letter-spacing: -0.01em; }
h2 { font-size: 13.5pt; margin: 7mm 0 2.6mm; break-after: avoid; }
h3 { font-size: 11pt; margin: 5mm 0 1.8mm; break-after: avoid; }
p { margin: 0 0 2.8mm; text-align: justify; }
img { display: block; width: 100%; height: auto; margin: 2mm 0 1mm; border: 0.25mm solid #e2e9e5; border-radius: 1.2mm; }
p > img + em, p em { color: #4a675c; }
table { width: 100%; border-collapse: collapse; font-size: 8.6pt; margin: 2.5mm 0 4mm; break-inside: avoid; }
th { background: #e9f5ef; text-align: left; }
th, td { border: 0.25mm solid #cfded6; padding: 1.5mm 1.9mm; vertical-align: top; }
code { font-family: Consolas, monospace; font-size: 8.8pt; background: #f2f6f4; padding: 0.2mm 0.9mm; }
pre { background: #f5f9f7; border: 0.3mm solid #d9e7e0; border-radius: 1.4mm; padding: 3.4mm; break-inside: avoid; }
pre code { font-size: 8.4pt; line-height: 1.42; background: none; }
ul, ol { margin: 0 0 2.8mm 0; padding-left: 6mm; }
li { margin-bottom: 1.2mm; }
.cover { height: 246mm; display: flex; flex-direction: column; justify-content: space-between; break-after: page; }
.cover .kicker { font: 700 9pt "Segoe UI", sans-serif; letter-spacing: 0.18em; color: #159a72; }
.cover .rule { width: 44mm; height: 1.3mm; background: #159a72; margin: 5mm 0; }
.cover .meta { font: 9pt "Segoe UI", sans-serif; color: #4a675c; line-height: 1.85; }
.cover .rule-bottom { border-top: 0.3mm solid #d7e5de; padding-top: 4mm; }
"""

COVERS = {
    'solution': ('PASADHI · SOLUTION PAPER', 'Solution paper'),
    'full': ('PASADHI · FULL PAPER', 'Full paper with the complete evidence base'),
}


def border_stats(path: Path) -> tuple[float, tuple[int, int, int]]:
    """Median border luminance and colour, used to detect dark-background figures."""
    im = Image.open(path).convert('RGB')
    im.thumbnail((160, 160))
    w, h = im.size
    strips = (list(im.crop((0, 0, w, 2)).getdata()) + list(im.crop((0, h - 2, w, h)).getdata())
              + list(im.crop((0, 0, 2, h)).getdata()) + list(im.crop((w - 2, 0, w, h)).getdata()))
    lum = sorted(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in strips)
    rgb = tuple(int(median(pixel[channel] for pixel in strips)) for channel in range(3))
    return lum[len(lum) // 2], rgb


def whiten(path: Path, out: Path) -> None:
    """Put a dark-background chart on white without changing its coloured lines.

    Background-coloured pixels become white, grey pixels are inverted (white text becomes
    black, the grey grid becomes light grey) and saturated pixels keep their colour.
    """
    im = Image.open(path).convert('RGB')
    bg_colour = border_stats(path)[1]
    background = Image.new('RGB', im.size, bg_colour)
    diff = ImageChops.difference(im, background).convert('L')
    bg_mask = diff.point(lambda value: 255 if value <= 40 else 0)
    saturation = im.convert('HSV').split()[1]
    coloured = saturation.point(lambda value: 255 if value >= 40 else 0)
    inverted = ImageOps.invert(im)
    kept = Image.composite(im, inverted, coloured)
    result = Image.composite(Image.new('RGB', im.size, (255, 255, 255)), kept, bg_mask)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.save(out)


def inline_images(html: str, build: Path) -> str:
    """Rewrite relative image sources to absolute file URIs; whiten dark-background figures."""
    whitened: list[str] = []

    def repl(match: re.Match[str]) -> str:
        src = match.group(1)
        if src.startswith(('http://', 'https://', 'file:')):
            return match.group(0)
        path = (ROOT / src).resolve()
        if not path.exists():
            raise SystemExit(f'missing figure: {src}')
        use = path
        if path.suffix.lower() == '.png':
            lum, _colour = border_stats(path)
            if lum < 120:
                candidate = build / 'white' / src.replace('/', '__')
                if not candidate.exists() or candidate.stat().st_mtime < path.stat().st_mtime:
                    whiten(path, candidate)
                use = candidate
                whitened.append(src)
        return f'src="{use.as_uri()}"'

    html = re.sub(r'src="([^"]+)"', repl, html)
    if whitened:
        print('whitened:', ', '.join(whitened))
    return html


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--md', default='pasadhi/paper/SOLUTION.md')
    parser.add_argument('--out', default='landing-pasadhi/download/PASADHI-solution.pdf')
    parser.add_argument('--kind', default='solution', choices=sorted(COVERS))
    parser.add_argument('--version', default='v1.1')
    parser.add_argument('--date', default='23 October 2026')
    args = parser.parse_args()

    source = ROOT / args.md
    output = ROOT / args.out
    BUILD.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)

    lines = source.read_text(encoding='utf-8').splitlines()
    title = next(line[2:].strip() for line in lines if line.startswith('# '))
    body_md = '\n'.join(lines[1:])
    body_html = markdown.markdown(body_md, extensions=['tables', 'fenced_code', 'sane_lists'])
    body_html = inline_images(body_html, BUILD)

    kicker, blurb = COVERS[args.kind]
    figures = body_html.count('<img')
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<style>{CSS}</style></head><body>
<section class="cover">
  <div><p class="kicker">{kicker}</p><div class="rule"></div><h1>{title}</h1>
       <p style="font:10pt 'Segoe UI',sans-serif;color:#4a675c;margin-top:4mm">{blurb} · {figures} figures</p></div>
  <div class="meta"><div class="rule-bottom">
    PASADHI contributors · {args.version}<br>{args.date} · MIT for the open core<br>
    github.com/camponggogo/pasadhi · pasadhi.tech</div></div>
</section>
{body_html}
</body></html>"""
    html_path = BUILD / f'{args.kind}.html'
    html_path.write_text(html, encoding='utf-8')

    raw_pdf = BUILD / f'{args.kind}-raw.pdf'
    if raw_pdf.exists():
        raw_pdf.unlink()
    command = [str(EDGE), '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
               '--virtual-time-budget=20000', '--allow-file-access-from-files',
               f'--print-to-pdf={raw_pdf}', html_path.as_uri()]
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
            layer.line(17 * mm, 13.4 * mm, width - 17 * mm, 13.4 * mm)
            layer.setFont('Helvetica', 7.1)
            layer.setFillColorRGB(0.33, 0.42, 0.38)
            layer.drawString(17 * mm, 9.8 * mm, f'PASADHI {COVERS[args.kind][1].lower()} · {args.version} · {args.date}')
            layer.drawRightString(width - 17 * mm, 9.8 * mm, f'{index + 1} / {total}')
            layer.save()
            buffer.seek(0)
            page.merge_page(PdfReader(buffer).pages[0])
        writer.add_page(page)
    writer.add_metadata({'/Title': title, '/Author': 'PASADHI contributors',
                         '/Subject': COVERS[args.kind][1],
                         '/Keywords': 'distributed inference, matrix compute, office hardware, pricing'})
    with open(output, 'wb') as handle:
        writer.write(handle)
    print('pages', total, 'figures', figures, 'size', round(output.stat().st_size / 1024, 1), 'KB', output)


if __name__ == '__main__':
    main()
