"""Check generated landing links, discoverability data and deployment allowlist."""
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from deploy.deploy_landing import PUBLIC_FILES


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs=[];self.ids=set();self.json=[];self.text=[];self.structured=False;self.hidden=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.add(a['id'])
        for name in ('src','href'):
            if a.get(name):self.refs.append(a[name])
        if tag in ('script','style'):
            self.hidden+=1
            self.structured=tag=='script' and a.get('type')=='application/ld+json'
        if tag=='link' and a.get('rel')=='canonical':self.canonical=a['href']
    def handle_endtag(self,tag):
        if tag in ('script','style'):
            self.hidden=max(0,self.hidden-1);self.structured=False
    def handle_data(self,data):
        if self.structured:self.json.append(data)
        elif not self.hidden:self.text.append(data)


def check():
    locales=json.loads((ROOT/'site_content/locales.json').read_text(encoding='utf-8'))
    allowed=set(PUBLIC_FILES)
    csp=(ROOT/'deploy/nginx-suay-snippet.conf').read_text(encoding='utf-8')
    for name in allowed:assert (ROOT/'landing'/name).is_file(),name
    for code in locales:
        name='index.html' if code=='en' else code+'/index.html'
        source=(ROOT/'landing'/name).read_text(encoding='utf-8')
        page=Page();page.feed(source)
        assert page.canonical=='https://campong.online/projects/suay/'+('' if code=='en' else code+'/'),name
        assert len(re.findall(r'rel="alternate" hreflang=',source))==13,name
        assert 'installation' in page.ids and all('install-'+r in page.ids for r in ('gateway','worker','client','rust')),name
        for ref in page.refs:
            url=urlsplit(ref)
            if url.scheme or url.netloc:continue
            if not url.path:
                if url.fragment:assert unquote(url.fragment) in page.ids,(name,ref)
                continue
            target=(ROOT/'landing'/name).parent/unquote(url.path)
            if target.is_dir():target=target/'index.html'
            target=target.resolve()
            assert target.is_relative_to((ROOT/'landing').resolve()) and target.is_file(),(name,ref)
            assert target.relative_to(ROOT/'landing').as_posix() in allowed,(name,ref,'not deployable')
        visible=' '.join(' '.join(page.text).split())
        assert len(page.json)==1,name
        graph=json.loads(page.json[0])['@graph']
        faq=next(x for x in graph if x['@type']=='FAQPage')
        for q in faq['mainEntity']:
            assert ' '.join(q['name'].split()) in visible,(name,q['name'])
            assert ' '.join(q['acceptedAnswer']['text'].split()) in visible,(name,q['name'],'answer mismatch')
        digest='sha256-'+base64.b64encode(hashlib.sha256(page.json[0].encode()).digest()).decode()
        assert digest in csp,(name,'CSP mismatch')
    for svg in (ROOT/'landing/assets/install').glob('*.svg'):ET.parse(svg)
    sitemap=ET.parse(ROOT/'landing/sitemap.xml')
    assert len(sitemap.getroot())==len(locales)
    print(f'PASS: {len(locales)} pages; links, deployment assets, FAQ parity, canonical/hreflang, SVG and CSP')


if __name__=='__main__':check()
