"""Build the PASADHI isometric scene as static SVG (no runtime geometry) and write the page."""
from __future__ import annotations

import math
from pathlib import Path

COS, SIN = math.cos(math.pi / 6), math.sin(math.pi / 6)
OX, OY = 450, 330


def iso(x, y, z=0.0):
    return OX + (x - y) * COS, OY + (x + y) * SIN - z


def pt(x, y, z=0.0):
    a, b = iso(x, y, z)
    return f'{a:.1f},{b:.1f}'


def poly(points, fill, extra=''):
    return f'<polygon points="{points}" fill="{fill}"{extra}/>'


def box(x, y, z, w, d, h, tones):
    top = ' '.join([pt(x, y, z + h), pt(x + w, y, z + h), pt(x + w, y + d, z + h), pt(x, y + d, z + h)])
    left = ' '.join([pt(x, y + d, z + h), pt(x + w, y + d, z + h), pt(x + w, y + d, z), pt(x, y + d, z)])
    right = ' '.join([pt(x + w, y, z + h), pt(x + w, y + d, z + h), pt(x + w, y + d, z), pt(x + w, y, z)])
    return poly(left, tones[0]) + poly(right, tones[1]) + poly(top, tones[2])


T = {
    'baseL': '#ded6c4', 'baseR': '#ece6d6', 'baseTop': '#f6f1e6',
    'plinthL': '#b3d2c1', 'plinthR': '#c4dccd', 'plinth': '#d2e7dc',
    'caseL': '#c6dfd4', 'caseR': '#dcece4', 'caseTop': '#ffffff',
    'busL': '#0d6048', 'busR': '#12795b', 'bus': '#169b74',
    'gpuL': '#d96a3f', 'gpuR': '#ef7c4e', 'gpu': '#ff9a6d',
}

S: list[str] = []


def add(part: str) -> None:
    S.append(part)


def machine_laptop(x, y):
    out = [box(x, y, 10, 96, 70, 8, [T['plinthL'], T['plinthR'], T['plinth']])]
    out.append(box(x + 14, y + 10, 18, 68, 5, 40, [T['caseL'], T['caseR'], T['caseTop']]))
    out.append(poly(' '.join([pt(x + 18, y + 12, 24), pt(x + 78, y + 12, 24),
                              pt(x + 78, y + 12, 52), pt(x + 18, y + 12, 52)]), '#123c30'))
    out.append(poly(' '.join([pt(x + 22, y + 13, 27), pt(x + 52, y + 13, 27),
                              pt(x + 52, y + 13, 33), pt(x + 22, y + 13, 33)]), '#2f8a68'))
    out.append(box(x + 12, y + 22, 18, 72, 34, 4, [T['caseL'], T['caseR'], '#ffffff']))
    for i in range(6):
        for j in range(4):
            kx, ky = iso(x + 18 + i * 11, y + 26 + j * 7, 22)
            out.append(f'<rect x="{kx - 3.4:.1f}" y="{ky - 1.6:.1f}" width="6.8" height="3.2" rx="1" fill="#ccdad3"/>')
    return ''.join(out)


def machine_server(x, y):
    out = [box(x, y, 10, 96, 70, 8, [T['plinthL'], T['plinthR'], T['plinth']])]
    out.append(box(x + 12, y + 10, 18, 72, 50, 58, [T['caseL'], T['caseR'], T['caseTop']]))
    for i in range(4):
        a = iso(x + 16, y + 12, 26 + i * 13)
        b = iso(x + 80, y + 12, 26 + i * 13)
        out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#c7d8d0" stroke-width="2.4"/>')
        c = iso(x + 18, y + 12, 31 + i * 13)
        tone = '#ffd166' if i == 1 else '#7fbfa9'
        out.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="2.6" fill="{tone}"/>')
    return ''.join(out)


def machine_desktop(x, y):
    out = [box(x, y, 10, 96, 70, 8, [T['plinthL'], T['plinthR'], T['plinth']])]
    out.append(box(x + 12, y + 12, 18, 50, 46, 44, [T['caseL'], T['caseR'], T['caseTop']]))
    c = iso(x + 37, y + 14, 44)
    out.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="5" fill="#a9c9bd"/>'
               f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="2" fill="#e9f3ee"/>')
    out.append(box(x + 66, y + 18, 18, 22, 30, 5, [T['caseL'], T['caseR'], '#ffffff']))
    return ''.join(out)


def machine_gpu(x, y):
    out = [box(x, y, 10, 96, 70, 8, [T['plinthL'], T['plinthR'], T['plinth']])]
    out.append(box(x + 10, y + 18, 18, 78, 10, 10, [T['gpuL'], T['gpuR'], T['gpu']]))
    out.append(box(x + 10, y + 18, 28, 78, 16, 34, [T['gpuL'], T['gpuR'], '#ffb189']))
    c = iso(x + 46, y + 18, 44)
    out.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="8" fill="#7a3418"/>'
               f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="3.4" fill="#ffd166"/>')
    return ''.join(out)


NODES = [
    {'name': 'laptop', 'x': -250, 'y': -80, 'draw': machine_laptop, 'back': True},
    {'name': 'server', 'x': 135, 'y': -195, 'draw': machine_server, 'back': True},
    {'name': 'GPU', 'x': 160, 'y': 55, 'draw': machine_gpu, 'back': False},
    {'name': 'desktop', 'x': -215, 'y': 150, 'draw': machine_desktop, 'back': False},
]


def build() -> str:
    add(f'<ellipse cx="{OX}" cy="{OY + 150}" rx="390" ry="94" fill="#14302a" opacity=".07"/>')
    add(box(-300, -235, 0, 560, 440, 10, [T['baseL'], T['baseR'], T['baseTop']]))
    for i in range(-280, 241, 24):
        a = iso(i, -192, 10)
        b = iso(i, -182, 10)
        add(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#bcb3a0" stroke-width="1.1"/>')
    for x, y in ((-288, -221), (248, -221), (-288, 193), (248, 193)):
        c = iso(x, y, 10)
        add(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="3.4" fill="#bcb3a0"/>')

    for node in [n for n in NODES if n['back']]:
        add(node['draw'](node['x'], node['y']))

    cables = []
    for index, node in enumerate(NODES):
        a = iso(node['x'] + 48, node['y'] + 30, 30)
        b = iso(0, 0, 44)
        mx, my = (a[0] + b[0]) / 2, min(a[1], b[1]) - 26
        d = (f'M {a[0]:.1f} {a[1]:.1f} Q {mx:.1f} {my:.1f} {b[0]:.1f} {b[1]:.1f}')
        cables.append(d)
        add(f'<path d="{d}" fill="none" stroke="#2f4a41" stroke-width="5.5" stroke-linecap="round" opacity=".92"/>')
        add(f'<path d="{d}" fill="none" stroke="#9ad3bd" stroke-width="1.5" stroke-linecap="round" opacity=".7"/>')

    add(box(-58, -58, 10, 116, 116, 12, [T['busL'], T['busR'], T['bus']]))
    add(box(-42, -42, 22, 84, 84, 64, [T['busL'], T['busR'], T['bus']]))
    add(box(-50, -50, 86, 100, 100, 8, ['#0a4e39', '#0f6a4e', '#1cb184']))
    for i in (-24, 0, 24):
        for x, y in ((i, 42), (42, i)):
            c = iso(x, y, 52)
            add(f'<rect x="{c[0] - 3.5:.1f}" y="{c[1] - 3.5:.1f}" width="7" height="7" rx="1.6" fill="#07301f"/>')

    add(box(-6, -6, 94, 12, 12, 52, ['#0a4e39', '#0f6a4e', '#1cb184']))
    cx, cy = iso(0, 0, 196)
    cx, cy = round(cx), round(cy)
    add(f'<circle cx="{cx}" cy="{cy}" r="50" fill="#ffffff" stroke="#cfdcd5" stroke-width="2"/>')
    add(f'<circle cx="{cx}" cy="{cy}" r="43" fill="none" stroke="#e6efe9" stroke-width="1"/>')
    for i in range(13):
        angle = math.radians(-210 + i * 20)
        x1, y1 = cx + math.cos(angle) * 38, cy + math.sin(angle) * 38
        x2, y2 = cx + math.cos(angle) * 46, cy + math.sin(angle) * 46
        wide = 2 if i % 6 == 0 else 1
        tone = '#14302a' if i % 6 == 0 else '#9fb8ac'
        add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{tone}" stroke-width="{wide}"/>')
    add(f'<text x="{cx}" y="{cy + 32}" text-anchor="middle" font-family="Nunito,sans-serif" font-size="9.5" fill="#5c7168">GFLOP/s</text>')
    add(f'<g id="needle" transform="rotate(-48 {cx} {cy})"><line x1="{cx}" y1="{cy}" x2="{cx + 36}" y2="{cy}" stroke="#e0563f" stroke-width="2.8" stroke-linecap="round"/></g>')
    add(f'<circle cx="{cx}" cy="{cy}" r="4.4" fill="#14302a"/>')

    c = iso(-10, 215, 16)
    add(f'<rect x="{c[0] - 44:.1f}" y="{c[1] - 17:.1f}" width="88" height="34" rx="9" fill="#12241f" stroke="#0b3f30"/>')
    for i, digit in enumerate('0711'):
        x = c[0] - 35 + i * 18
        add(f'<rect x="{x:.1f}" y="{c[1] - 11:.1f}" width="15" height="22" rx="3" fill="#0a1a15" stroke="#0b3f30"/>')
        add(f'<text id="d{i}" x="{x + 7.5:.1f}" y="{c[1] + 5:.1f}" text-anchor="middle" '
            f'font-family="Nunito,sans-serif" font-size="12" fill="#d1ff68">{digit}</text>')

    for node in [n for n in NODES if not n['back']]:
        add(node['draw'](node['x'], node['y']))

    for node in NODES:
        p = iso(node['x'] + 48, node['y'] + 72, 0)
        add(f'<text x="{p[0]:.1f}" y="{p[1] + 16:.1f}" text-anchor="middle" font-family="Nunito,sans-serif" '
            f'font-size="10.5" font-weight="700" fill="#5c7168">{node["name"]}</text>')

    for index, d in enumerate(cables):
        add(f'<path id="c{index}" d="{d}" fill="none" stroke="none"/>')
        dur = 2.8 + index * 0.4
        add(f'<circle r="5" fill="#ffd166" stroke="#a87700" stroke-width="1.2">'
            f'<animateMotion dur="{dur:.2f}s" repeatCount="indefinite"><mpath href="#c{index}"/></animateMotion></circle>')
        add(f'<circle r="3.6" fill="#8fd6bb" stroke="#3c7d64" stroke-width="1.2">'
            f'<animateMotion dur="{dur:.2f}s" begin="{1.4 + index * 0.25:.2f}s" repeatCount="indefinite" '
            f'keyPoints="1;0" keyTimes="0;1"><mpath href="#c{index}"/></animateMotion></circle>')

    return '\n'.join(S)


SCENE = build()
PAGE = Path(__file__).resolve().parents[1] / 'pasadhi' / 'web' / 'anatomy' / 'pasadhi-pool.html'


def main() -> None:
    template = PAGE.read_text(encoding='utf-8')
    start = template.index('<svg id="scene"')
    end = template.index('</svg>', start) + len('</svg>')
    replacement = (
        '<svg id="scene" viewBox="0 0 900 640" role="img" '
        'aria-label="Isometric office pool: four machines on a base, cables carrying work packets into a central bus, '
        'a dial gauge above it">\n' + SCENE + '\n</svg>'
    )
    page = template[:start] + replacement + template[end:]
    page = page.replace("document.getElementById('scene').innerHTML = S.join('\\n');", '')
    PAGE.write_text(page, encoding='utf-8')
    print('scene polygons:', SCENE.count('<polygon'), 'path:', SCENE.count('<path'))


if __name__ == '__main__':
    main()
