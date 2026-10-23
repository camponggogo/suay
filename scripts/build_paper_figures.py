"""Render figure-only, high-resolution PNGs for the paper (no page chrome)."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'pasadhi' / 'web' / 'anatomy'
BUILD = ROOT / 'pasadhi' / 'paper' / '_build'
EDGE = Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')

PAGES = [
    ('pasadhi-system.html', 'pasadhi-system-fig.png', 1360, 900),
    ('pasadhi-install.html', 'pasadhi-install-fig.png', 1120, 860),
]


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    for source, target, width, height in PAGES:
        text = (WEB / source).read_text(encoding='utf-8')
        match = re.search(r'<svg[^>]*>.*?</svg>', text, re.S)
        if not match:
            raise SystemExit(f'no svg in {source}')
        svg = match.group(0)
        svg = re.sub(r'viewBox="([^"]+)"', lambda m: f'viewBox="{m.group(1)}" preserveAspectRatio="xMidYMid meet"', svg)
        wrapper = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@import url("{(ROOT / 'pasadhi/web/fonts/fonts.css').as_uri()}");
html,body{{margin:0;padding:0;background:#fff}}
svg{{display:block;width:100vw;height:auto}}
</style></head><body>{svg}</body></html>"""
        html_path = BUILD / source.replace('.html', '-fig.html')
        html_path.write_text(wrapper, encoding='utf-8')
        out = WEB / target
        command = [str(EDGE), '--headless=new', '--disable-gpu', '--hide-scrollbars',
                   '--force-device-scale-factor=2', '--virtual-time-budget=8000',
                   f'--window-size={width},{height}', f'--screenshot={out}', html_path.as_uri()]
        subprocess.run(command, capture_output=True, text=True)
        print(target, out.stat().st_size if out.exists() else 'FAILED')


if __name__ == '__main__':
    main()
