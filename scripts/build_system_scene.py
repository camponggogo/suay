"""PASADHI full system as one isometric floor: app -> gateway -> pool -> storage, devices feeding the pool."""
from __future__ import annotations

from pathlib import Path

COS, SIN = 0.8660254, 0.5
OX, OY = 700, 520
RED = '#d93f2b'

S: list[str] = []


def iso(x, y, z=0.0):
    return OX + (x - y) * COS, OY + (x + y) * SIN - z


def pt(x, y, z=0.0):
    a, b = iso(x, y, z)
    return f'{a:.1f},{b:.1f}'


def box(x, y, z, w, d, h, tones, stroke='#b9d0c4'):
    top = ' '.join([pt(x, y, z + h), pt(x + w, y, z + h), pt(x + w, y + d, z + h), pt(x, y + d, z + h)])
    left = ' '.join([pt(x, y + d, z + h), pt(x + w, y + d, z + h), pt(x + w, y + d, z), pt(x, y + d, z)])
    right = ' '.join([pt(x + w, y, z + h), pt(x + w, y + d, z + h), pt(x + w, y + d, z), pt(x + w, y, z)])
    return (f'<polygon points="{left}" fill="{tones[0]}" stroke="{stroke}" stroke-width="0.8"/>'
            f'<polygon points="{right}" fill="{tones[1]}" stroke="{stroke}" stroke-width="0.8"/>'
            f'<polygon points="{top}" fill="{tones[2]}" stroke="{stroke}" stroke-width="0.8"/>')


def badge(x, y, z, text, up=True):
    a = iso(x, y, z)
    w = 20 + len(text) * 7.4
    return (f'<g><line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{a[0]:.1f}" y2="{a[1] - 16:.1f}" '
            f'stroke="{RED}" stroke-width="1.3" stroke-dasharray="3 2"/>'
            f'<rect x="{a[0] - w / 2:.1f}" y="{a[1] - 34:.1f}" width="{w:.1f}" height="19" rx="9" '
            f'fill="#fff" stroke="{RED}" stroke-width="1.4"/>'
            f'<text x="{a[0]:.1f}" y="{a[1] - 20:.1f}" text-anchor="middle" font-family="Nunito, sans-serif" '
            f'font-size="10.5" font-weight="800" fill="{RED}">{text}</text></g>')


T = {
    'floorL': '#ded6c4', 'floorR': '#ece6d6', 'floor': '#f7f2e7',
    'devL': '#c2dcd1', 'devR': '#d9eae2', 'dev': '#ffffff',
    'poolL': '#0d6048', 'poolR': '#12795b', 'pool': '#169b74',
    'gwL': '#2f6f8f', 'gwR': '#3b84a6', 'gw': '#55a7c9',
    'appL': '#b98f3d', 'appR': '#d2a852', 'app': '#f0cf7c',
    'stL': '#6d6a8f', 'stR': '#8583a8', 'st': '#a9a7c9',
    'gpuL': '#d4693f', 'gpuR': '#ee7a4c', 'gpu': '#ff9a6d',
}

Z = 26  # platform height


def platform(cx, cy, w, d, tones):
    x, y = cx - w / 2, cy - d / 2
    return box(x, y, 0, w, d, Z, tones), (x, y, w, d)


def device(x, y, kind):
    out = [box(x, y, 0, 74, 50, 6, [T['devL'], T['devR'], '#e9f6ef'])]
    if kind == 'desktop':
        out.append(box(x + 10, y + 8, 6, 38, 32, 32, [T['devL'], T['devR'], T['dev']]))
        out.append(box(x + 52, y + 11, 6, 15, 20, 4, [T['devL'], T['devR'], '#ffffff']))
    elif kind == 'server':
        out.append(box(x + 10, y + 6, 6, 54, 36, 42, [T['devL'], T['devR'], T['dev']]))
        for i in range(3):
            a = iso(x + 14, y + 8, 14 + i * 11)
            b = iso(x + 60, y + 8, 14 + i * 11)
            out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
                       f'stroke="#b9cdc6" stroke-width="1.8"/>')
    elif kind == 'gpu':
        out.append(box(x + 8, y + 10, 6, 58, 7, 7, [T['gpuL'], T['gpuR'], T['gpu']]))
        out.append(box(x + 8, y + 10, 14, 58, 11, 13, [T['gpuL'], T['gpuR'], '#ffb189']))
    else:
        out.append(box(x + 10, y + 6, 6, 48, 4, 26, [T['devL'], T['devR'], T['dev']]))
        out.append(box(x + 8, y + 11, 6, 52, 24, 4, [T['devL'], T['devR'], '#ffffff']))
    return ''.join(out)


def bridge(x1, y1, x2, y2, z=Z, width=8):
    a = iso(x1, y1, z + width / 2)
    b = iso(x2, y2, z + width / 2)
    return (f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#9dc4b3" '
            f'stroke-width="{width}" stroke-linecap="round" opacity=".95"/>'
            f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#e2f3ea" '
            f'stroke-width="1.6"/>')


def build() -> str:
    S.append(f'<ellipse cx="{OX}" cy="{OY + 210}" rx="600" ry="150" fill="#14302a" opacity=".06"/>')
    S.append(box(-420, -300, -10, 840, 600, 10, [T['floorL'], T['floorR'], T['floor']]))

    # platforms (app, gateway, pool, storage) in a row on the floor
    platforms = [
        (-400, -20, 170, 130, (T['appL'], T['appR'], '#f7dda0'), 'app · users'),
        (-200, -10, 180, 140, (T['gwL'], T['gwR'], '#7cc3dd'), 'gateway · L1–L2'),
        (70, 20, 230, 170, (T['poolL'], T['poolR'], '#1cb184'), 'pool · L3–L5'),
        (330, 60, 150, 120, (T['stL'], T['stR'], '#c2c0dd'), 'storage · blocks'),
    ]
    rects = []
    for cx, cy, w, d, tones, _label in platforms:
        part, rect = platform(cx, cy, w, d, tones)
        S.append(part)
        rects.append((rect, _label))

    # bridges between platforms
    S.append(bridge(-313, 30, -292, 26))
    S.append(bridge(-108, 34, -48, 40))
    S.append(bridge(188, 48, 253, 56))

    # app blocks
    for gx, gy in ((-448, -46), (-396, -58)):
        S.append(box(gx, gy, Z, 40, 30, 28, [T['appL'], T['appR'], T['app']]))
    # gateway blocks
    for index, (gx, gy) in enumerate(((-252, -46), (-212, -20), (-248, 22))):
        S.append(box(gx, gy, Z, 42, 32, 28 + index * 6, [T['gwL'], T['gwR'], T['gw']]))
    # pool tower and GPUs
    S.append(box(18, 0, Z, 92, 92, 52, [T['poolL'], T['poolR'], T['pool']]))
    for gx, gy in ((-38, 84), (58, 108), (140, 76)):
        S.append(box(gx, gy, Z, 52, 8, 8, [T['gpuL'], T['gpuR'], T['gpu']]))
        S.append(box(gx, gy, Z + 8, 52, 11, 12, [T['gpuL'], T['gpuR'], '#ffb189']))
    # storage drums
    for gx in (286, 332):
        S.append(box(gx, 24, Z, 38, 38, 42, [T['stL'], T['stR'], T['st']]))

    # devices on the floor, feeding the pool
    devices = [(-380, 130, 'desktop'), (-300, 220, 'server'), (-120, 250, 'laptop'), (80, 240, 'gpu'),
               (250, 200, 'desktop'), (300, -180, 'server'), (60, -240, 'laptop'), (-240, -200, 'gpu')]
    for x, y, kind in sorted(devices, key=lambda item: item[0] + item[1]):
        S.append(device(x, y, kind))
    for x, y, kind in devices:
        a = iso(x + 36, y + 24, 14)
        b = iso(104, 24, Z)
        mx, my = (a[0] + b[0]) / 2, min(a[1], b[1]) - 14
        S.append(f'<path d="M {a[0]:.1f} {a[1]:.1f} Q {mx:.1f} {my:.1f} {b[0]:.1f} {b[1]:.1f}" fill="none" '
                 f'stroke="#8fbcab" stroke-width="1.4" opacity=".5"/>')

    # platform labels last, so nothing covers them
    for (x, y, w, d), label in rects:
        a = iso(x + 12, y + d + 30, Z + 30)
        S.append(f'<text x="{a[0]:.1f}" y="{a[1]:.1f}" font-family="Nunito, sans-serif" font-size="10.5" '
                 f'font-weight="800" fill="#3f6154" paint-order="stroke" stroke="#ffffff" '
                 f'stroke-width="3" stroke-linejoin="round">{label}</text>')

    # red percentages
    S.append(badge(150, 130, Z + 40, '30% devices'))
    S.append(badge(230, 96, Z + 80, '88.7% hit'))
    S.append(badge(-140, 60, Z + 40, '96.5% queue'))
    S.append(badge(-470, -80, Z + 40, '98% cpu'))
    S.append(badge(-430, 60, Z + 40, '42% gpu'))
    S.append(badge(340, 100, Z + 60, 'all layers'))
    return '\n'.join(S)


PAGE = Path(__file__).resolve().parents[1] / 'pasadhi' / 'web' / 'anatomy' / 'pasadhi-system.html'


def main() -> None:
    scene = build()
    template = PAGE.read_text(encoding='utf-8')
    start = template.index('<svg id="scene"')
    end = template.index('</svg>', start) + len('</svg>')
    replacement = ('<svg id="scene" viewBox="0 0 1240 860" role="img" aria-label="Full system: app, gateway, '
                   'pool and storage platforms with office devices feeding the pool">\n' + scene + '\n</svg>')
    PAGE.write_text(template[:start] + replacement + template[end:], encoding='utf-8')
    print('polygons', scene.count('<polygon'), 'badges', scene.count('stroke="' + RED + '"'))


if __name__ == '__main__':
    main()
