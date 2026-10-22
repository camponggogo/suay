"""Build the PASADHI story pages (EN + TH) with an animated isometric vignette per chapter."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'landing-pasadhi'

VIGNETTES = {
    'machine': '''
<svg viewBox="0 0 240 150" class="vig" role="img" aria-label="one machine">
  <g transform="translate(120,96)">
    <polygon points="0,-46 40,-24 0,-2 -40,-24" fill="#e9f6ef" stroke="#bcd8c9"/>
    <polygon points="-40,-24 0,-2 0,26 -40,4" fill="#cfe6da" stroke="#bcd8c9"/>
    <polygon points="40,-24 0,-2 0,26 40,4" fill="#dcece4" stroke="#bcd8c9"/>
    <circle cx="0" cy="6" r="4" fill="#159a72" class="pulse"/>
    <path d="M40,4 C70,10 70,44 100,44" fill="none" stroke="#159a72" stroke-width="3" class="flow"/>
  </g>
</svg>''',
    'heartbeat': '''
<svg viewBox="0 0 240 150" class="vig" role="img" aria-label="heartbeat">
  <g transform="translate(120,100)">
    <polygon points="0,-52 26,-38 0,-24 -26,-38" fill="#e9f6ef" stroke="#bcd8c9"/>
    <polygon points="-26,-38 0,-24 0,30 -26,16" fill="#cfe6da" stroke="#bcd8c9"/>
    <polygon points="26,-38 0,-24 0,30 26,16" fill="#dcece4" stroke="#bcd8c9"/>
    <circle cx="0" cy="-38" r="6" fill="#159a72" class="pulse"/>
    <circle cx="0" cy="-38" r="12" fill="none" stroke="#159a72" class="ping"/>
    <circle cx="0" cy="-38" r="18" fill="none" stroke="#159a72" class="ping p2"/>
  </g>
</svg>''',
    'loop': '''
<svg viewBox="0 0 240 150" class="vig" role="img" aria-label="dial">
  <g transform="translate(120,78)">
    <circle r="46" fill="#fff" stroke="#cfe0d7"/>
    <circle r="38" fill="none" stroke="#e6efe9"/>
    <g stroke="#9fb8ac" stroke-width="1">
      <line x1="0" y1="-38" x2="0" y2="-32"/><line x1="27" y1="-27" x2="22" y2="-22"/>
      <line x1="38" y1="0" x2="32" y2="0"/><line x1="27" y1="27" x2="22" y2="22"/>
      <line x1="0" y1="38" x2="0" y2="32"/><line x1="-27" y1="27" x2="-22" y2="22"/>
      <line x1="-38" y1="0" x2="-32" y2="0"/><line x1="-27" y1="-27" x2="-22" y2="-22"/>
    </g>
    <line x1="0" y1="0" x2="30" y2="0" stroke="#e0563f" stroke-width="3" stroke-linecap="round" class="sweep"/>
    <circle r="4" fill="#14302a"/>
  </g>
</svg>''',
    'cache': '''
<svg viewBox="0 0 240 150" class="vig" role="img" aria-label="cache blocks">
  <g transform="translate(28,86)">
    <g fill="#dcece4" stroke="#bcd8c9">
      <rect x="0" y="-14" width="26" height="20" rx="4" class="blk b1"/>
      <rect x="30" y="-14" width="26" height="20" rx="4" class="blk b2"/>
      <rect x="60" y="-14" width="26" height="20" rx="4" class="blk b3"/>
      <rect x="90" y="-14" width="26" height="20" rx="4" class="blk b4"/>
      <rect x="120" y="-14" width="26" height="20" rx="4" class="blk b5"/>
      <rect x="150" y="-14" width="26" height="20" rx="4" class="blk b6"/>
    </g>
    <path d="M0,30 H176" stroke="#cfe0d7" stroke-width="2"/>
    <circle r="5" fill="#159a72" class="dot"><animateMotion dur="3.6s" repeatCount="indefinite"
      path="M0,30 H176"/></circle>
  </g>
</svg>''',
    'router': '''
<svg viewBox="0 0 240 150" class="vig" role="img" aria-label="router">
  <g transform="translate(120,96)">
    <circle r="10" fill="#159a72"/>
    <g stroke="#bcd8c9" stroke-width="2" fill="none">
      <path d="M10,-4 L64,-40"/><path d="M10,0 L70,0"/><path d="M10,4 L64,40"/>
    </g>
    <g fill="#e9f6ef" stroke="#bcd8c9">
      <rect x="64" y="-56" width="34" height="26" rx="6"/>
      <rect x="70" y="-13" width="34" height="26" rx="6"/>
      <rect x="64" y="30" width="34" height="26" rx="6"/>
    </g>
    <circle r="5" fill="#ffd166" class="pick">
      <animateMotion dur="2.6s" repeatCount="indefinite" path="M10,0 L70,0"/>
    </circle>
  </g>
</svg>''',
    'mesh': '''
<svg viewBox="0 0 240 150" class="vig" role="img" aria-label="mesh">
  <g transform="translate(120,92)">
    <g stroke="#9ec9b6" stroke-width="1.6" fill="none" opacity=".9">
      <path d="M-62,-26 L0,-52 L62,-26 L0,0 Z"/><path d="M-62,26 L0,52 L62,26 L0,0 Z"/>
      <path d="M-62,-26 L-62,26"/><path d="M62,-26 L62,26"/><path d="M0,-52 L0,52"/>
    </g>
    <g fill="#159a72">
      <circle cx="0" cy="0" r="7"/>
      <circle cx="-62" cy="-26" r="4"/><circle cx="62" cy="-26" r="4"/>
      <circle cx="-62" cy="26" r="4"/><circle cx="62" cy="26" r="4"/>
      <circle cx="0" cy="-52" r="4"/><circle cx="0" cy="52" r="4"/>
    </g>
    <circle r="4.5" fill="#ffd166"><animateMotion dur="4.2s" repeatCount="indefinite"
      path="M-62,-26 L0,-52 L62,-26 L62,26 L0,52 L-62,26 Z"/></circle>
  </g>
</svg>''',
}

CHAPTERS = [
    {
        'date': '2026-10-19', 'metric': '12.0 req/s · p50 3 811 ms',
        'en_title': 'Fifty machines, one Python process',
        'en_body': 'The first real load test. Throughput sat at 12 req/s while latency grew linearly; at C=50, '
                   '96.5 % of the response time was queueing above a 174 ms floor. The fleet was fine — the '
                   'control path was the bottleneck.',
        'th_title': 'ห้าสิบเครื่อง กับ Python process เดียว',
        'th_body': 'การทดสอบโหลดจริงครั้งแรก throughput นิ่งที่ 12 req/s แต่ latency โตเป็นเส้นตรง ที่ C=50 '
                   'มี 96.5 % ของเวลาตอบสนองเป็นการรอคิวเหนือพื้น 174 ms — ฟลีตไม่ช้า แต่ control path คือคอขวด',
    },
    {
        'date': '2026-10-20', 'metric': '44 → 161 req/s per shard',
        'en_title': 'Split the planes and the fleet wakes up',
        'en_body': 'Heartbeats moved out of the gateway into a node plane: state in memory, one batch flush every '
                   'ten seconds, sharded by crc32. Heartbeat throughput tripled and single-request latency halved.',
        'th_title': 'แยกชั้นการทำงาน ฟลีตก็ตื่น',
        'th_body': 'ย้าย heartbeat ออกจาก gateway ไปเป็น node plane: เก็บ state ในหน่วยความจำ flush เป็นชุดทุก 10 วิ '
                   'แบ่ง shard ด้วย crc32 — heartbeat โต 3.7 เท่า และ latency ต่อคำขอลดลงครึ่งหนึ่ง',
    },
    {
        'date': '2026-10-21', 'metric': '15.7 → 22.3 / 24.8 req/s',
        'en_title': 'The ceiling was the event loop',
        'en_body': 'A raw health endpoint served 58.7–71.2 req/s while a completion cost about 60 ms of loop '
                   'time. Caching the live node list for five seconds took the same workload from 4.9 to 15.0 '
                   'req/s; a second worker added another 48 %.',
        'th_title': 'เพดานคือ event loop',
        'th_body': 'endpoint เปล่า ๆ รับได้ 58.7–71.2 req/s แต่คำขอ completion กินเวลา loop ราว 60 ms — '
                   'cache รายการเครื่อง 5 วินาที พา workload เดิมจาก 4.9 ไป 15.0 req/s และ worker ตัวที่สองเพิ่มอีก 48 %',
    },
    {
        'date': '2026-10-21', 'metric': '111.4 s → 0.71 s (157×)',
        'en_title': 'Stop computing the same tokens twice',
        'en_body': 'Content-addressed 256-token blocks, a registry of which machine holds which block, and '
                   'longest-prefix routing. The median collapsed by 157×; p95 did not move at all.',
        'th_title': 'หยุดคำนวณ token เดิมซ้ำ',
        'th_body': 'บล็อก 256 token ที่อ้างจากเนื้อหา + ทะเบียนว่าเครื่องไหนถือบล็อกไหน + longest-prefix routing '
                   '— ค่ามัธยฐานลด 157 เท่า ส่วน p95 ไม่ขยับ',
    },
    {
        'date': '2026-10-21', 'metric': '90.15 % · 31.5 µs',
        'en_title': 'Specialists beat one big generalist',
        'en_body': 'A router that reads the question and the attached document sends work to the right expert: '
                   '90.15 % over 6 000 queries. Eight 1B experts fit in 32 machines where a mixture needed 86.',
        'th_title': 'ผู้เชี่ยวชาญชนะโมเดลใหญ่ตัวเดียว',
        'th_body': 'router ที่อ่านทั้งคำถามและเอกสารแนบ ส่งงานไปถูกผู้เชี่ยวชาญ: 90.15 % จาก 6,000 คำถาม '
                   'ผู้เชี่ยวชาญ 1B แปดตัวอยู่ใน 32 เครื่อง ขณะที่ mixture ต้องใช้ 86',
    },
    {
        'date': '2026-10-22 → 23', 'metric': '3 564 GFLOP/s · 30 links',
        'en_title': 'One office, one group, one web',
        'en_body': 'Groups of 100–200 machines share 30 % under a single id with an elected controller, working '
                   'offline for internal jobs. Mixed fleets add small GPUs: 1 450 cards reach 9.54 PFLOPS f32, '
                   'and the price follows measured impact, not a flat rate.',
        'th_title': 'ออฟฟิศเดียว กลุ่มเดียว เครือข่ายเดียว',
        'th_body': 'กลุ่ม 100–200 เครื่องแชร์ 30 % ภายใต้ id เดียว มี controller ที่เลือกกันเอง และทำงานออฟไลน์ได้ '
                   'ฟลีตผสมเพิ่มการ์ดจอเล็ก: 1,450 ใบได้ 9.54 PFLOPS f32 และราคาคิดตาม impact ที่วัดได้',
    },
]

CSS_STORY = '''
:root{--paper:#fbf9f3;--ink:#14302a;--muted:#5c7168;--line:#e6e1d5;--brand:#159a72;--brand-d:#0f6a4e;--sun:#ffd166}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.7 "Nunito","Segoe UI",system-ui,sans-serif}
.wrap{width:min(1080px,92%);margin:0 auto;padding:26px 0 60px}
header{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:14px}
.brand{font:800 22px "Nunito",sans-serif;color:var(--brand-d);text-decoration:none}
header nav{display:flex;gap:18px;font-size:13.5px;font-weight:700}
header a{color:#3d5a51;text-decoration:none}
header a:hover{color:var(--brand)}
.hero{padding:48px 0 26px;max-width:760px}
.eyebrow{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--brand-d);font-weight:800}
h1{font:800 clamp(32px,4.4vw,52px)/1.1 "Nunito",sans-serif;letter-spacing:-.03em;margin:12px 0 14px}
h1 em{font-style:normal;color:var(--brand)}
.lead{color:#3d5a51;font-size:17px}
.tl{position:relative;margin-top:30px}
.tl:before{content:"";position:absolute;left:52px;top:10px;bottom:10px;width:2px;background:#dfeee6}
.chapter{display:grid;grid-template-columns:96px 200px 1fr;gap:22px;padding:22px 0;border-bottom:1px dashed #e4efe9;align-items:start}
.chapter:last-child{border-bottom:0}
.when{font:700 12px "Nunito",sans-serif;color:var(--muted);padding-top:8px}
.dot{position:relative}
.dot:before{content:"";position:absolute;left:-31px;top:10px;width:11px;height:11px;border-radius:50%;
  background:var(--brand);box-shadow:0 0 0 5px #e8f7f0}
.body h2{font:800 22px/1.25 "Nunito",sans-serif;margin:0 0 6px}
.body p{color:#42604f;margin:0 0 10px;font-size:15px}
.metric{display:inline-block;background:#e8f7f0;color:var(--brand-d);font:800 12.5px "Nunito",sans-serif;
  padding:6px 12px;border-radius:999px}
.vig{width:100%;max-width:190px;height:auto;display:block;margin:6px 0 0}
.vig .pulse{animation:pulse 2s ease-in-out infinite}
.vig .ping{opacity:0;transform-origin:center;animation:ping 2.6s ease-out infinite}
.vig .ping.p2{animation-delay:1.3s}
.vig .sweep{transform-origin:0 0;animation:sweep 4s ease-in-out infinite}
.vig .blk{animation:blink 3.6s ease-in-out infinite}
.vig .b2{animation-delay:.3s}.vig .b3{animation-delay:.6s}.vig .b4{animation-delay:.9s}
.vig .b5{animation-delay:1.2s}.vig .b6{animation-delay:1.5s}
.vig .pick{animation:pulse 1.4s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
@keyframes ping{0%{opacity:.55;transform:scale(.6)}100%{opacity:0;transform:scale(1.8)}}
@keyframes sweep{0%,100%{transform:rotate(-38deg)}50%{transform:rotate(38deg)}}
@keyframes blink{0%,100%{fill:#dcece4}30%{fill:#8fd6bb}}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:28px 0}
.two a{display:block;text-decoration:none;border:1px solid var(--line);border-radius:16px;background:#fff;padding:14px}
.two img{width:100%;height:auto;border-radius:10px;margin-bottom:8px}
.two b{color:var(--brand-d)}
footer{border-top:1px solid var(--line);margin-top:40px;padding-top:20px;color:var(--muted);font-size:12.5px}
@media(max-width:860px){.chapter{grid-template-columns:74px 1fr}.vig-wrap{grid-column:2;max-width:220px}.body{grid-column:2}}
@media(max-width:760px){.tl:before{left:8px}.chapter{grid-template-columns:1fr;gap:6px;padding-left:26px}
  .dot:before{left:-26px}.two{grid-template-columns:1fr}}
'''

PAGE = '''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="https://pasadhi.tech/{slug}">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap">
<style>{css}</style>
</head><body><div class="wrap">
<header><a class="brand" href="{home}">PASADHI</a>
  <nav><a href="{home}#how">{nav_how}</a><a href="{home}#pricing">{nav_price}</a>
  <a href="{home}#download">{nav_download}</a><a href="{story_other}">{other_label}</a></nav></header>
<div class="hero"><p class="eyebrow">{kicker}</p><h1>{heading}</h1><p class="lead">{lead}</p></div>
<div class="tl">
{chapters}
</div>
<div class="two">
  <a href="{home}anatomy/pool.html"><img src="{home}anatomy/pool.png" alt="pool"><b>{pool_label}</b></a>
  <a href="{home}anatomy/mesh.html"><img src="{home}anatomy/mesh.png" alt="mesh"><b>{mesh_label}</b></a>
</div>
<footer>{footer}</footer>
</div></body></html>'''

CHAPTER = '''<div class="chapter"><div class="when">{date}</div>
 <div class="vig-wrap">{vig}</div>
 <div class="body dot"><h2>{title}</h2><p>{body}</p><span class="metric">{metric}</span></div></div>'''


def build(lang: str) -> str:
    en = lang == 'en'
    chapters = []
    for index, chapter in enumerate(CHAPTERS):
        key = ['machine', 'heartbeat', 'loop', 'cache', 'router', 'mesh'][index]
        chapters.append(CHAPTER.format(
            date=chapter['date'],
            vig=VIGNETTES[key],
            title=chapter['en_title'] if en else chapter['th_title'],
            body=chapter['en_body'] if en else chapter['th_body'],
            metric=chapter['metric']))
    return PAGE.format(
        lang='en' if en else 'th',
        css=CSS_STORY,
        title='PASADHI — how it was built' if en else 'PASADHI — เส้นทางการสร้าง',
        description=('Six measured steps from a 50-machine test bed to a mesh of offices, GPUs and groups.'
                     if en else 'หกก้าวที่วัดได้ จากการทดสอบ 50 เครื่อง สู่ตาข่ายของออฟฟิศ GPU และกลุ่ม'),
        slug='' if en else 'th/story.html',
        home='' if en else '../',
        nav_how='How it works',
        nav_price='Pricing',
        nav_download='Download',
        story_other='th/story.html' if en else 'story.html',
        other_label='ไทย' if en else 'English',
        kicker='The build log, told as a story' if en else 'บันทึกการสร้าง เล่าเป็นเรื่อง',
        heading=('Six measurements that turned<br><em>a room of PCs into a pool</em>' if en
                 else 'หกการวัดที่เปลี่ยน<br><em>ห้องคอมพิวเตอร์ให้เป็นคลัสเตอร์เดียว</em>'),
        lead=('Every step below changed the architecture because a number said so. The failed ideas are kept in '
              'the repository, because they are the part that saves the next team a week.'
              if en else 'ทุกก้าวด้านล่างเปลี่ยนสถาปัตยกรรมเพราะตัวเลขบอกไว้ ความคิดที่ล้มเหลวถูกเก็บไว้ใน repo '
                         'เพราะนั่นคือส่วนที่ช่วยให้ทีมถัดไปประหยัดเวลาหนึ่งสัปดาห์'),
        chapters='\n'.join(chapters),
        pool_label='See the pool move (isometric)' if en else 'ดู pool ที่ขยับได้ (isometric)',
        mesh_label='See the mesh move (isometric)' if en else 'ดู mesh ที่ขยับได้ (isometric)',
        footer=('© 2026 PASADHI contributors · MIT for the open core · '
                '<a href="download/PASADHI-solution.pdf">Solution paper (PDF)</a>' if en else
                '© 2026 PASADHI contributors · แกนหลัก MIT · '
                '<a href="../download/PASADHI-solution.pdf">Solution paper (PDF)</a>'),
    )


def main() -> None:
    (OUT / 'story.html').write_text(build('en'), encoding='utf-8')
    (OUT / 'th').mkdir(parents=True, exist_ok=True)
    (OUT / 'th' / 'story.html').write_text(build('th'), encoding='utf-8')
    print('wrote story.html and th/story.html')


if __name__ == '__main__':
    main()
