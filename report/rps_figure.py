"""Figure 39: throughput versus concurrency for 1, 2 and 4 gateway workers.

    python report/rps_figure.py
"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

INK, MUTED, GRID = '#1a1a1a', '#5a5a5a', '#e3e3e3'
COLOURS = {1: '#7f7f7f', 2: '#1f4e79', 4: '#c55a11'}
DATA = {
    1: [(8, 15.0), (16, 15.7)],
    2: [(8, 22.3), (16, 24.8)],
    4: [(8, 29.1), (16, 23.7), (32, 20.5)],
}

fig, ax = plt.subplots(figsize=(7.4, 4.2), facecolor='white')
ax.set_facecolor('white')
for spine in ax.spines.values():
    spine.set_color('#999999')
ax.tick_params(colors=MUTED, labelsize=9)
ax.grid(True, color=GRID, linewidth=0.7)
ax.set_axisbelow(True)

for workers, points in DATA.items():
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ax.plot(xs, ys, marker='o', markersize=5, linewidth=1.8, color=COLOURS[workers],
            label=f'{workers} worker' + ('s' if workers > 1 else ''))

ax.axhspan(58.7, 71.2, color='#dddddd', alpha=0.6)
ax.text(8.4, 66, 'raw loop ceiling (health / models)', fontsize=7.5, color=MUTED)
ax.axhline(15.7, color='#bbbbbb', linestyle=':', linewidth=1)

ax.set_xlim(6, 34)
ax.set_ylim(0, 78)
ax.set_xlabel('concurrency (clients)', color=MUTED, fontsize=9)
ax.set_ylabel('requests/s', color=MUTED, fontsize=9)
ax.set_title('Gateway throughput by worker count (completion path)', color=INK, fontsize=10.5, pad=10)
ax.legend(frameon=False, fontsize=8, labelcolor=MUTED, loc='center right')

fig.tight_layout()
out = Path('report/figures')
out.mkdir(parents=True, exist_ok=True)
fig.savefig(out / 'fig39_rps_ceiling.png', facecolor='white', dpi=300)
fig.savefig('report/figures/fig39_rps_ceiling.png', facecolor='white', dpi=300)
print('wrote report/figures/fig39_rps_ceiling.png')
