"""Build reviewed static translations and matching SEO data. No translation service."""
import base64
import hashlib
import html
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://campong.online/projects/suay/'
LOCALES = json.loads((ROOT/'site_content/locales.json').read_text(encoding='utf-8'))


def url(code):
    return BASE + ('' if code == 'en' else code+'/')


def language_menu(code):
    prefix = './' if code == 'en' else '../'
    links = ''.join(f'<a href="{prefix}{"" if lang=="en" else lang+"/"}" lang="{lang}" hreflang="{lang}"'+(' aria-current="page"' if lang==code else '')+'>'+html.escape(row['name'])+'</a>' for lang,row in LOCALES.items())
    return '<div class="language-switcher"><button type="button" id="language-toggle" aria-label="Choose language" aria-expanded="false" aria-controls="language-options"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="m9 3 6 0 1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1Z"/><circle cx="12" cy="12" r="3"/></svg></button><div id="language-options" hidden><strong>Language</strong>'+links+'</div></div>'


def header(code):
    prefix = './' if code=='en' else '../'
    return f'<header class="nav"><a class="wordmark" href="{prefix}"><img class="brand-network" src="{prefix}assets/suay-network.svg" width="40" height="40" alt="">suay</a><nav aria-label="Navigation"><a href="#versions">Python / Rust</a><a href="#faq">FAQ</a></nav>{language_menu(code)}<a class="github" href="https://github.com/camponggogo/suay">Star on GitHub ↗</a></header>'


def versions(code):
    heading = 'Choose a version' if code=='en' else LOCALES[code]['limits_title']
    detail = 'Python contains the control-plane and Petals pilots. Rust is a local resource supervisor; it does not replace the complete Python stack.' if code=='en' else LOCALES[code]['limits']
    return '<section class="wrap version-section" id="versions"><p class="eyebrow">TWO SOURCE DIRECTORIES / DIFFERENT ROLES</p><h2>'+heading+'</h2><p>'+detail+'</p><div class="version-grid"><article><span class="status available">PYTHON VERSION · PILOT</span><h3>Python</h3><p>Organization API · Petals LAN · Visitor analytics</p><a href="https://github.com/camponggogo/suay/tree/main/versions/python">versions/python ↗</a></article><article><span class="status experiment">RUST VERSION · EXPERIMENTAL</span><h3>Rust</h3><p>Hardware snapshots · Memory admission · Local backend supervision</p><a href="https://github.com/camponggogo/suay/tree/main/versions/rust">versions/rust ↗</a></article></div></section>'


def anatomy(code, prefix):
    thai = code == 'th'
    title = 'SUAY ทำงานอย่างไร — ทีละขั้น' if thai else 'How SUAY works, step by step'
    titles = ['ส่งคำขอ AI','ตรวจสิทธิ์','ตรวจนโยบาย','ประมวลผล','ส่งคำตอบกลับ'] if thai else ['Send request','Check access','Enforce policy','Run backend','Return response']
    descriptions = [
        'แอปส่ง prompt พร้อม API key ที่กำหนดขอบเขตสิทธิ์ไว้',
        'Gateway ตรวจสิทธิ์ inference วันหมดอายุ และสถานะเพิกถอน key',
        'ตรวจว่าโมเดลอยู่ในรายการอนุญาต และหักโควตาจำนวนคำขอที่รับ ไม่ใช่จำนวน model token',
        'ส่งคำขอไปยัง endpoint ของ backend ที่ผู้ดูแลตั้งค่าและอนุมัติไว้',
        'ส่งผลลัพธ์กลับสู่แอป โดยมีบันทึก audit สำหรับคำขอที่รับแล้ว',
    ] if thai else [
        'A developer app sends a prompt with a scoped API key.',
        'The gateway checks inference scope, expiry and revocation.',
        'Check the model allowlist and accepted-request budget. This is not a model-token budget.',
        'Forward to the fixed inference endpoint configured and approved by the operator.',
        'Return the backend result to the app. Accepted submissions are audited.',
    ]
    buttons=''.join(f'<button type="button" data-anatomy-step="{i}" data-description="{html.escape(description,quote=True)}" aria-pressed="{"true" if i==0 else "false"}"><span>0{i+1}</span> {html.escape(label)}</button>' for i,(label,description) in enumerate(zip(titles,descriptions)))
    play,pause = ('เล่น GIF','หยุด') if thai else ('Play GIF','Pause')
    note = 'ภาพสาธิตคอมหลายประเภท Raspberry Pi โทรศัพท์ และหน้าจอ AI Agent • ไม่ใช่ session จริงหรือการรับรองอุปกรณ์ • Petals LAN และ Rust supervisor ยังเป็นส่วนทดลองแยกกัน' if thai else 'Concept device pool with laptops, Raspberry Pi boards, phones and an illustrative AI Agent UI. Not a live session or device certification. Petals LAN and Rust supervision remain separate experiments.'
    benefits = ['ใช้ทรัพยากรเดิมอย่างมีข้อมูลประกอบ','ควบคุมสิทธิ์ โมเดล และโควตาคำขอ','จัดการผู้ใช้ นโยบาย และ audit ส่วนกลาง'] if thai else ['Evaluate the hardware you already own','Control keys, models and request budgets','Manage users, policies and audit centrally']
    benefit_html='<ul class="anatomy-benefits">'+''.join('<li>'+html.escape(item)+'</li>' for item in benefits)+'</ul>'
    return f'''<section class="wrap system-anatomy" id="system-anatomy" data-anatomy data-assets="{prefix}assets/anatomy" aria-labelledby="anatomy-heading"><p class="eyebrow">SUAY / SYSTEM ANATOMY</p><h2 id="anatomy-heading">{title}</h2>{benefit_html}<figure><img data-anatomy-image src="{prefix}assets/anatomy/step-1.png" width="1800" height="1120" loading="lazy" decoding="async" alt="SUAY concept: desktops, laptops, Raspberry Pi, phones, edge computer, gateway and server exchanging data beside a demo AI Agent web UI"><figcaption>{note}</figcaption></figure><div class="anatomy-steps" role="group" aria-label="{'เลือกขั้นตอน' if thai else 'Choose a step'}">{buttons}</div><p class="anatomy-readout" data-anatomy-readout aria-live="polite">{descriptions[0]}</p><div class="anatomy-actions"><button type="button" data-anatomy-play data-play="{play}" data-pause="{pause}" aria-pressed="false">{play}</button><a href="{prefix}assets/anatomy/suay-system-steps.gif" download>{'ดาวน์โหลด GIF' if thai else 'Download GIF'}</a><a href="{prefix}assets/anatomy/suay-system.svg" download>SVG</a><a href="{prefix}assets/anatomy/step-5.png" target="_blank" rel="noopener">{'ดูภาพขนาดเต็ม' if thai else 'View full size'}</a></div><noscript><p>Five steps: send a scoped request; verify access; check model and request budget; run the approved backend; return its response. Download the GIF to view the sequence.</p></noscript></section>'''


def main():
    template=(ROOT/'site_content/index.template.html').read_text(encoding='utf-8')
    template=template.replace('<!-- SITE_HEADER -->',header('en')).replace('<!-- VERSION_CHOOSER -->',versions('en'))
    faq_en=json.loads((ROOT/'site_content/faq.en.json').read_text())
    hashes=[]
    for code,row in LOCALES.items():
        prefix='./' if code=='en' else '../'
        if code=='en':
            body=template
            faq=faq_en
            desc='SUAY: open-source local AI resource sharing, a Python organization gateway and an experimental Rust memory supervisor. Explore source, limits and LAN compute.'
        else:
            desc=row['intro']
            faq=[{'@type':'Question','name':row['q'+str(i)],'acceptedAnswer':{'@type':'Answer','text':row['a'+str(i)]}} for i in [1,2,3]]
            details=''.join('<details><summary>'+item['name']+'</summary><p>'+item['acceptedAnswer']['text']+'</p></details>' for item in faq)
            body=f'''<!doctype html><html lang="{code}"><head><!-- SEO_HEAD --></head><body><a class="skip" href="#main">Skip to content</a>{header(code)}<main id="main"><section class="hero wrap"><div class="hero-copy"><p class="eyebrow">LOCAL AI / OPEN SOURCE / SHARED COMPUTE</p><h1>{row['hero']}<br><span>{row['hero2']}</span></h1><p class="lead">{row['intro']}</p><div class="actions"><a class="btn lime" href="https://github.com/camponggogo/suay">{row['source']} ↗</a></div></div><figure class="network-hero"><img src="../assets/suay-device-landing.png" width="1536" height="1024" fetchpriority="high" alt="SUAY shared-compute concept"><figcaption>Concept illustration · Not a hardware compatibility certification</figcaption></figure></section><section class="wrap project-answer"><h2>{row['how_title']}</h2><p>{row['how']}</p><a href="https://github.com/camponggogo/suay/blob/main/docs/ARCHITECTURE.md">Architecture ↗</a></section>{versions(code)}<section class="wrap search-faq" id="faq"><h2>{row['faq_title']}</h2>{details}</section><section class="join"><div class="wrap"><h2>{row['source']}</h2><pre class="thai-clone"><code>git clone https://github.com/camponggogo/suay.git</code></pre><div class="join-links"><a href="https://github.com/camponggogo/suay">GitHub Star ↗</a><a href="https://github.com/camponggogo/suay/blob/main/CONTRIBUTING.md">Contribute ↗</a></div><p class="license-note">MIT code · Model licenses vary · GitHub Sponsors: setup pending</p></div></section></main><footer class="wrap"><a href="../">SUAY</a><a href="../sitemap.xml">Sitemap</a><span>© 2026 SUAY contributors</span></footer></body></html>'''
        marker='<section class="wrap search-faq"'
        body=body.replace(marker,anatomy(code,prefix)+marker,1)
        graph={'@context':'https://schema.org','@graph':[
            {'@type':'WebSite','@id':BASE+'#website','name':'SUAY','url':BASE,'inLanguage':list(LOCALES)},
            {'@type':'WebPage','@id':url(code)+'#page','url':url(code),'name':row['title'],'inLanguage':code,'isPartOf':{'@id':BASE+'#website'},'about':{'@id':BASE+'#software'}},
            {'@type':'SoftwareSourceCode','@id':BASE+'#software','name':'SUAY','url':BASE,'codeRepository':'https://github.com/camponggogo/suay','license':'https://github.com/camponggogo/suay/blob/main/LICENSE','programmingLanguage':['Python','Rust','JavaScript'],'developmentStatus':'Experimental pilot','author':{'@type':'Person','name':'campong','url':'https://github.com/camponggogo'}},
            {'@type':'FAQPage','@id':url(code)+'#faq','inLanguage':code,'mainEntity':faq}]}
        data=json.dumps(graph,ensure_ascii=False,separators=(',',':'))
        hashes.append('sha256-'+base64.b64encode(hashlib.sha256(data.encode()).digest()).decode())
        alternates=''.join(f'<link rel="alternate" hreflang="{lang}" href="{url(lang)}">' for lang in LOCALES)+f'<link rel="alternate" hreflang="x-default" href="{BASE}">'
        head=f'''<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1"><meta name="theme-color" content="#101413"><title>{html.escape(row['title'])}</title><meta name="description" content="{html.escape(desc,quote=True)}"><link rel="canonical" href="{url(code)}">{alternates}<meta property="og:type" content="website"><meta property="og:site_name" content="SUAY"><meta property="og:url" content="{url(code)}"><meta property="og:title" content="{html.escape(row['title'],quote=True)}"><meta property="og:description" content="{html.escape(desc,quote=True)}"><meta property="og:image" content="{BASE}assets/suay-device-landing.png"><meta property="og:image:width" content="1536"><meta property="og:image:height" content="1024"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{html.escape(row['title'],quote=True)}"><meta name="twitter:description" content="{html.escape(desc,quote=True)}"><meta name="twitter:image" content="{BASE}assets/suay-device-landing.png"><link rel="icon" type="image/svg+xml" href="{prefix}assets/suay-network.svg"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap"><link rel="stylesheet" href="{prefix}style.css"><link rel="stylesheet" href="{prefix}metrics.css"><script type="application/ld+json">{data}</script><script defer src="{prefix}language-menu.js"></script><script defer src="{prefix}metrics.js"></script>'''
        head+=f'<script defer src="{prefix}anatomy.js"></script>'
        if code=='en': head+='<script defer src="./main.js"></script>'
        output=body.replace('<!-- SEO_HEAD -->',head)
        path=ROOT/'landing'/('index.html' if code=='en' else code+'/index.html')
        path.parent.mkdir(exist_ok=True);path.write_text(output,encoding='utf-8')
    ns='http://www.sitemaps.org/schemas/sitemap/0.9';xhtml='http://www.w3.org/1999/xhtml'
    ET.register_namespace('',ns);ET.register_namespace('xhtml',xhtml)
    sitemap=ET.Element('{'+ns+'}urlset')
    for code in LOCALES:
        node=ET.SubElement(sitemap,'{'+ns+'}url');ET.SubElement(node,'{'+ns+'}loc').text=url(code);ET.SubElement(node,'{'+ns+'}lastmod').text='2026-10-19'
        for lang in [*LOCALES,'x-default']:ET.SubElement(node,'{'+xhtml+'}link',{'rel':'alternate','hreflang':lang,'href':url('en' if lang=='x-default' else lang)})
    ET.ElementTree(sitemap).write(ROOT/'landing/sitemap.xml',encoding='utf-8',xml_declaration=True)
    path=ROOT/'deploy/nginx-suay-snippet.conf';config=path.read_text();config=re.sub(r"script-src 'self'(?: 'sha256-[^']+')*;", "script-src 'self' "+' '.join("'"+h+"'" for h in hashes)+';',config);path.write_text(config)
    path=ROOT/'deploy/indexnow.json';indexnow=json.loads(path.read_text());indexnow['urlList']=[url(code) for code in LOCALES];path.write_text(json.dumps(indexnow,indent=2)+'\n')
    print('Built',len(LOCALES),'language pages, sitemap alternates and matching CSP hashes')


if __name__=='__main__':main()
