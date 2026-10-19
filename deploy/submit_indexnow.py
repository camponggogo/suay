"""Notify participating search engines about changed SUAY URLs, not guarantee indexing.

The verification key is intentionally public, not an authentication secret.
"""
import json
from pathlib import Path
from urllib.parse import urlparse
import urllib.request


def main():
    data = json.loads(Path(__file__).with_name('indexnow.json').read_text())
    prefix = 'https://campong.online/projects/suay/'
    if data['host'] != 'campong.online' or not data['keyLocation'].startswith(prefix):
        raise ValueError('Unexpected IndexNow host or key location')
    for url in data['urlList']:
        if not url.startswith(prefix) or urlparse(url).hostname != data['host']:
            raise ValueError('Only SUAY public URLs may be submitted')
    with urllib.request.urlopen(data['keyLocation'], timeout=20) as response:
        if response.read().decode().strip() != data['key']:
            raise ValueError('Published IndexNow key does not match')
    request = urllib.request.Request('https://api.indexnow.org/indexnow',
                                     data=json.dumps(data).encode(),
                                     headers={'Content-Type': 'application/json; charset=utf-8',
                                              'User-Agent': 'SUAY-site-update'}, method='POST')
    with urllib.request.urlopen(request, timeout=30) as response:
        print('IndexNow HTTP status:', response.status)
        print('Submitted URLs:', len(data['urlList']))
        print('Accepted notification only; crawl, indexing and ranking are not guaranteed.')


if __name__ == '__main__':
    main()
