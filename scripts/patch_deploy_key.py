from pathlib import Path

p = Path('deploy/deploy_pasadhi.py')
t = p.read_text(encoding='utf-8')

# 1) key-based auth when the deploy key exists
old_connect = "    client.connect(host, username=user, password=secret, timeout=30)"
new_connect = """    key_path = Path.home() / '.ssh' / 'ssh_hostinger_deploy'
    if key_path.exists():
        client.connect(host, username=user, key_filename=str(key_path), timeout=30,
                       allow_agent=False, look_for_keys=False)
    else:
        client.connect(host, username=user, password=secret, timeout=30)"""
if old_connect in t:
    t = t.replace(old_connect, new_connect)

# 2) robust include insertion, copied from the SUAY deployer
old_inc_start = t.index('def add_include(text: str) -> str:')
old_inc_end = t.index('SNIPPET_BODY =')
new_inc = '''def add_include(text: str) -> str:
    """Insert the include inside the exact HTTPS server block, refusing guesswork."""
    needle = '    server_name campong.online;'
    if text.count(needle) != 1:
        raise ValueError('Expected one exact campong.online server; refusing to edit')
    position = text.index(needle)
    start = text.rfind('server {', 0, position)
    if start < 0:
        raise ValueError('Cannot find the server block')
    depth, end = 0, None
    for index in range(text.index('{', start), len(text)):
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                end = index
                break
    if end is None or 'listen 443' not in text[start:end]:
        raise ValueError('Expected an HTTPS server block')
    line = '    include ' + SNIPPET + ';'
    if line in text[start:end]:
        return text
    return text[:end] + line + '\\n' + text[end:]


'''
t = t[:old_inc_start] + new_inc + t[old_inc_end:]
p.write_text(t, encoding='utf-8')
print('patched deploy script')
