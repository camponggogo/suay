"""SUAY physical gateway explainer: shared geometry -> SVG, PNG and animated GIF.

Uses Pillow for raster output. No browser, remote fonts or generative service.
All animation is illustrative; it is not a performance or telemetry readout.
"""
from dataclasses import dataclass
from pathlib import Path
from html import escape
import json
import math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'landing/assets/anatomy'
W, H = 1800, 1120
BG, INK, MUTED, LIME = '#101916', '#edf0e6', '#a2b09f', '#cefa85'
STEPS = [
    ('Send an AI request', 'A developer app submits a prompt with a scoped API key.', 'DEVELOPER APPLICATION'),
    ('Check access', 'The gateway verifies key scope, expiry and revocation.', 'ORGANIZATION GATEWAY'),
    ('Enforce the policy', 'Only approved models pass. Accepted requests use the key budget.', 'MODEL ALLOWLIST / REQUEST BUDGET'),
    ('Run the approved backend', 'The gateway forwards to the fixed endpoint configured by the operator.', 'APPROVED INFERENCE BACKEND'),
    ('Return the response', 'The backend result returns to the app. The submission is audited.', 'RESPONSE / AUDIT'),
]


def p(x, y, z):
    return (440 + .9*x - .9*y, 340 + .38*x + .38*y - .9*z)


@dataclass
class Part:
    name: str
    x: float
    y: float
    z: float
    w: float
    d: float
    h: float
    group: str = 'base'
    material: str = 'metal'


PARTS = []


def box(name, x, y, z, w, d, h, group='base', material='metal'):
    PARTS.append(Part(name, x, y, z, w, d, h, group, material))


def model():
    # Grounded bench, feet, machined bezel and mounting hardware.
    for x in (24, 796):
        for y in (22, 403):
            box('rubber foot', x, y, -36, 28, 25, 36, material='rubber')
    box('bench chassis', 0, 0, 0, 850, 440, 16)
    box('inset work surface', 10, 10, 16, 830, 420, 3, material='dark')
    for x in (16, 826):
        for y in (17, 415):
            box('corner screw seat', x, y, 19, 6, 6, 2, material='screw')
    # Old desktop workstation: CRT, ventilation, stand, keyboard and tower.
    box('computer base', 48, 115, 19, 145, 104, 10, 'app')
    box('monitor foot', 77, 142, 29, 70, 52, 7, 'app')
    box('monitor riser', 96, 156, 36, 32, 24, 18, 'app')
    box('CRT shell', 53, 109, 54, 128, 79, 107, 'app', 'cream')
    box('CRT front bezel', 59, 188, 62, 116, 8, 91, 'app', 'cream')
    box('CRT glass', 70, 196, 77, 92, 2, 67, 'app', 'screen')
    for z in (88, 102, 116):
        box('screen prompt line', 80, 198, z, 48 if z == 116 else 65, 1, 3, 'app', 'display')
    box('monitor power button', 158, 197, 66, 6, 2, 5, 'app', 'led')
    box('keyboard bed', 48, 231, 19, 148, 47, 7, 'app', 'cream')
    for row in range(4):
        for col in range(10):
            box('keyboard key', 54+col*13, 235+row*9, 26, 10, 6, 3, 'app', 'key')
    box('tower case', 211, 119, 19, 54, 104, 134, 'app', 'cream')
    box('tower front panel', 216, 223, 25, 43, 3, 121, 'app', 'key')
    for z in (37, 47, 57, 67, 77):
        box('tower vent', 222, 226, z, 30, 1, 2, 'app', 'dark')
    box('tower drive bay', 220, 226, 114, 33, 1, 9, 'app', 'dark')
    box('tower status lamp', 247, 226, 95, 4, 1, 4, 'app', 'led')
    box('app network port', 215, 252, 23, 17, 10, 16, 'app', 'port')
    # SUAY gateway appliance with physical key slot and policy indicator bank.
    box('gateway mounting tray', 330, 103, 19, 208, 159, 8, 'gateway')
    box('gateway chassis', 340, 113, 27, 188, 133, 94, 'gateway')
    box('gateway lid', 337, 110, 121, 194, 139, 5, 'gateway', 'light')
    box('gateway front fascia', 346, 246, 33, 176, 6, 81, 'gateway', 'dark')
    box('key card socket', 356, 252, 84, 48, 2, 6, 'auth', 'port')
    box('scoped key card', 366, 253, 82, 28, 17, 2, 'auth', 'lime')
    box('gateway display glass', 416, 252, 66, 61, 2, 35, 'policy', 'screen')
    for index in range(4):
        box('policy display bar', 422+index*12, 254, 72, 7, 1, 8+index*4, 'policy', 'display')
    for index in range(3):
        box('scope indicator', 358+index*15, 252, 53, 6, 2, 6, 'auth', 'led')
    box('request input socket', 363, 252, 26, 22, 10, 15, 'gateway', 'port')
    box('backend output socket', 489, 252, 26, 22, 10, 15, 'gateway', 'port')
    for index in range(9):
        box('lid ventilation rib', 353+index*17, 132, 126, 3, 70, 1, 'gateway', 'dark')
    for x in (345, 517):
        for y in (119, 235):
            box('lid fastener', x, y, 126, 5, 5, 1, 'gateway', 'screw')
    # Approved backend cabinet: rails, populated shelves, disks and status lamps.
    box('rack plinth', 653, 104, 19, 139, 171, 11, 'backend')
    for x in (658, 778):
        box('rack upright', x, 112, 30, 10, 152, 224, 'backend')
    box('rack roof', 656, 108, 254, 135, 163, 9, 'backend', 'light')
    box('rear rack panel', 668, 111, 30, 110, 5, 224, 'backend', 'dark')
    for index in range(4):
        z = 40+index*49
        box('backend sled', 670, 132, z, 104, 132, 39, 'backend')
        box('sled bezel', 670, 264, z+3, 104, 4, 32, 'backend', 'dark')
        for drive in range(3):
            box('disk caddy', 677+drive*24, 268, z+11, 19, 2, 13, 'backend', 'key')
        box('backend indicator', 758, 268, z+14, 5, 2, 5, 'backend', 'led')
    box('backend network socket', 680, 268, 26, 22, 10, 13, 'backend', 'port')
    # Mixed device pool, illustrative rather than a compatibility certification.
    for x,y in ((55,330),(680,330)):
        box('laptop deck',x,y,19,105,76,6,'pool','light')
        box('laptop hinge',x+6,y,25,93,6,5,'pool')
        box('laptop screen casing',x+4,y,30,97,6,66,'pool','metal')
        box('laptop glass',x+10,y+6,36,84,1,53,'pool','screen')
        for row in range(3):
            for col in range(8):
                box('laptop key',x+8+col*11,y+17+row*10,25,8,7,2,'pool','key')
        box('laptop trackpad',x+38,y+51,25,28,17,1,'pool','dark')
        box('laptop network socket',x+91,y+69,19,14,10,9,'pool','port')
    for x,y in ((230,340),(590,350)):
        box('phone cradle',x-6,y-2,19,45,28,6,'pool')
        box('phone body',x,y,25,32,8,87,'pool','dark')
        box('phone glass',x+3,y+8,34,26,1,69,'pool','screen')
        box('phone speaker',x+10,y+9,106,12,1,2,'pool','screw')
        box('phone app tile',x+8,y+9,69,16,1,16,'pool','display')
        box('phone charging port',x+11,y+8,25,10,5,4,'pool','port')
    for x,y in ((320,335),(455,355)):
        for dx,dy in ((3,3),(63,3),(3,43),(63,43)):
            box('Pi mounting standoff',x+dx,y+dy,19,4,4,5,'pool','screw')
        box('Raspberry Pi PCB',x,y,24,72,52,3,'pool','pcb')
        box('Pi processor',x+24,y+16,27,21,20,7,'pool','dark')
        box('Pi USB block',x+47,y+40,27,22,15,14,'pool','light')
        box('Pi ethernet block',x+3,y+40,27,22,15,14,'pool','light')
        for pin in range(10):
            box('Pi GPIO pin',x+5+pin*5,y+3,27,2,4,7,'pool','screw')
        box('Pi activity LED',x+36,y+43,27,3,3,2,'pool','led')
    box('edge computer enclosure',165,345,19,54,55,32,'pool')
    for i in range(7):
        box('edge heatsink fin',169+i*6,349,51,3,45,6,'pool','light')
    box('edge network port',176,400,23,19,6,12,'pool','port')
    assert len(PARTS) >= 80
    assert len({a.name for a in PARTS}) >= 40


class Canvas:
    def __init__(self):
        self.image = Image.new('RGB', (W, H), BG)
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
                    '<title id="title">SUAY: from request to response</title>',
                    '<desc id="desc">Old computers, laptops, Raspberry Pi boards, phones and an edge computer exchange illustrative data around a SUAY gateway and server rack. A demonstration AI Agent web interface sits alongside. Five steps explain the implemented inference proxy; mixed-device compute remains experimental.</desc>',
                    f'<rect width="{W}" height="{H}" fill="{BG}"/>']

    def poly(self, points, fill, stroke='#24372d', width=1):
        self.draw.polygon(points, fill=fill)
        if stroke:
            self.draw.line(points+[points[0]], fill=stroke, width=width, joint='curve')
        self.svg.append(f'<polygon points="'+ ' '.join(f'{x:.2f},{y:.2f}' for x,y in points)+f'" fill="{fill}" stroke="{stroke or "none"}" stroke-width="{width}" stroke-linejoin="round"/>')

    def line(self, points, fill, width=1):
        self.draw.line(points, fill=fill, width=width, joint='curve')
        self.svg.append('<polyline points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in points)+f'" fill="none" stroke="{fill}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')

    def rect(self, xy, fill, outline=None, radius=0):
        self.draw.rounded_rectangle(xy, radius, fill=fill, outline=outline)
        x,y,x2,y2=xy
        self.svg.append(f'<rect x="{x}" y="{y}" width="{x2-x}" height="{y2-y}" rx="{radius}" fill="{fill}" stroke="{outline or "none"}"/>')

    def circle(self, xy, radius, fill):
        x,y=xy
        self.draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill)
        self.svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius}" fill="{fill}"/>')

    def text(self, xy, value, size=20, fill=INK, bold=False):
        fontpath=Path('C:/Windows/Fonts')/('segoeuib.ttf' if bold else 'segoeui.ttf')
        font=ImageFont.truetype(str(fontpath),size) if fontpath.exists() else ImageFont.truetype('DejaVuSans.ttf',size)
        self.draw.text(xy,value,font=font,fill=fill)
        x,y=xy
        self.svg.append(f'<text x="{x}" y="{y+size}" font-family="Segoe UI, DejaVu Sans, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{fill}">{escape(value)}</text>')


PALETTES = {
    'metal': ('#43564a','#273c31','#344a3b'),
    'light': ('#627565','#384e3e','#4b6350'),
    'cream': ('#b4b89b','#747f66','#939d7e'),
    'key': ('#849278','#455d49','#657b5d'),
    'dark': ('#21372a','#14231a','#1b3022'),
    'rubber': ('#19251d','#0b120d','#101b13'),
    'port': ('#111c15','#0a100d','#14261a'),
    'screen': ('#253d29','#122218','#1b3221'),
    'screw': ('#b9c6a8','#586853','#84957b'),
    'lime': (LIME,'#607f3e','#91b854'),
    'pcb': ('#58834b','#25482c','#39603a'),
}


def solid(canvas, a, step):
    x,y,z,w,d,h=a.x,a.y,a.z,a.w,a.d,a.h
    active = a.group == ('app' if step in (0,4) else 'auth' if step==1 else 'policy' if step==2 else 'backend')
    if a.material in ('led','display'):
        shades = (LIME,'#729349','#a4ca6c') if active else ('#59794a','#2a402b','#425d36')
    else:
        shades=PALETTES[a.material]
    # The camera sees the positive X and positive Y faces and the top.
    canvas.poly([p(x,y+d,z),p(x+w,y+d,z),p(x+w,y+d,z+h),p(x,y+d,z+h)],shades[2])
    canvas.poly([p(x+w,y,z),p(x+w,y+d,z),p(x+w,y+d,z+h),p(x+w,y,z+h)],shades[1])
    canvas.poly([p(x,y,z+h),p(x+w,y,z+h),p(x+w,y+d,z+h),p(x,y+d,z+h)],shades[0])


ROUTES = [
    [(224,262,30),(224,291,23),(374,291,23),(374,262,30)],
    [(500,262,30),(500,291,23),(691,291,23),(691,278,30)],
]
BRANCHES = [
    [(153,409,24),(153,424,23),(440,424,23),(440,291,23),(374,291,23),(374,262,30)],
    [(245,353,26),(245,410,23),(440,410,23),(440,291,23),(374,291,23)],
    [(333,390,32),(333,402,23),(440,402,23),(440,291,23)],
    [(468,410,32),(520,410,23),(520,291,23),(500,291,23)],
    [(605,363,26),(605,424,23),(520,424,23),(520,291,23)],
    [(778,409,24),(778,432,23),(520,432,23),(520,291,23),(500,262,30)],
    [(185,406,30),(185,418,23),(440,418,23),(440,291,23),(374,291,23)],
]


def agent_window(c, step, progress):
    x,y=1230,255
    c.rect((x,y,1740,808),'#142019','#465c43',18)
    c.rect((x+1,y+1,1739,y+43),'#25362a',radius=17)
    for i in range(3): c.circle((x+21+i*16,y+21),4,('#87987c' if i else LIME))
    c.text((x+88,y+10),'AI workspace / concept UI',16,MUTED)
    c.text((x+25,y+67),'SUAY / AI Agent',27,INK,True)
    c.rect((x+387,y+70,x+475,y+99),'#31462c',radius=8)
    c.text((x+405,y+73),'DEMO',15,LIME,True)
    c.text((x+25,y+119),'MODEL / OPERATOR-APPROVED BACKEND',14,MUTED,True)
    c.line([(x+25,y+153),(x+485,y+153)],'#3b503c')
    c.text((x+25,y+177),'YOU',13,LIME,True)
    c.rect((x+25,y+207,x+485,y+281),'#233328',radius=12)
    c.text((x+43,y+226),'Summarize our internal notes.',22,INK)
    status=['Ready to send','Verifying API key','Model + request budget accepted',
            'Waiting for approved backend','Response ready'][step]
    c.circle((x+33,y+317),4,LIME)
    c.text((x+48,y+303),status,20,LIME)
    c.text((x+25,y+356),'SUAY ASSISTANT',13,MUTED,True)
    c.rect((x+25,y+385,x+485,y+472),'#1b2c20','#334c34',12)
    if step==4:
        c.text((x+44,y+400),'Here is a concise summary',21,INK)
        c.text((x+44,y+431),'of the notes you provided.',21,INK)
    else:
        c.text((x+44,y+403),'Your response appears here.',20,MUTED)
        if step==3:
            for i in range(3):
                c.circle((x+48+i*15,y+449),3,LIME if int(progress*6)%3==i else '#506347')
    c.text((x+25,y+500),'ILLUSTRATIVE UI / NOT A LIVE SESSION',13,MUTED)
    c.text((x+25,y+522),'No remote shell or desktop control.',16,LIME)


def packet(route, progress):
    lengths=[math.dist(a,b) for a,b in zip(route,route[1:])]
    remain=progress*sum(lengths)
    for a,b,length in zip(route,route[1:],lengths):
        if remain<=length:
            return p(*(a[i]+(b[i]-a[i])*remain/length for i in range(3)))
        remain-=length
    return p(*route[-1])


def frame(step, progress=.5, light=False):
    c=Canvas()
    c.rect((22,22,W-22,H-22), BG, '#3b4f3e',24)
    c.text((58,47),'FIG 01 / SUAY SYSTEM',17,LIME,True)
    c.text((1380,47),'FROM REQUEST TO RESPONSE',17,MUTED)
    c.text((58,86),'More from the hardware you already own.',38,INK,True)
    c.text((58,139),'Explore shared local AI. Give every team a controlled way to build.',21,MUTED)
    for i,(a,b) in enumerate([
        ('REUSE EXISTING CAPACITY','Measure first. Upgrade with evidence.'),
        ('CONTROL AI ACCESS','Scoped keys / approved models / budgets'),
        ('MANAGE CENTRALLY','Users / policies / usage / audit')]):
        x=58+i*385
        c.rect((x,184,x+363,246),'#1b2a20','#354c35',10)
        c.text((x+14,193),a,16,LIME,True)
        c.text((x+14,220),b,15,MUTED)
    c.text((58,265),'MIXED DEVICES / CONCEPT POOL',14,MUTED,True)
    # Shadow is confined to the supporting floor, beneath every foot.
    c.poly([p(-8,-8,-38),p(865,-8,-38),p(865,458,-38),p(-8,458,-38)],'#0a100d',None)
    # A stable painter order derived from plan depth and then height.
    parts=sorted(PARTS,key=lambda a:(a.x+a.y+.55*(a.w+a.d),a.z))
    # Base before devices; shared surface wiring before the appliances.
    for a in parts:
        if a.group=='base': solid(c,a,step)
    for route in ROUTES+BRANCHES:
        pts=[p(*point) for point in route]
        c.line(pts,'#0a110d',9)
        c.line(pts,'#536d47',3 if route in BRANCHES else 4)
    overlays={'CRT glass','screen prompt line','monitor power button',
              'tower vent','tower drive bay','tower status lamp',
              'gateway display glass','policy display bar','scope indicator',
              'disk caddy','backend indicator','lid ventilation rib','lid fastener',
              'key card socket','scoped key card','laptop glass','phone glass',
              'phone app tile','phone speaker','laptop key',
              'Pi processor','Pi USB block','Pi ethernet block','Pi GPIO pin','Pi activity LED'}
    for a in parts:
        if a.group!='base' and a.name not in overlays and a.name!='edge heatsink fin':
            solid(c,a,step)
            if a.name=='edge computer enclosure':
                for fin in parts:
                    if fin.name=='edge heatsink fin': solid(c,fin,step)
    # Surface details belong on their exposed front faces, above their bezels.
    for a in parts:
        if a.name in overlays and a.material not in ('led','display'): solid(c,a,step)
    for a in parts:
        if a.name in overlays and a.material in ('led','display'): solid(c,a,step)
    # Bidirectional pulses illustrate conversation, not actual peer traffic.
    for i,route in enumerate(BRANCHES):
        phase=(progress*.85+i*.17)%1
        c.circle(packet(route,phase),4,LIME)
        c.circle(packet(route,1-phase),2,'#9dbd88')
    if step in (0,1):
        c.circle(packet(ROUTES[0],progress if step==0 else 1),6,LIME)
    elif step==2:
        c.circle(p(444,254,91),4,LIME)
    elif step==3:
        c.circle(packet(ROUTES[1],progress),6,LIME)
    else:
        route=ROUTES[1] if progress<.5 else ROUTES[0]
        c.circle(packet(route,1-(progress*2 if progress<.5 else (progress-.5)*2)),6,LIME)
    agent_window(c,step,progress)
    c.text((1230,827),'Desktop / Laptop / Mobile / Pi / Edge / Server',17,MUTED)
    c.text((58,866),f'0{step+1} / 05',20,LIME,True)
    c.text((206,860),STEPS[step][0],32,INK,True)
    c.text((206,910),STEPS[step][1],22,MUTED)
    for i in range(5):
        c.rect((206+i*300,963,481+i*300,968),LIME if i==step else '#344638',radius=2)
    c.text((58,1005),'CURRENT GATEWAY + EXPERIMENTAL DEVICE POOL',15,LIME,True)
    c.text((58,1036),'Petals LAN and Rust supervision are separate experiments. Device and model compatibility vary.',19,MUTED)
    c.text((58,1064),'No automatic gateway-to-Petals integration or fleet command transport yet. No guaranteed savings.',17,MUTED)
    c.text((1510,1064),'campong.online',17,LIME,True)
    c.svg.append('</svg>')
    if light:
        # The same four-tone geometry mapped to a paper palette, not an inverted picture.
        mapping={BG:'#f0f0e7',INK:'#203426',MUTED:'#4e6655',LIME:'#547b20',
                 '#3b4f3e':'#bcc7b4','#0a100d':'#d3d8c8','#344638':'#b8c5ae'}
        import re
        svg='\n'.join(c.svg)
        svg=re.sub(r'#[0-9a-fA-F]{6}',lambda m:mapping.get(m[0],m[0]),svg)
        return c.image,svg
    return c.image,'\n'.join(c.svg)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    model()
    # Geometry checks are local checks, not the absent Anatomy kit's full audit.
    assert all(a.w>0 and a.d>0 and a.h>0 for a in PARTS)
    assert all(0<=x<=850 and 0<=y<=440 for r in ROUTES+BRANCHES for x,y,z in r)
    for i in range(5):
        image,svg=frame(i)
        image.save(OUT/f'step-{i+1}.png',optimize=True)
        (OUT/f'step-{i+1}.svg').write_text(svg,encoding='utf-8')
    (OUT/'suay-system-light.svg').write_text(frame(0,light=True)[1],encoding='utf-8')
    (OUT/'suay-system.svg').write_text(frame(0)[1],encoding='utf-8')
    frames=[]
    for i in range(5):
        for j in range(24):
            frames.append(frame(i,j/23)[0].resize((1440,896),Image.Resampling.LANCZOS))
    palette=frames[0].quantize(colors=128)
    frames=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
    frames[0].save(OUT/'suay-system-steps.gif',save_all=True,append_images=frames[1:],
                   duration=[120,130]*60,loop=0,optimize=True,disposal=1)
    (OUT/'steps.json').write_text(json.dumps([{'title':s[0],'description':s[1]} for s in STEPS],indent=2)+'\n')
    print(f'Built {len(PARTS)} physical parts; 5 SVG/PNG steps; 120 frames, 15-second GIF.')


if __name__=='__main__':main()
