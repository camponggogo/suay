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
    'anatomy/mesh.html',
    'anatomy/mesh.png',
    'anatomy/pasadhi-install-fig.png',
    'anatomy/pasadhi-install.html',
    'anatomy/pasadhi-install.png',
    'anatomy/pasadhi-system-fig.png',
    'anatomy/pasadhi-system.html',
    'anatomy/pasadhi-system.png',
    'anatomy/pool.html',
    'anatomy/pool.png',
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
    'story.html',
    'style.css',
    'th/index.html',
    'th/story.html',
    'theme.css',
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
            for name in ('PASADHI-0.1.0-win64-portable.zip', 'PASADHI-0.1.0-source.zip'):
                print(run(f"curl --fail --silent --show-error --max-time 20 -o /dev/null "
                          f"-w '{name}: %{{http_code}} %{{size_download}}\\n' "
                          f"https://campong.online/projects/pasadhi/download/{name}").strip())
            print('Release:', release)
    finally:
        client.close()


if __name__ == '__main__':
    main()
