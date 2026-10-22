import re
from pathlib import Path

text = Path('.zwork/dom.html').read_text(encoding='utf-8', errors='ignore')
title = re.search(r'<title>(.*?)</title>', text, re.S)
print('title:', title.group(1)[:200] if title else 'none')
index = text.find('id="scene"')
print('svg snippet:', text[index:index + 220].replace('\n', ' '))
print('polygons in dom:', text.count('<polygon'))
