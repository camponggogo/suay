from pathlib import Path

for name in ('pasadhi/app/group.py', 'pasadhi/app/impact.py'):
    p = Path(name)
    t = p.read_text(encoding='utf-8')
    if 'sys.path.insert' in t:
        print(name, 'has bootstrap')
        continue
    anchor = 'from dataclasses import dataclass, field, asdict' if 'field, asdict' in t else 'from dataclasses import dataclass'
    bootstrap = ('import sys\nfrom pathlib import Path\n\n'
                 "if __package__ in (None, ''):\n    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))\n\n")
    t = t.replace(anchor, bootstrap + anchor, 1)
    p.write_text(t, encoding='utf-8')
    print(name, 'patched')
