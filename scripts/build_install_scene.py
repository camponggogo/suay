"""Four-panel isometric figure: how PASADHI is installed, step by step."""
from __future__ import annotations

from pathlib import Path

COS, SIN = 0.8660254, 0.5
RED = '#d93f2b'
S: list[str] = []

T = {
    'floorL': '#ded6c4', 'floorR': '#ece6d6', 'floor': '#f7f2e7',
    'devL': '#c2dcd1', 'devR': '#d9eae2', 'dev': '#ffffff',
    'poolL': '#0d6048', 'poolR': '#12795b', 'pool': '#169b74',
    'gpuL': '#d4693f', 'gpuR': '#ee7a4c', 'gpu': '#ff9a6d',
    'appL': '#b98f3d', 'appR': '#d2a852', 'app': '#f0cf7c',
}


class Panel:
    def __init__(self, ox: float, oy: float) -> None:
        self.ox, self.oy = ox, oy
        self.out: list[str] = []

    def iso(self, x, y, z=0.0):
        return self.ox + (x - y) * COS, self.oy + (x + y) * SIN - z

    def pt(self, x, y, z=0.0):
        a, b = self.iso(x, y, z)
        return f'{a:.1f},{b:.1f}'

    def box(self, x, y, z, w, d, h, tones, stroke='#b9d0c4'):
        top = ' '.join([self.pt(x, y, z + h), self.pt(x + w, y, z + h),
                        self.pt(x + w, y + d, z + h), self.pt(x, y + d, z + h)])
        left = ' '.join([self.pt(x, y + d, z + h), self.pt(x + w, y + d, z + h),
                         self.pt(x + w, y + d, z), self.pt(x, y + d, z)])
        right = ' '.join([self.pt(x + w, y, z + h), self.pt(x + w, y + d, z + h),
                          self.pt(x + w, y + d, z), self.pt(x + w, y, z)])
        self.out.append(f'<polygon points="{left}" fill="{tones[0]}" stroke="{stroke}" stroke-width="0.8"/>'
                        f'<polygon points="{right}" fill="{tones[1]}" stroke="{stroke}" stroke-width="0.8"/>'
                        f'<polygon points="{top}" fill="{tones[2]}" stroke="{stroke}" stroke-width="0.8"/>')

    def text(self, x, y, z, value, size=9.5, weight='800', fill='#3f6154', anchor='start'):
        a = self.iso(x, y, z)
        self.out.append(f'<text x="{a[0]:.1f}" y="{a[1]:.1f}" text-anchor="{anchor}" '
                        f'font-family="Nunito, sans-serif" font-size="{size}" font-weight="{weight}" '
                        f'fill="{fill}">{value}</text>')

    def dot(self, x, y, z, value):
        a = self.iso(x, y, z)
        self.out.append(f'<circle cx="{a[0]:.1f}" cy="{a[1]:.1f}" r="11" fill="{RED}"/>'
                        f'<text x="{a[0]:.1f}" y="{a[1] + 4:.1f}" text-anchor="middle" '
                        f'font-family="Nunito, sans-serif" font-size="12" font-weight="800" '
                        f'fill="#fff">{value}</text>')

    def arrow(self, x, y, z, height=34):
        a = self.iso(x, y, z)
        self.out.append(f'<path d="M {a[0]:.1f} {a[1] - height:.1f} L {a[0]:.1f} {a[1] - 4:.1f}" '
                        f'stroke="{RED}" stroke-width="2.2" stroke-linecap="round"/>'
                        f'<path d="M {a[0] - 5:.1f} {a[1] - 10:.1f} L {a[0]:.1f} {a[1] - 1:.1f} '
                        f'L {a[0] + 5:.1f} {a[1] - 10:.1f}" fill="none" stroke="{RED}" stroke-width="2.2" '
                        f'stroke-linecap="round"/>')

    def render(self):
        return ''.join(self.out)


def plate(p: Panel):
    p.box(-60, -50, -8, 120, 100, 8, [T['floorL'], T['floorR'], T['floor']])
    p.box(-52, -42, 0, 104, 84, 4, ['#e9e1cf', '#f2ecdc', '#fbf6e9'])


def dotted(p: Panel, value):
    p.dot(-46, -38, 8, value)


def step1(ox, oy):
    p = Panel(ox, oy)
    plate(p)
    p.box(-34, 6, 4, 46, 34, 5, [T['devL'], T['devR'], '#eef8f2'])
    p.box(-26, 10, 9, 30, 4, 20, [T['devL'], T['devR'], T['dev']])
    p.box(-28, 14, 9, 34, 22, 3, [T['devL'], T['devR'], '#ffffff'])
    p.box(6, -6, 4, 30, 24, 22, [T['appL'], T['appR'], T['app']])
    p.text(6, -8, 30, 'zip', 8, '700', '#8a6b23')
    p.arrow(12, 30, 4, 26)
    p.text(-52, 46, 6, 'PASADHI-0.1.0', 8.5, '800', '#4d6b5e')
    dotted(p, '1')
    return p.render()


def step2(ox, oy):
    p = Panel(ox, oy)
    plate(p)
    p.box(-38, 2, 4, 62, 8, 34, [T['devL'], T['devR'], T['dev']])
    p.box(-42, 6, 4, 70, 26, 4, [T['devL'], T['devR'], '#ffffff'])
    for index in range(4):
        p.box(-32 + index * 14, 10, 10, 8, 18, 3, ['#cfe3da', '#dfeee7', '#ffffff'])
        p.box(-30 + index * 14, 12, 13, 4, 14, 8 + index * 3, [T['poolL'], T['poolR'], T['pool']])
    p.text(-40, 42, 8, '5 sliders', 8.5, '800', '#4d6b5e')
    dotted(p, '2')
    return p.render()


def step3(ox, oy):
    p = Panel(ox, oy)
    plate(p)
    p.box(-30, 0, 4, 56, 48, 30, [T['devL'], T['devR'], T['dev']])
    for index in range(3):
        p.box(-22, 8 + index * 12, 12, 40, 6, 4, [T['devL'], T['devR'], '#ffffff'])
    a = p.iso(-2, 24, 44)
    p.out.append(f'<circle cx="{a[0]:.1f}" cy="{a[1]:.1f}" r="12" fill="none" stroke="{T["pool"]}" '
                 f'stroke-width="3" stroke-dasharray="6 4"><animateTransform attributeName="transform" '
                 f'type="rotate" from="0 {a[0]:.1f} {a[1]:.1f}" to="360 {a[0]:.1f} {a[1]:.1f}" '
                 f'dur="5s" repeatCount="indefinite"/></circle>')
    p.text(-34, 54, 8, 'start with the OS', 8.5, '800', '#4d6b5e')
    dotted(p, '3')
    return p.render()


def step4(ox, oy):
    p = Panel(ox, oy)
    plate(p)
    p.box(-40, 2, 4, 26, 20, 18, [T['devL'], T['devR'], T['dev']])
    p.box(4, -2, 4, 40, 34, 26, [T['poolL'], T['poolR'], T['pool']])
    p.box(-4, 8, 30, 20, 14, 6, [T['gpuL'], T['gpuR'], T['gpu']])
    a = p.iso(-12, 22, 18)
    b = p.iso(6, 16, 22)
    p.out.append(f'<path id="flow" d="M {a[0]:.1f} {a[1]:.1f} Q {(a[0] + b[0]) / 2:.1f} {min(a[1], b[1]) - 26:.1f} '
                 f'{b[0]:.1f} {b[1]:.1f}" fill="none" stroke="#8fbcab" stroke-width="1.8"/>')
    p.out.append(f'<circle r="3.4" fill="{RED}"><animateMotion dur="2.4s" repeatCount="indefinite">'
                 f'<mpath href="#flow"/></animateMotion></circle>')
    p.text(-44, 46, 8, 'join the pool', 8.5, '800', '#4d6b5e')
    dotted(p, '4')
    return p.render()


PAGE = Path(__file__).resolve().parents[1] / 'pasadhi' / 'web' / 'anatomy' / 'pasadhi-install.html'


def build() -> str:
    S.clear()
    spots = ((230, 190), (620, 190), (230, 560), (620, 560))
    for index, (ox, oy) in enumerate(spots):
        S.append((step1, step2, step3, step4)[index](ox, oy))
    captions = ('download the build', 'probe, then set the five shares', 'let it start with the OS',
                'it joins the pool and earns')
    for index, (ox, oy) in enumerate(spots):
        S.append(f'<text x="{ox}" y="{oy + 118}" text-anchor="middle" font-family="Nunito, sans-serif" '
                 f'font-size="12" font-weight="800" fill="#3f6154">{captions[index]}</text>')
    return '\n'.join(S)


def main() -> None:
    scene = build()
    template = PAGE.read_text(encoding='utf-8')
    start = template.index('<svg id="scene"')
    end = template.index('</svg>', start) + len('</svg>')
    replacement = ('<svg id="scene" viewBox="80 90 800 610" role="img" aria-label="Four installation steps in '
                   'isometric view: download, probe, autostart, join the pool">\n' + scene + '\n</svg>')
    PAGE.write_text(template[:start] + replacement + template[end:], encoding='utf-8')
    print('polygons', scene.count('<polygon'), 'steps', scene.count('r="11"'))


if __name__ == '__main__':
    main()
