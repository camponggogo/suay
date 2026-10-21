"""List stored credentials related to GitHub (target, user, length, prefix) — no secrets printed."""
import ctypes
import ctypes.wintypes as wt

CRED_TYPE_GENERIC = 1
CRED_ENUMERATE_ALL = 0x1


class Credential(ctypes.Structure):
    _fields_ = [
        ('Flags', wt.DWORD), ('Type', wt.DWORD), ('TargetName', wt.LPWSTR), ('Comment', wt.LPWSTR),
        ('LastWritten', wt.FILETIME), ('CredentialBlobSize', wt.DWORD),
        ('CredentialBlob', ctypes.POINTER(ctypes.c_char)), ('Persist', wt.DWORD),
        ('AttributeCount', wt.DWORD), ('Attributes', ctypes.c_void_p), ('TargetAlias', wt.LPWSTR),
        ('UserName', wt.LPWSTR),
    ]


advapi = ctypes.WinDLL('advapi32', use_last_error=True)
count = wt.DWORD(0)
pointer = ctypes.POINTER(ctypes.POINTER(Credential))()
ok = advapi.CredEnumerateW(None, CRED_ENUMERATE_ALL, ctypes.byref(count), ctypes.byref(pointer))
if not ok:
    raise ctypes.WinError(ctypes.get_last_error())

for index in range(count.value):
    item = pointer[index].contents
    target = item.TargetName or ''
    user = item.UserName or ''
    if 'github' not in target.lower() and 'github' not in user.lower() and 'campong' not in user.lower():
        continue
    blob = ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize)
    secret = blob.decode('utf-16-le', errors='ignore').rstrip('\x00')
    printable = all(32 <= ord(c) < 127 for c in secret)
    print(f'target={target!r} user={user!r} type={item.Type} length={len(secret)} printable={printable} prefix={secret[:4]!r}')
advapi.CredFree(pointer)
