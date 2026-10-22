"""Build the PASADHI mesh scene: many office devices and GPU nodes wired into one web.

Deterministic SVG generated here (no runtime geometry), with SMIL packets on a subset of links.

    python scripts/build_mesh_scene.py
"""
from __future__ import annotations

import math
from pathlib import Path

COS, SIN = math.cos(math.pi / 6), math.sin(math.pi / 6)
OX, OY = 560, 430


def iso(x, y, z=0.0):
    return OX + (x - y) * COS, OY + (x + y) * SIN - z


def pt(x, y, z=0.0):
    a, b = iso(x, y, z)
    return f'{a:.1f},{b:.1f}'


def poly(points, fill, extra=''):
    return f'<polygon points="{points}" fill="{fill}"{extra}/>'


def box(x, y, z, w, d, h, tones, stroke=''):
    top = ' '.join([pt(x, y, z + h), pt(x + w, y, z + h), pt(x + w, y + d, z + h), pt(x, y + d, z + h)])
    left = ' '.join([pt(x, y + d, z + h), pt(x + w, y + d, z + h), pt(x + w, y + d, z), pt(x, y + d, z)])
    right = ' '.join([pt(x + w, y, z + h), pt(x + w, y + d, z + h), pt(x + w, y + d, z), pt(x + w, y, z)])
    extra = f' stroke="{stroke}" stroke-width="0.8"' if stroke else ''
    return poly(left, tones[0], extra) + poly(right, tones[1], extra) + poly(top, tones[2], extra)


T = {
    'baseL': '#ded6c4', 'baseR': '#ece6d6', 'baseTop': '#f7f2e7',
    'plinthL': '#b0d0bf', 'plinthR': '#c2dacb', 'plinth': '#d0e5d9',
    'caseL': '#c2dcd1', 'caseR': '#d9eae2', 'caseTop': '#ffffff',
    'busL': '#0b5a43', 'busR': '#0f7255', 'bus': '#159a72',
    'gpuL': '#d4693f', 'gpuR': '#ee7a4c', 'gpu': '#ff9a6d',
    'phoneL': '#c9d8d1', 'phoneR': '#e4eeea', 'phoneTop': '#ffffff',
}

S: list[str] = []


def add(part: str) -> None:
    S.append(part)


def machine_base(x, y, w=92, d=66):
    return box(x, y, 10, w, d, 8, [T['plinthL'], T['plinthR'], T['plinth']], '#a9c7b8')


def laptop(x, y):
    out = [machine_base(x, y)]
    out.append(box(x + 14, y + 8, 18, 62, 5, 36, [T['caseL'], T['caseR'], T['caseTop']], '#b9d4c8'))
    out.append(poly(' '.join([pt(x + 18, y + 10, 24), pt(x + 72, y + 10, 24),
                              pt(x + 72, y + 10, 48), pt(x + 18, y + 10, 48)]), '#123c30'))
    out.append(poly(' '.join([pt(x + 21, y + 11, 27), pt(x + 48, y + 11, 27),
                              pt(x + 48, y + 11, 32), pt(x + 21, y + 11, 32)]), '#3d9b77'))
    out.append(box(x + 12, y + 18, 18, 68, 32, 4, [T['caseL'], T['caseR'], '#ffffff'], '#c7dbd2'))
    for i in range(5):
        for j in range(3):
            kx, ky = iso(x + 18 + i * 12, y + 22 + j * 8, 22)
            out.append(f'<rect x="{kx - 3:.1f}" y="{ky - 1.4:.1f}" width="6" height="2.8" rx="1" fill="#c8dad2"/>')
    return ''.join(out)


def desktop(x, y):
    out = [machine_base(x, y)]
    out.append(box(x + 12, y + 11, 18, 48, 44, 42, [T['caseL'], T['caseR'], T['caseTop']], '#b9d4c8'))
    c = iso(x + 36, y + 13, 42)
    out.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="5" fill="#9dbeb1"/>'
               f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="2" fill="#eaf4ef"/>')
    out.append(box(x + 64, y + 16, 18, 20, 28, 5, [T['caseL'], T['caseR'], '#ffffff'], '#c7dbd2'))
    return ''.join(out)


def server(x, y):
    out = [machine_base(x, y)]
    out.append(box(x + 12, y + 8, 18, 68, 48, 56, [T['caseL'], T['caseR'], T['caseTop']], '#b9d4c8'))
    for i in range(4):
        a = iso(x + 16, y + 10, 26 + i * 12)
        b = iso(x + 76, y + 10, 26 + i * 12)
        out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#b9cdc6" stroke-width="2.2"/>')
        c = iso(x + 18, y + 10, 31 + i * 12)
        out.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="2.4" fill="{"#ffd166" if i == 1 else "#86bfa9"}"/>')
    return ''.join(out)


def gpu_node(x, y, cards=2):
    out = [machine_base(x, y, 92, 70)]
    for index in range(cards):
        z = 18 + index * 16
        out.append(box(x + 10, y + 16, z, 72, 8, 8, [T['gpuL'], T['gpuR'], T['gpu']], '#b8542c'))
        out.append(box(x + 10, y + 16, z + 10, 72, 12, 14, [T['gpuL'], T['gpuR'], '#ffb189'], '#b8542c'))
        c = iso(x + 46, y + 16, z + 20)
        out.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="3.6" fill="#7a3418"/>')
    return ''.join(out)


def phone(x, y):
    out = [machine_base(x, y, 60, 46)]
    out.append(box(x + 12, y + 8, 18, 34, 4, 54, [T['phoneL'], T['phoneR'], T['phoneTop']], '#b9d4c8'))
    out.append(poly(' '.join([pt(x + 15, y + 10, 26), pt(x + 43, y + 10, 26),
                              pt(x + 43, y + 10, 64), pt(x + 15, y + 10, 64)]), '#123c30'))
    out.append(poly(' '.join([pt(x + 18, y + 11, 30), pt(x + 40, y + 11, 30),
                              pt(x + 40, y + 11, 44), pt(x + 18, y + 11, 44)]), '#3d9b77'))
    return ''.join(out)


def pool(x, y):
    out = [box(x - 44, y - 44, 10, 88, 88, 10, [T['busL'], T['busR'], '#1aa87c'], '#0a4a37')]
    out.append(box(x - 30, y - 30, 20, 60, 60, 46, [T['busL'], T['busR'], T['bus']], '#0a4a37'))
    out.append(box(x - 36, y - 36, 66, 72, 72, 6, ['#084c38', '#0c6349', '#1cb184'], '#073b2b'))
    for i in (-18, 0, 18):
        for px, py in ((x + i, y + 30), (x + 30, y + i)):
            c = iso(px, py, 40)
            out.append(f'<rect x="{c[0] - 3:.1f}" y="{c[1] - 3:.1f}" width="6" height="6" rx="1.4" fill="#062f22"/>')
    out.append(box(x - 5, y - 5, 72, 10, 10, 34, ['#084c38', '#0c6349', '#1cb184'], '#073b2b'))
    return ''.join(out)


# ring of devices around the pool: radius in world units
RING = [
    (-330, -170, 'desktop'), (-140, -300, 'laptop'), (90, -330, 'server'),
    (300, -230, 'gpu2'), (370, -30, 'desktop'), (330, 170, 'gpu3'),
    (150, 320, 'laptop'), (-80, 350, 'server'), (-290, 280, 'desktop'),
    (-400, 90, 'phone'), (-380, -80, 'gpu2'), (200, 380, 'phone'),
]
DRAW = {
    'desktop': desktop, 'laptop': laptop, 'server': server,
    'gpu2': lambda x, y: gpu_node(x, y, 2), 'gpu3': lambda x, y: gpu_node(x, y, 3),
    'phone': phone,
}


def build() -> str:
    # floor
    add(f'<ellipse cx="{OX}" cy="{OY + 250}" rx="640" ry="170" fill="#14302a" opacity=".06"/>')
    add(box(-470, -430, 0, 940, 860, 10, [T['baseL'], T['baseR'], T['baseTop']], '#d3cab6'))
    for i in range(-450, 451, 40):
        a = iso(i, -432, 10)
        b = iso(i, -420, 10)
        add(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#c6bda9" stroke-width="1"/>')
    for x, y in ((-455, -415), (445, -415), (-455, 415), (445, 415)):
        c = iso(x, y, 10)
        add(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="4" fill="#c6bda9"/>')

    # links: ring neighbours + spokes to the pool + a few cross-links (the web)
    links = []
    for index, (x, y, kind) in enumerate(RING):
        links.append(((x + 34, y + 26), (0, 0), 'spoke'))
        nx, ny, _ = RING[(index + 1) % len(RING)]
        links.append(((x + 34, y + 26), (nx + 34, ny + 26), 'ring'))
    for a, b in ((0, 4), (2, 6), (3, 9), (5, 8), (1, 11), (7, 10)):
        x1, y1, _ = RING[a]
        x2, y2, _ = RING[b]
        links.append(((x1 + 34, y1 + 26), (x2 + 34, y2 + 26), 'cross'))

    drawn = 0
    for index, ((x1, y1), (x2, y2), kind) in enumerate(links):
        a = iso(x1, y1, 26)
        b = iso(x2, y2, 26)
        lift = 34 if kind == 'spoke' else 22
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - lift
        d = f'M {a[0]:.1f} {a[1]:.1f} Q {mx:.1f} {my:.1f} {b[0]:.1f} {b[1]:.1f}'
        width = 3.0 if kind != 'ring' else 2.2
        add(f'<path d="{d}" fill="none" stroke="#31584c" stroke-width="{width}" stroke-linecap="round" opacity=".55"/>')
        add(f'<path d="{d}" fill="none" stroke="#8fd0b8" stroke-width="1" stroke-linecap="round" opacity=".45"/>')
        if index % 3 == 0:
            drawn += 1
            add(f'<path id="m{index}" d="{d}" fill="none" stroke="none"/>')
            dur = 3.0 + (index % 5) * 0.38
            add(f'<circle r="4" fill="#ffd166" stroke="#a87700" stroke-width="1">'
                f'<animateMotion dur="{dur:.2f}s" begin="{(index % 7) * 0.22:.2f}s" repeatCount="indefinite">'
                f'<mpath href="#m{index}"/></animateMotion></circle>')
            add(f'<circle r="3" fill="#8fd6bb" stroke="#3c7d64" stroke-width="1">'
                f'<animateMotion dur="{dur:.2f}s" begin="{dur / 2 + (index % 7) * 0.22:.2f}s" repeatCount="indefinite" '
                f'keyPoints="1;0" keyTimes="0;1"><mpath href="#m{index}"/></animateMotion></circle>')

    # pool first (it sits at the centre, behind the front nodes)
    add(pool(0, 0))

    # nodes in depth order, so nearer machines cover the links correctly
    for x, y, kind in sorted(RING, key=lambda item: item[0] + item[1]):
        add(DRAW[kind](x, y))

    # labels
    for x, y, kind in RING:
        p = iso(x + 34, y + 78, 0)
        label = 'GPU ×3' if kind == 'gpu3' else 'GPU ×2' if kind == 'gpu2' else kind
        add(f'<text x="{p[0]:.1f}" y="{p[1] + 12:.1f}" text-anchor="middle" '
            f'font-family="Nunito, sans-serif" font-size="9.5" font-weight="700" fill="#5c7168">{label}</text>')

    # dial above the pool
    cx, cy = iso(0, 0, 156)
    cx, cy = round(cx), round(cy)
    add(f'<circle cx="{cx}" cy="{cy}" r="46" fill="#ffffff" stroke="#cfdcd5" stroke-width="2"/>')
    add(f'<circle cx="{cx}" cy="{cy}" r="39" fill="none" stroke="#e6efe9" stroke-width="1"/>')
    for i in range(13):
        angle = math.radians(-210 + i * 20)
        x1, y1 = cx + math.cos(angle) * 33, cy + math.sin(angle) * 33
        x2, y2 = cx + math.cos(angle) * 40, cy + math.sin(angle) * 40
        add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{"#14302a" if i % 6 == 0 else "#9fb8ac"}" stroke-width="{2 if i % 6 == 0 else 1}"/>')
    add(f'<g id="needle" transform="rotate(-48 {cx} {cy})">'
        f'<line x1="{cx}" y1="{cy}" x2="{cx + 30}" y2="{cy}" stroke="#e0563f" stroke-width="2.6" stroke-linecap="round"/></g>')
    add(f'<circle cx="{cx}" cy="{cy}" r="4" fill="#14302a"/>')
    add(f'<text x="{cx}" y="{cy + 26}" text-anchor="middle" font-family="Nunito, sans-serif" font-size="8.5" fill="#5c7168">GFLOP/s</text>')

    return '\n'.join(S)


PAGE = Path(__file__).resolve().parents[1] / 'pasadhi' / 'web' / 'anatomy' / 'pasadhi-mesh.html'


def main() -> None:
    scene = build()
    template = PAGE.read_text(encoding='utf-8')
    start = template.index('<svg id="scene"')
    end = template.index('</svg>', start) + len('</svg>')
    replacement = ('<svg id="scene" viewBox="0 0 1140 760" role="img" '
                   'aria-label="Isometric mesh: twelve office devices and GPU nodes wired to one pool">\n'
                   + scene + '\n</svg>')
    PAGE.write_text(template[:start] + replacement + template[end:], encoding='utf-8')
    print('mesh polygons:', scene.count('<polygon'), 'paths:', scene.count('<path'))


if __name__ == '__main__':
    main()
