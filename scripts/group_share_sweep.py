import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pasadhi.app import group as gp

g = gp.default_office(120, 20, 10)
print(' share   earnings   per node')
rows = []
for share in (0.2, 0.3, 0.5, 0.7, 0.9, 1.0):
    g.share_pct = share
    g.mode = 'shared'
    result = gp.economics(g)
    per_node = result['shared_earnings_thb_month'] / 150
    rows.append({'share': share, 'earnings': result['shared_earnings_thb_month'], 'per_node': round(per_node)})
    print(f'{share*100:>5.0f}% {result["shared_earnings_thb_month"]:>10,.0f} {per_node:>9,.0f}')

out = Path('pasadhi/bench/results/group_share_sweep.json')
out.write_text(__import__('json').dumps(rows, indent=2), encoding='utf-8')
print('wrote', out)
