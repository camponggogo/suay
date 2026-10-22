import importlib.util
from pathlib import Path

import paramiko

ROOT = Path('D:/Projects/Petals_Distributed_Inference')
spec = importlib.util.spec_from_file_location('deploy_landing', ROOT / 'deploy' / 'deploy_landing.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
config = module.settings()
host, user = config['HOSTINGER_SSH_SERVER'], config['HOSTINGER_SSH_USER']

keys = ['sshhostinger', 'ssh_hostinger', 'ssh_hostinger_deploy', 'id_ed25519']
for name in keys:
    path = Path.home() / '.ssh' / name
    if not path.exists():
        print(name, 'missing')
        continue
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, key_filename=str(path), timeout=20,
                       allow_agent=False, look_for_keys=False)
        stdin, stdout, stderr = client.exec_command('hostname', timeout=20)
        print(name, 'OK ->', stdout.read().decode().strip())
        client.close()
    except Exception as error:
        print(name, type(error).__name__, str(error)[:90])
