"""Figure 41: what happens when the number of listening ports grows (measured 1–8, extrapolated to 100)."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

INK, MUTED, GRID = '#1a1a1a', '#5a5a5a', '#e3e3e3'
PORTS = [1, 2, 4, 8]
RPS = [15.7, 26.5, 20.8, 23.5]
MEM_PER_PORT_MIB = 45.0
HOST_GIB = 7.7

fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.2), facecolor='white')


def style(ax, title, xlabel, ylabel):
    ax.set_facecolor('white')
    for spine in ax.spines.values():
        spine.set_color('#999999')
    ax.tick_params(colors=MUTED, labelsize=8.5)
    ax.grid(True, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.set_title(title, color=INK, fontsize=10, pad=9)
    ax.set_xlabel(xlabel, color=MUTED, fontsize=8.5)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=8.5)


ax = axes[0]
style(ax, 'Aggregate throughput versus listening ports', 'gateway ports (one worker each)', 'requests/s')
ax.plot(PORTS, RPS, marker='o', markersize=6, linewidth=1.8, color='#1f4e79', label='measured')
ax.axhspan(24, 29, color='#d9e2ec', alpha=0.8)
ax.text(1.1, 29.4, 'saturation on this host (24–29 req/s)', fontsize=7.5, color=MUTED)
ax.plot([8, 100], [23.5, 27], linestyle='--', linewidth=1.4, color='#c55a11',
        label='extrapolation: flat, no gain')
ax.set_xscale('log')
ax.set_xticks([1, 2, 4, 8, 16, 32, 64, 100])
ax.set_xticklabels(['1', '2', '4', '8', '16', '32', '64', '100'])
ax.set_ylim(0, 34)
ax.legend(frameon=False, fontsize=7.8, labelcolor=MUTED, loc='lower right')

ax = axes[1]
style(ax, 'Cost of each extra port', 'gateway ports', 'memory (GiB)')
ports = [1, 2, 4, 8, 16, 32, 64, 100]
memory = [p * MEM_PER_PORT_MIB / 1024 for p in ports]
ax.bar(range(len(ports)), memory, color='#2e75b6', width=0.62)
ax.axhline(HOST_GIB, color='#a61c00', linestyle='--', linewidth=1.2)
ax.text(0.2, HOST_GIB - 0.55, f'host memory {HOST_GIB} GiB (fleet already uses 1.3 GiB)', fontsize=7.2, color='#a61c00')
for index, value in enumerate(memory):
    ax.text(index, value + 0.1, f'{value:.1f}', ha='center', fontsize=7.2, color=INK)
ax.set_xticks(range(len(ports)))
ax.set_xticklabels([str(p) for p in ports])
ax.set_ylim(0, 8.6)

fig.tight_layout()
out = Path('report/figures')
out.mkdir(parents=True, exist_ok=True)
fig.savefig(out / 'fig41_many_ports.png', facecolor='white', dpi=300)
print('wrote report/figures/fig41_many_ports.png')
