"""Deploy only SUAY's static landing page through the existing host Nginx.

Dry-run by default. SSH credentials come from process environment or ignored .env.
The server's host key must already be trusted in ~/.ssh/known_hosts.
"""
import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import posixpath
import shlex
import stat

ROOT = Path(__file__).resolve().parents[1]
VHOST = '/etc/nginx/sites-available/campong.online'
SNIPPET = '/etc/nginx/snippets/campong-suay.conf'
INCLUDE = '    include /etc/nginx/snippets/campong-suay.conf;'
BASE = '/opt/suay'
PUBLIC_FILES = ('index.html', 'style.css', 'main.js', 'assets/suay-network.svg',
                'assets/suay-logo.svg', 'assets/suay-device-landing.jpg')


def settings():
    result = {}
    envfile = ROOT / 'deploy' / '.env'
    if envfile.exists():
        for line in envfile.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                result[key.strip()] = value.strip().strip('"').strip("'")
    for key in ('HOSTINGER_SSH_SERVER', 'HOSTINGER_SSH_USER', 'HOSTINGER_SSH_PASSWORD'):
        if key in os.environ:
            result[key] = os.environ[key]
        if not result.get(key):
            raise ValueError(f'Missing {key}; set environment or ignored deploy/.env')
    return result


def add_include(text):
    # Only the exact non-www HTTPS server, preserving all root/project locations.
    needle = '    server_name campong.online;'
    if text.count(needle) != 1:
        raise ValueError('Expected one exact campong.online HTTPS server; refusing automatic edit')
    position = text.index(needle)
    start = text.rfind('server {', 0, position)
    if start < 0:
        raise ValueError('Cannot find target server block')
    depth, end = 0, None
    for i in range(text.index('{', start), len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                end = i
                break
    if end is None or 'listen 443' not in text[start:end]:
        raise ValueError('Expected HTTPS server block')
    if INCLUDE.strip() in text[start:end]:
        return text
    if '/projects/suay' in text:
        raise ValueError('Existing SUAY location needs manual review')
    return text[:end] + INCLUDE + '\n' + text[end:]


def main():
    import paramiko
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Upload, validate and reload Nginx')
    args = parser.parse_args()
    for name in PUBLIC_FILES:
        path = ROOT / 'landing' / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f'Missing or symlinked public asset: {name}')
    config = settings()
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        client.connect(config['HOSTINGER_SSH_SERVER'], username=config['HOSTINGER_SSH_USER'],
                       password=config['HOSTINGER_SSH_PASSWORD'], timeout=20,
                       look_for_keys=False, allow_agent=False)

        def run(command):
            _, stdout, stderr = client.exec_command(command, timeout=45)
            out, err = stdout.read().decode(), stderr.read().decode()
            status = stdout.channel.recv_exit_status()
            if status:
                raise RuntimeError(f'Remote command failed ({status}): {err or out}')
            return out + err

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
            revised = add_include(original.decode())
            previous_snippet = read(SNIPPET) if exists(SNIPPET) else None
            link = BASE + '/current'
            info = exists(link)
            if info and not stat.S_ISLNK(info.st_mode):
                raise ValueError('Existing /opt/suay/current is not a symlink; refusing to replace')
            previous_link = sftp.readlink(link) if info else None
            print(run('nginx -t').strip())
            plan = dict(domain='campong.online', public_path='/projects/suay/',
                        files=list(PUBLIC_FILES), modify_vhost=revised != original.decode(),
                        mode='apply' if args.apply else 'dry-run', control_plane_published=False)
            print(json.dumps(plan, indent=2))
            if not args.apply:
                return

            release_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            release = BASE + '/releases/' + release_id
            backup = BASE + '/backups/' + release_id
            run('mkdir -p ' + shlex.quote(release + '/assets') + ' ' + shlex.quote(backup))
            write(backup + '/vhost.conf', original)
            if previous_snippet is not None:
                write(backup + '/snippet.conf', previous_snippet)
            write(backup + '/previous.json', json.dumps({'current': previous_link}).encode())
            # Only the explicit static allowlist is transferred; .env/control/db never enter the release.
            for name in PUBLIC_FILES:
                sftp.putfo(BytesIO((ROOT / 'landing' / name).read_bytes()), posixpath.join(release, name))
                sftp.chmod(posixpath.join(release, name), 0o644)
            activated = False
            try:
                sftp.symlink(release, link + '.next-' + release_id)
                run('mv -Tf ' + shlex.quote(link + '.next-' + release_id) + ' ' + shlex.quote(link))
                activated = True
                write(SNIPPET, (ROOT / 'deploy' / 'nginx-suay-snippet.conf').read_bytes())
                write(VHOST, revised.encode())
                print(run('nginx -t').strip())
                print(run('systemctl reload nginx').strip())
                print(run("curl --fail --silent --show-error --max-time 20 https://campong.online/projects/suay/ | grep -F 'Wake old' >/dev/null && echo 'SUAY public HTTPS check: passed'").strip())
                print(run("curl --fail --silent --show-error --max-time 20 -o /dev/null https://campong.online/ && echo 'Main website HTTPS check: passed'").strip())
                print('Published: https://campong.online/projects/suay/')
                print('Release:', release)
                print('Rollback backup:', backup)
            except Exception:
                write(VHOST, original)
                if previous_snippet is None:
                    if exists(SNIPPET):
                        sftp.remove(SNIPPET)
                else:
                    write(SNIPPET, previous_snippet)
                if activated:
                    if previous_link:
                        rollback_link = link + '.rollback-' + release_id
                        sftp.symlink(previous_link, rollback_link)
                        run('mv -Tf ' + shlex.quote(rollback_link) + ' ' + shlex.quote(link))
                    else:
                        sftp.remove(link)
                run('nginx -t && systemctl reload nginx')
                print('Deployment failed; restored previous Nginx configuration and release link.')
                raise
    finally:
        client.close()


if __name__ == '__main__':
    main()
