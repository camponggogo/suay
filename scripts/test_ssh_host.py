import importlib.util
import socket
from pathlib import Path

import paramiko

ROOT = Path('D:/Projects/Petals_Distributed_Inference')
spec = importlib.util.spec_from_file_location('deploy_landing', ROOT / 'deploy' / 'deploy_landing.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
config = module.settings()

host = config['HOSTINGER_SSH_SERVER']
user = config['HOSTINGER_SSH_USER']
secret = config['HOSTINGER_SSH_PASSWORD']

for attempt in (1, 2):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, password=secret, timeout=25, banner_timeout=25, auth_timeout=25)
        stdin, stdout, stderr = client.exec_command('hostname; uptime', timeout=30)
        print('OK attempt', attempt, stdout.read().decode().strip().replace('\n', ' | '))
        client.close()
        break
    except paramiko.AuthenticationException as error:
        print('attempt', attempt, 'auth failed:', error)
    except Exception as error:
        print('attempt', attempt, type(error).__name__, str(error)[:160])
