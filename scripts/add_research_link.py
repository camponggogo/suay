"""Add the Research link to every landing page nav and the sitemap, once."""
from pathlib import Path

ROOT = Path('landing')
LINK = '<a href="{href}">Research</a>'
changed = []
for page in [ROOT / 'index.html', *sorted(ROOT.glob('*/index.html'))]:
    text = page.read_text(encoding='utf-8')
    if 'research.html' in text:
        continue
    href = '../research.html' if page.parent != ROOT else './research.html'
    anchor = '<a href="#installation">Install</a>'
    if anchor not in text:
        continue
    text = text.replace(anchor, anchor + LINK.format(href=href), 1)
    page.write_text(text, encoding='utf-8')
    changed.append(str(page))
print('nav updated:', len(changed))
for item in changed:
    print(' ', item)

sitemap = ROOT / 'sitemap.xml'
xml = sitemap.read_text(encoding='utf-8')
entry = ('  <url><loc>https://campong.online/projects/suay/research.html</loc>'
         '<lastmod>2026-10-21</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>\n')
if 'research.html' not in xml:
    xml = xml.replace('</urlset>', entry + '</urlset>')
    sitemap.write_text(xml, encoding='utf-8')
    print('sitemap updated')
else:
    print('sitemap already has research.html')
