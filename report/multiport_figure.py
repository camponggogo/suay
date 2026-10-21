"""Figure 40: single port versus multi-port parallel, direct and through an L4 proxy."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

INK, MUTED, GRID = '#1a1a1a', '#5a5a5a', '#e3e3e3'
LABELS = [
    '1 port\n1 worker',
    '1 port\n2 workers',
    '2 ports × 1 worker\ndirect (C=16)',
    '2 ports × 1 worker\ndirect (C=32)',
    '2 ports × 1 worker\nvia L4 proxy (C=16)',
    '2 ports × 1 worker\nvia L4 proxy (C=32)',
]
VALUES = [15.7, 24.8, 26.5, 28.8, 20.8, 19.2]
ERRORS = [0, 0, 0, 0, 0, 0]
COLOURS = ['#7f7f7f', '#1f4e79', '#2e75b6', '#2e75b6', '#c55a11', '#c55a11']

fig, ax = plt.subplots(figsize=(8.4, 4.3), facecolor='white')
ax.set_facecolor('white')
for spine in ax.spines.values():
    spine.set_color('#999999')
ax.tick_params(colors=MUTED, labelsize=8)
ax.grid(True, axis='y', color=GRID, linewidth=0.7)
ax.set_axisbelow(True)

bars = ax.bar(range(len(VALUES)), VALUES, color=COLOURS, width=0.62)
for bar, value in zip(bars, VALUES):
    ax.text(bar.get_x() + bar.get_width() / 2, value + 0.5, f'{value:.1f}', ha='center',
            fontsize=8.5, color=INK)

ax.set_xticks(range(len(VALUES)))
ax.set_xticklabels(LABELS, color=MUTED)
ax.set_ylabel('requests/s', color=MUTED, fontsize=9)
ax.set_ylim(0, 33)
ax.set_title('Multi-port parallel transport against the single-port baselines', color=INK, fontsize=10.5, pad=10)
ax.text(0.99, 0.02, 'all runs: 0 errors', transform=ax.transAxes, ha='right', fontsize=7.5, color=MUTED)

fig.tight_layout()
out = Path('report/figures')
out.mkdir(parents=True, exist_ok=True)
fig.savefig(out / 'fig40_multiport.png', facecolor='white', dpi=300)
print('wrote report/figures/fig40_multiport.png')
