from pathlib import Path

p = Path('pasadhi/app/budget.py')
t = p.read_text(encoding='utf-8')
if 'sys.path.insert' not in t:
    t = t.replace('from dataclasses import dataclass, asdict',
                  'import sys\nfrom dataclasses import dataclass, asdict\nfrom pathlib import Path\n\n'
                  "if __package__ in (None, ''):\n    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))")
    p.write_text(t, encoding='utf-8')
    print('bootstrap added')
else:
    print('already has bootstrap')
