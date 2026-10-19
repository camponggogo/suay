"""Install the landing-only analytics service; private config never enters the web release."""
from datetime import datetime, timezone
from pathlib import Path
import shlex

import paramiko
from deploy_landing import ROOT, settings


def main():
    config=settings()
    private=ROOT/'.local/visitor/private'
    if not all((private/name).is_file() for name in ['.env','username.key']):
        raise SystemExit('Initialize ignored .local/visitor/private credentials first')
    source=ROOT/'versions/python/visitor_analytics'
    files=['__init__.py','app.py','credentials.py','requirements.txt','static/index.html','static/style.css','static/app.js']
    release='/opt/suay-visitor/releases/'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    client=paramiko.SSHClient();client.load_system_host_keys()
    client.connect(config['HOSTINGER_SSH_SERVER'],username=config['HOSTINGER_SSH_USER'],password=config['HOSTINGER_SSH_PASSWORD'],timeout=20,look_for_keys=False,allow_agent=False)
    try:
        def run(command):
            _,out,err=client.exec_command(command,timeout=180)
            output=out.read().decode();error=err.read().decode()
            if out.channel.recv_exit_status():raise RuntimeError(error or output)
            return output+error
        print(run("id suay-visitor >/dev/null 2>&1 || useradd --system --home-dir /var/lib/suay-visitor --shell /usr/sbin/nologin suay-visitor").strip())
        run('mkdir -p '+shlex.quote(release+'/visitor_analytics/static')+' /var/lib/suay-visitor/private; chmod 700 /var/lib/suay-visitor /var/lib/suay-visitor/private')
        with client.open_sftp() as sftp:
            for name in files:
                sftp.put(str(source/name),release+'/visitor_analytics/'+name)
                sftp.chmod(release+'/visitor_analytics/'+name,0o644)
            for name in ['.env','username.key']:
                target='/var/lib/suay-visitor/private/'+name
                try:sftp.stat(target)
                except FileNotFoundError:
                    sftp.put(str(private/name),target);sftp.chmod(target,0o600)
            unit='''[Unit]
Description=SUAY public landing analytics (separate from coordinator)
After=network.target
[Service]
User=suay-visitor
Group=suay-visitor
WorkingDirectory=/opt/suay-visitor/current
Environment=SUAY_VISITOR_STATE=/var/lib/suay-visitor
Environment=SUAY_VISITOR_ORIGIN=https://campong.online
ExecStart=/opt/suay-visitor/venv/bin/python -m uvicorn visitor_analytics.app:create_app --factory --host 127.0.0.1 --port 8095 --no-access-log --no-proxy-headers
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/var/lib/suay-visitor
UMask=0077
MemoryMax=256M
CPUQuota=30%
[Install]
WantedBy=multi-user.target
'''
            with sftp.open('/etc/systemd/system/suay-visitor.service','w') as handle:handle.write(unit)
        run('chown -R suay-visitor:suay-visitor /var/lib/suay-visitor')
        print(run('python3 -m ensurepip --version >/dev/null 2>&1 || (apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv)').strip())
        print(run('/opt/suay-visitor/venv/bin/python -m pip --version >/dev/null 2>&1 || python3 -m venv /opt/suay-visitor/venv').strip())
        print(run('/opt/suay-visitor/venv/bin/python -m pip install --disable-pip-version-check -q -r '+shlex.quote(release+'/visitor_analytics/requirements.txt')).strip())
        run('ln -sfn '+shlex.quote(release)+' /opt/suay-visitor/current.next; mv -Tf /opt/suay-visitor/current.next /opt/suay-visitor/current')
        print(run('systemctl daemon-reload; systemctl enable --now suay-visitor; systemctl restart suay-visitor').strip())
        print(run("for attempt in 1 2 3 4 5; do curl --fail --silent http://127.0.0.1:8095/health && exit 0; sleep 1; done; systemctl status suay-visitor --no-pager; exit 1").strip())
        print('Visitor analytics is loopback-only on 8095. Credentials kept outside the public site.')
    finally:client.close()


if __name__=='__main__':main()
