"""Encrypted username and password verifier; no plaintext credential file."""
import hashlib
import getpass
import hmac
import json
import os
from pathlib import Path
import secrets
import sys

from cryptography.fernet import Fernet


def password_hash(value):
    salt = secrets.token_hex(16)
    return salt + ':' + hashlib.pbkdf2_hmac('sha256', value.encode(), salt.encode(), 600000).hex()


def password_matches(value, stored):
    salt, expected = stored.split(':')
    actual = hashlib.pbkdf2_hmac('sha256', value.encode(), salt.encode(), 600000).hex()
    return hmac.compare_digest(expected, actual)


def save(directory, username, password, must_change=True):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    keyfile = directory / 'username.key'
    if not keyfile.exists():
        keyfile.write_bytes(Fernet.generate_key())
        keyfile.chmod(0o600)
    encrypted = Fernet(keyfile.read_bytes()).encrypt(username.encode()).decode()
    content = f'ADMIN_USERNAME_ENCRYPTED={encrypted}\nADMIN_PASSWORD_HASH={password_hash(password)}\nADMIN_MUST_CHANGE={int(must_change)}\n'
    tmp = directory / '.env.next'
    descriptor = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
        handle.write(content)
    os.replace(tmp, directory / '.env')
    (directory / '.env').chmod(0o600)


def load(directory):
    directory = Path(directory)
    values = dict(line.split('=', 1) for line in (directory / '.env').read_text().splitlines() if '=' in line)
    username = Fernet((directory / 'username.key').read_bytes()).decrypt(values['ADMIN_USERNAME_ENCRYPTED'].encode()).decode()
    return username, values['ADMIN_PASSWORD_HASH'], values.get('ADMIN_MUST_CHANGE') == '1'


if __name__ == '__main__':
    print('Provide initial credential JSON on stdin; secrets will not be printed.', flush=True)
    data = ({'username': input('Username: '), 'password': getpass.getpass('Password: ')}
            if sys.stdin.isatty() else json.loads(sys.stdin.readline()))
    directory = Path(sys.argv[1])
    if (directory / '.env').exists():
        raise SystemExit('Credential file exists; refusing to overwrite')
    if len(data['password']) < 10:
        raise SystemExit('Initial password must be at least 10 characters')
    save(directory, data['username'], data['password'])
    print('Encrypted username and password hash created. First-login rotation required.')
