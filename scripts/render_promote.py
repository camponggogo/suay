"""Reproducible SUAY motion-graphics exports. Requires FFmpeg with libx264."""
from pathlib import Path
import argparse
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SCENES = [
    (0, 4, 'Your next AI resource', 'is already here.'),
    (4, 9, 'Wake old machines.', 'Run AI together.'),
    (9, 14, 'Explore Python + Rust', 'Different tools. Shared ambition.'),
    (14, 19, 'Start with your local network.', 'Build with your community.'),
    (19, 24, 'SUAY / Open source', 'github.com/camponggogo/suay'),
]


def render(portrait=False):
    width, height = (1080, 1920) if portrait else (1920, 1080)
    out = ROOT / ('.local/promote' if portrait else 'landing/assets')
    out.mkdir(parents=True, exist_ok=True)
    work = ROOT / '.local/promote/render'
    work.mkdir(parents=True, exist_ok=True)
    name = 'suay-promote-vertical' if portrait else 'suay-promote'
    filters = [f'scale={width-100}:{height-330}:force_original_aspect_ratio=decrease:force_divisible_by=2',
               f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x0c1411',
               'setsar=1',
               'drawbox=x=0:y=0:w=iw:h=190:color=0x0c1411@0.95:t=fill',
               f'drawbox=x=0:y={height-210}:w=iw:h=210:color=0x0c1411@0.95:t=fill']
    font = 'C\\:/Windows/Fonts/segoeuib.ttf'
    for i, (start, end, title, subtitle) in enumerate(SCENES):
        for j, content in enumerate((title, subtitle)):
            path = work / f'{i}-{j}.txt'
            path.write_text(content, encoding='utf-8')
            relative = path.relative_to(ROOT).as_posix()
            size = (53 if portrait else 62) if j == 0 else (34 if portrait else 40)
            y = (80 if portrait else 46) if j == 0 else height-155
            color = '0xd3ff85' if j == 0 else 'white'
            filters.append(f"drawtext=fontfile='{font}':textfile='{relative}':fontsize={size}:fontcolor={color}:x=(w-tw)/2:y={y}:enable='gte(t,{start})*lt(t,{end})'")
    filters += [f"drawtext=fontfile='{font}':text='campong.online':fontsize=24:fontcolor=0xabb6a3:x=(w-tw)/2:y=h-70",
                "fade=t=in:st=0:d=0.6", "fade=t=out:st=23.4:d=0.6"]
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','warning','-y',
                    '-loop','1','-framerate','24','-i','landing/assets/suay-device-landing.png',
                    '-vf',','.join(filters),'-t','24','-an','-c:v','libx264',
                    '-preset','fast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',
                    str(out/(name+'.mp4'))], cwd=ROOT, check=True)
    print(out/(name+'.mp4'))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--portrait', action='store_true')
    render(parser.parse_args().portrait)
