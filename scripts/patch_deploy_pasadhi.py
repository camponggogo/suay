from pathlib import Path

p = Path('deploy/deploy_pasadhi.py')
t = p.read_text(encoding='utf-8')

old_settings = '''def settings() -> dict:
    result = {}
    envfile = ROOT / 'deploy' / '.env'
    if envfile.exists():
        for line in envfile.read_text(encoding='utf-8', errors='ignore').splitlines():
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                result[key.strip()] = value.strip().strip('"').strip("'")
    return result'''
new_settings = '''def settings() -> dict:
    """Reuse the exact loader used by the SUAY deployment (BOM-safe, env overrides)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location('deploy_landing', ROOT / 'deploy' / 'deploy_landing.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.settings()'''

if old_settings in t:
    t = t.replace(old_settings, new_settings)
else:
    print('settings block not found (already patched?)')

t = t.replace("password = config.get('HOSTINGER_SSH_PASSWORD')", "secret = config.get('HOSTINGER_SSH_PASSWORD')")
t = t.replace('if not host or not password:', 'if not host or not secret:')
t = t.replace('client.connect(host, username=user, password=password, timeout=30)',
              'client.connect(host, username=user, password=secret, timeout=30)')

p.write_text(t, encoding='utf-8')
print('patched; uses secret var:', 'password=secret' in t)
