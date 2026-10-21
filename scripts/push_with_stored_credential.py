"""Push the current branch using the GitHub credential stored for the camponggogo account.

The token is read from Windows Credential Manager and handed to git through a temporary
askpass script; it is never printed and never written into the repository config.

    python scripts/push_with_stored_credential.py --target "GitHub - https://api.github.com/camponggogo" --user camponggogo
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import sys
from pathlib import Path

CRED_TYPE_GENERIC = 1


class Credential(ctypes.Structure):
    _fields_ = [
        ('Flags', wt.DWORD),
        ('Type', wt.DWORD),
        ('TargetName', wt.LPWSTR),
        ('Comment', wt.LPWSTR),
        ('LastWritten', wt.FILETIME),
        ('CredentialBlobSize', wt.DWORD),
        ('CredentialBlob', ctypes.POINTER(ctypes.c_char)),
        ('Persist', wt.DWORD),
        ('AttributeCount', wt.DWORD),
        ('Attributes', ctypes.c_void_p),
        ('TargetAlias', wt.LPWSTR),
        ('UserName', wt.LPWSTR),
    ]


def read_credential(target):
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    pointer = ctypes.POINTER(Credential)()
    if not advapi.CredReadW(ctypes.c_wchar_p(target), CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        item = pointer.contents
        blob = ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize)
        return blob.decode('utf-16-le').rstrip('\x00'), item.UserName
    finally:
        advapi.CredFree(pointer)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', default='GitHub - https://api.github.com/camponggogo')
    parser.add_argument('--user', default='camponggogo')
    parser.add_argument('--remote', default='origin')
    parser.add_argument('--branch', default='main')
    args = parser.parse_args()

    token, stored_user = read_credential(args.target)
    if not token:
        sys.exit('credential is empty')
    print(f'credential found: user={stored_user or args.user} length={len(token)} kind={token[:4]}…')

    workspace = Path(__file__).resolve().parents[1]
    askpass = workspace / '.zwork' / 'askpass.cmd'
    askpass.parent.mkdir(parents=True, exist_ok=True)
    askpass.write_text(
        '@echo off\r\n'
        'echo %1 | findstr /I "username" >nul && (echo %SUAY_GIT_USER% & exit /b 0)\r\n'
        'echo %SUAY_GIT_TOKEN%\r\n',
        encoding='utf-8')

    environment = dict(os.environ)
    environment['SUAY_GIT_TOKEN'] = token
    environment['SUAY_GIT_USER'] = args.user
    environment['GIT_TERMINAL_PROMPT'] = '0'
    environment['GCM_INTERACTIVE'] = 'never'

    command = ['git', '-c', f'core.askPass={askpass}', 'push', args.remote, args.branch, '--progress']
    result = subprocess.run(command, cwd=workspace, env=environment, capture_output=True, text=True)
    output = (result.stdout + result.stderr).replace(token, '***')
    print(output[-1500:])
    print('exit', result.returncode)
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
