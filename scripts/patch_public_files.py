from pathlib import Path

p = Path('deploy/deploy_pasadhi.py')
t = p.read_text(encoding='utf-8')
needle = "PUBLIC_FILES = ('index.html', 'th/index.html', 'style.css', 'sitemap.xml')"
replacement = "PUBLIC_FILES = ('index.html', 'th/index.html', 'style.css', 'sitemap.xml', 'robots.txt')"
if needle in t:
    t = t.replace(needle, replacement)
    p.write_text(t, encoding='utf-8')
    print('PUBLIC_FILES updated')
else:
    print('pattern not found; current line:')
    for line in t.splitlines():
        if 'PUBLIC_FILES' in line:
            print(line)
