import importlib.util
import os
from pathlib import Path

ROOT = Path('D:/Projects/Petals_Distributed_Inference')

spec = importlib.util.spec_from_file_location('deploy_landing', ROOT / 'deploy' / 'deploy_landing.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
config = module.settings()
print('host', config['HOSTINGER_SSH_SERVER'])
print('user', config['HOSTINGER_SSH_USER'])
print('password length', len(config['HOSTINGER_SSH_PASSWORD']))
