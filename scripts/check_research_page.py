import re

import httpx

response = httpx.get('https://campong.online/projects/suay/research.html', timeout=30, follow_redirects=True)
text = response.text
print('status', response.status_code, 'bytes', len(text))
print('title:', re.search(r'<title>(.*?)</title>', text).group(1))
print('timeline entries:', text.count('class="tl-item'))
first = re.search(r'<h3>(.*?)</h3>', text)
print('newest entry:', first.group(1) if first else 'none')
print('paper strip present:', 'White paper v1.1' in text)
print('old sections gone:', 'THE SIX NUMBERS THAT MATTER' not in text)
