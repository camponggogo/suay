"""Inspect stored GitHub credentials without revealing them: target, user, length, prefix."""
import ctypes
import ctypes.wintypes as wt

CRED_TYPE_GENERIC = 1


class Credential(ctypes.Structure):
    _fields_ = [
        ('Flags', wt.DWORD), ('Type', wt.DWORD), ('TargetName', wt.LPWSTR), ('Comment', wt.LPWSTR),
        ('LastWritten', wt.FILETIME), ('CredentialBlobSize', wt.DWORD),
        ('CredentialBlob', ctypes.POINTER(ctypes.c_char)), ('Persist', wt.DWORD),
        ('AttributeCount', wt.DWORD), ('Attributes', ctypes.c_void_p), ('TargetAlias', wt.LPWSTR),
        ('UserName', wt.LPWSTR),
    ]


def read(target):
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    pointer = ctypes.POINTER(Credential)()
    if not advapi.CredReadW(ctypes.c_wchar_p(target), CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)):
        return None
    try:
        item = pointer.contents
        blob = ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize)
        text = blob.decode('utf-16-le', errors='ignore').rstrip('\x00')
        return item.UserName, text
    finally:
        advapi.CredFree(pointer)


for target in ('git:https://github.com', 'git:https://campong-hot@github.com',
               'GitHub - https://api.github.com/camponggogo'):
    entry = read(target)
    if not entry:
        print(f'{target}: <none>')
        continue
    user, secret = entry
    printable = all(32 <= ord(c) < 127 for c in secret)
    print(f'{target}: user={user} length={len(secret)} printable={printable} prefix={secret[:4]!r}')
