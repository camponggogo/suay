"""Deploy the PASADHI landing page and its isometric anatomy pages.

Key-based SSH only (no credential literal in this file). Adds the anatomy folder and keeps the same release
layout as the earlier deployer:

    python deploy/deploy_pasadhi_assets.py [--apply]
"""
from __future__ import annotations

import argparse
import posixpath
import shlex
import stat
from datetime import datetime, timezone
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'landing-pasadhi'
HOST = '187.52.120.204'
USER = 'root'
KEY = Path.home() / '.ssh' / 'ssh_hostinger_deploy'
BASE = '/opt/pasadhi'

FILES = (
    'index.html', 'th/index.html', 'style.css', 'sitemap.xml', 'robots.txt',
    'story.html', 'th/story.html', 'download/PASADHI-solution.pdf',
    'anatomy/pool.html', 'anatomy/mesh.html', 'anatomy/pool.png', 'anatomy/mesh.png',
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    missing = [name for name in FILES if not (SOURCE / name).exists()]
    if missing:
        raise SystemExit(f'missing source files: {missing}')

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, key_filename=str(KEY), timeout=30,
                   allow_agent=False, look_for_keys=False)

    def run(command: str) -> str:
        stdin, stdout, stderr = client.exec_command(command, timeout=180)
        out = stdout.read().decode(errors='replace')
        err = stderr.read().decode(errors='replace')
        code = stdout.channel.recv_exit_status()
        if code != 0:
            raise RuntimeError(f'{command}\n{err[-400:]}')
        return out

    try:
        with client.open_sftp() as sftp:
            link = f'{BASE}/current'
            info = None
            try:
                info = sftp.lstat(link)
            except FileNotFoundError:
                pass
            if info and not stat.S_ISLNK(info.st_mode):
                raise SystemExit('/opt/pasadhi/current is not a symlink')
            previous = sftp.readlink(link) if info else None

            print('plan:', {'files': len(FILES), 'target': BASE, 'mode': 'apply' if args.apply else 'dry-run'})
            if not args.apply:
                return

            release_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            release = f'{BASE}/releases/{release_id}'
            backup = f'{BASE}/backups/{release_id}'
            directories = {posixpath.dirname(posixpath.join(release, name)) for name in FILES}
            run('mkdir -p ' + ' '.join(shlex.quote(d) for d in sorted(directories | {backup})))
            with sftp.open(f'{backup}/previous.txt', 'w') as handle:
                handle.write(previous or '')

            for name in FILES:
                sftp.put(str(SOURCE / name), posixpath.join(release, name))
                sftp.chmod(posixpath.join(release, name), 0o644)

            staged = f'{link}.next-{release_id}'
            sftp.symlink(release, staged)
            run('mv -Tf ' + shlex.quote(staged) + ' ' + shlex.quote(link))
            print(run('nginx -t').strip())
            print(run('systemctl reload nginx').strip())
            print(run("curl --fail --silent --show-error --max-time 20 "
                      "https://campong.online/projects/pasadhi/anatomy/mesh.html | grep -F 'the office as one web' "
                      ">/dev/null && echo 'mesh page: passed'").strip())
            print(run("curl --fail --silent --show-error --max-time 20 -o /dev/null "
                      "-w 'mesh png: %{http_code} %{size_download}\\n' "
                      "https://campong.online/projects/pasadhi/anatomy/mesh.png").strip())
            print(run("curl --fail --silent --show-error --max-time 20 -o /dev/null "
                      "-w 'paper pdf: %{http_code} %{size_download}\\n' "
                      "https://campong.online/projects/pasadhi/download/PASADHI-solution.pdf").strip())
            print(run("curl --fail --silent --show-error --max-time 20 "
                      "https://campong.online/projects/pasadhi/story.html | grep -F 'Six measurements' >/dev/null "
                      "&& echo 'story page: passed'").strip())
            print('Release:', release)
    finally:
        client.close()


if __name__ == '__main__':
    main()
