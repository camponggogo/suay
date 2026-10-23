"""Deploy the PASADHI landing page to the existing Nginx host.

Dry-run by default; --apply uploads, adds the /projects/pasadhi/ location, creates the pasadhi.tech vhost,
reloads Nginx and rolls back on any failure.

    python deploy/deploy_pasadhi.py [--apply]
"""
from __future__ import annotations

import argparse
import json
import posixpath
import shlex
import stat
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'landing-pasadhi'
VHOST = '/etc/nginx/sites-available/campong.online'
SNIPPET = '/etc/nginx/snippets/campong-pasadhi.conf'
SITE = '/etc/nginx/sites-available/pasadhi.tech'
ENABLED = '/etc/nginx/sites-enabled/pasadhi.tech'
BASE = '/opt/pasadhi'
PUBLIC_FILES = (
    'brand/logo-light-transparent.png',
    'download/PASADHI-0.1.0-android-termux.zip',
    'download/PASADHI-0.1.0-linux.tar.gz',
    'download/PASADHI-0.1.0-macos.tar.gz',
    'download/PASADHI-0.1.0-source.zip',
    'download/PASADHI-0.1.0-win64-portable.zip',
    'download/PASADHI-0.1.0-windows.zip',
    'download/PASADHI-full-paper.pdf',
    'download/PASADHI-pitch-2026.pptx',
    'download/PASADHI-solution.pdf',
    'download/SHA256SUMS.txt',
    'download/latest/PASADHI-android-termux.zip',
    'download/latest/PASADHI-linux.tar.gz',
    'download/latest/PASADHI-macos.tar.gz',
    'download/latest/PASADHI-source.zip',
    'download/latest/PASADHI-windows.zip',
    'download/latest/SHA256SUMS.txt',
    'download/latest/release.json',
    'download/release.json',
    'download/v0.1.0/PASADHI-0.1.0-android-termux.zip',
    'download/v0.1.0/PASADHI-0.1.0-linux.tar.gz',
    'download/v0.1.0/PASADHI-0.1.0-macos.tar.gz',
    'download/v0.1.0/PASADHI-0.1.0-source.zip',
    'download/v0.1.0/PASADHI-0.1.0-windows.zip',
    'download/v0.1.0/SHA256SUMS.txt',
    'download/v0.1.0/release.json',
    'fonts/DejaVu-LICENSE.txt',
    'fonts/DejaVuSans.ttf',
    'fonts/GPL-2.0.txt',
    'fonts/NotoSans.ttf',
    'fonts/NotoSansMono.ttf',
    'fonts/NotoSansThai.ttf',
    'fonts/NotoSerif.ttf',
    'fonts/Nunito.ttf',
    'fonts/README.md',
    'fonts/THSarabunNew-Bold.ttf',
    'fonts/THSarabunNew-BoldItalic.ttf',
    'fonts/THSarabunNew-Italic.ttf',
    'fonts/THSarabunNew-LICENSE.txt',
    'fonts/THSarabunNew-original.zip',
    'fonts/THSarabunNew.ttf',
    'fonts/fonts.css',
    'fonts/notosans-OFL.txt',
    'fonts/notosansmono-OFL.txt',
    'fonts/notosansthai-OFL.txt',
    'fonts/notoserif-OFL.txt',
    'fonts/nunito-OFL.txt',
    'fonts/sources.json',
    'index.html',
    'motion.js',
    'pitch/assets/compute-background.png',
    'pitch/assets/logo.png',
    'pitch/assets/system.png',
    'pitch/deck.json',
    'pitch/financial-plan.json',
    'pitch/funding-plan.md',
    'pitch/index.html',
    'pitch/present.css',
    'pitch/present.js',
    'robots.txt',
    'sitemap.xml',
    'style.css',
    'th/index.html',
    'theme.css',
)
MARKER = 'PASADHI'


def settings() -> dict:
    """Reuse the exact loader used by the SUAY deployment (BOM-safe, env overrides)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location('deploy_landing', ROOT / 'deploy' / 'deploy_landing.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.settings()


def add_include(text: str) -> str:
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
    return text[:end] + line + '\n' + text[end:]


SNIPPET_BODY = """# PASADHI landing (added by deploy_pasadhi.py)
location ^~ /projects/pasadhi/ {
    alias /opt/pasadhi/current/;
    index index.html;
    try_files $uri $uri/ /projects/pasadhi/index.html;
}
"""

SITE_BODY = """server {
    listen 80;
    listen [::]:80;
    server_name pasadhi.tech www.pasadhi.tech;
    root /opt/pasadhi/current;
    index index.html;
    location / { try_files $uri $uri/ /index.html; }
    location = /sitemap.xml { alias /opt/pasadhi/current/sitemap.xml; }
}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    config = settings()
    host = config.get('HOSTINGER_SSH_SERVER')
    user = config.get('HOSTINGER_SSH_USER', 'root')
    secret = config.get('HOSTINGER_SSH_PASSWORD')
    if not host or not secret:
        raise SystemExit('SSH credentials missing in deploy/.env')

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key_path = Path.home() / '.ssh' / 'ssh_hostinger_deploy'
    if key_path.exists():
        client.connect(host, username=user, key_filename=str(key_path), timeout=30,
                       allow_agent=False, look_for_keys=False)
    else:
        client.connect(host, username=user, password=secret, timeout=30)

    def run(command: str) -> str:
        stdin, stdout, stderr = client.exec_command(command, timeout=120)
        out = stdout.read().decode(errors='replace')
        err = stderr.read().decode(errors='replace')
        code = stdout.channel.recv_exit_status()
        if code != 0:
            raise RuntimeError(f'command failed ({code}): {command}\n{err[-400:]}')
        return out

    try:
        with client.open_sftp() as sftp:
            def read(path):
                with sftp.open(path, 'rb') as handle:
                    return handle.read()

            def exists(path):
                try:
                    return sftp.lstat(path)
                except FileNotFoundError:
                    return None

            def write(path, data):
                with sftp.open(path, 'wb') as handle:
                    handle.write(data)
                sftp.chmod(path, 0o644)

            original = read(VHOST)
            revised = add_include(original.decode()).encode()
            previous_snippet = read(SNIPPET) if exists(SNIPPET) else None
            previous_site = read(SITE) if exists(SITE) else None

            link = BASE + '/current'
            info = exists(link)
            if info and not stat.S_ISLNK(info.st_mode):
                raise ValueError('/opt/pasadhi/current exists and is not a symlink; refusing')
            previous_link = sftp.readlink(link) if info else None

            print(run('nginx -t').strip())
            print(json.dumps({'domain': 'pasadhi.tech',
                              'path': '/projects/pasadhi/',
                              'files': list(PUBLIC_FILES),
                              'vhost_include': revised != original,
                              'mode': 'apply' if args.apply else 'dry-run'}, indent=2))
            if not args.apply:
                return

            release_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            release = f'{BASE}/releases/{release_id}'
            backup = f'{BASE}/backups/{release_id}'
            directories = {posixpath.dirname(posixpath.join(release, name)) for name in PUBLIC_FILES}
            run('mkdir -p ' + ' '.join(shlex.quote(d) for d in sorted(directories | {backup})))
            write(backup + '/vhost.conf', original)
            if previous_snippet is not None:
                write(backup + '/snippet.conf', previous_snippet)
            if previous_site is not None:
                write(backup + '/site.conf', previous_site)
            write(backup + '/previous.json', json.dumps({'current': previous_link}).encode())

            for name in PUBLIC_FILES:
                sftp.putfo(BytesIO((SOURCE / name).read_bytes()), posixpath.join(release, name))
                sftp.chmod(posixpath.join(release, name), 0o644)

            activated = False
            try:
                sftp.symlink(release, link + '.next-' + release_id)
                run('mv -Tf ' + shlex.quote(link + '.next-' + release_id) + ' ' + shlex.quote(link))
                activated = True
                write(SNIPPET, SNIPPET_BODY.encode())
                write(VHOST, revised)
                write(SITE, SITE_BODY.encode())
                if not exists(ENABLED):
                    run('ln -s ' + shlex.quote(SITE) + ' ' + shlex.quote(ENABLED))
                print(run('nginx -t').strip())
                print(run('systemctl reload nginx').strip())
                print(run("curl --fail --silent --show-error --max-time 20 "
                          "https://campong.online/projects/pasadhi/ | grep -F 'PASADHI' >/dev/null && "
                          "echo 'path check: passed'").strip())
                print(run("curl --fail --silent --show-error --max-time 20 -H 'Host: pasadhi.tech' "
                          "http://127.0.0.1/ | grep -F 'PASADHI' >/dev/null && "
                          "echo 'vhost check: passed'").strip())
                print('Published: https://campong.online/projects/pasadhi/')
                print('Release:', release)
                print('Rollback backup:', backup)
            except Exception:
                write(VHOST, original)
                write(SITE, previous_site if previous_site is not None else SITE_BODY.encode())
                if previous_snippet is None:
                    if exists(SNIPPET):
                        sftp.remove(SNIPPET)
                else:
                    write(SNIPPET, previous_snippet)
                if activated and previous_link:
                    sftp.symlink(previous_link, link + '.rb-' + release_id)
                    run('mv -Tf ' + shlex.quote(link + '.rb-' + release_id) + ' ' + shlex.quote(link))
                run('nginx -t && systemctl reload nginx')
                print('Deployment failed; previous Nginx state restored.')
                raise
    finally:
        client.close()


if __name__ == '__main__':
    main()
