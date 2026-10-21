"""Cost model for BitTorrent-style computation sharding.

Answers one question with arithmetic instead of intuition: given a per-token compute cost and a measured
hop latency, how many pipeline stages are worth using — and at what point does activation traffic become the
new bottleneck?

    python sim/docker/bittorrent_model.py --out report/figures/fig9_pipeline_economics.png
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

BG = '#0b1020'
PANEL = '#121a33'
INK = '#e8ecff'
MUTED = '#8b93b8'
ACCENT = ['#7c5cff', '#22d3ee', '#34d399', '#fbbf24']

# Measured on the 50-machine run: uncontended dispatch hop 45 ms at C=1 includes HTTP + queue; the wire part is
# a few milliseconds. We model 1 ms (ideal LAN), 3 ms (realistic HTTP hop) and 8 ms (loaded hub).
HOPS = [1.0, 3.0, 8.0]
COMPUTE_PER_STEP = [30.0, 100.0, 300.0]   # ms per output step on one machine (8B CPU, 8B GPU, 70B CPU)
STAGES = np.arange(1, 33)
HIDDEN = 4096                              # 8B-class model, bf16
BYTES_PER_ACTIVATION = HIDDEN * 2          # 8 KiB carried per hop per step


def style(ax, title, xlabel, ylabel):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=MUTED, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color('#243055')
    ax.grid(True, color='#1d2745', linewidth=0.7, alpha=0.85)
    ax.set_title(title, color=INK, fontsize=11, pad=12)
    ax.set_xlabel(xlabel, color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='report/figures/fig9_pipeline_economics.png')
    parser.add_argument('--rps', type=float, default=10.0, help='request rate observed in the measurement')
    parser.add_argument('--steps', type=float, default=100.0, help='output steps (tokens) per response')
    args = parser.parse_args()

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8), facecolor=BG)

    ax = axes[0]
    style(ax, 'Per-step latency vs. pipeline stages', 'pipeline stages (machines in the chain)', 'ms per output step')
    optimum = {}
    for compute, color in zip(COMPUTE_PER_STEP, ACCENT):
        totals = compute / STAGES + STAGES * 3.0
        best = int(STAGES[int(np.argmin(totals))])
        optimum[compute] = (best, float(np.min(totals)))
        ax.plot(STAGES, totals, color=color, linewidth=2, label=f'{compute:.0f} ms/step on one machine')
        ax.scatter([best], [np.min(totals)], color=color, s=50, zorder=4, edgecolors=BG)
        ax.annotate(f'optimum S={best}', (best, np.min(totals)), textcoords='offset points', xytext=(6, 8),
                    fontsize=8, color=color)
    ax.set_yscale('log')
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)
    ax.axvline(50, color='#fb7185', linestyle='--', linewidth=1, alpha=0.7)
    ax.text(47, ax.get_ylim()[1] * 0.4, '50-way sharding', color='#fb7185', fontsize=8, ha='right', rotation=90)

    ax = axes[1]
    style(ax, 'Activation bandwidth vs. stages', 'pipeline stages', 'Mbit/s for the whole pipeline')
    traffic = args.rps * args.steps * BYTES_PER_ACTIVATION * 8 / 1e6
    ax.axhline(traffic, color=ACCENT[0], linewidth=2.2,
               label=f'activation traffic {traffic:.0f} Mbit/s (independent of stage count)')
    ax.axhline(1000, color='#fb7185', linestyle='--', linewidth=1.2, label='1 GbE link (1000 Mbit/s)')
    ax.axhline(0.0341, color=MUTED, linestyle=':', linewidth=1.4, label='measured gateway traffic (0.034 Mbit/s)')
    ax.text(1.4, traffic * 1.12, 'this becomes the new bottleneck', color=ACCENT[0], fontsize=8)
    ax.set_yscale('log')
    ax.set_xlim(1, 32)
    ax.set_xticks([1, 4, 8, 12, 16, 20, 24, 28, 32])
    ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc='center right')

    fig.tight_layout()
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, facecolor=BG, dpi=200)
    print('wrote', target)

    print('\noptimal stages (compute on one machine -> best pipeline depth, hop 3 ms):')
    for compute, (best, latency) in optimum.items():
        print(f'  {compute:5.0f} ms/step -> S*={best:2d}, {latency:6.1f} ms/step (vs {compute:.0f} unsharded)')

    print(f'\nactivation traffic at {args.rps:.0f} rps x {args.steps:.0f} steps: {traffic:.1f} Mbit/s')
    print(f'  = {traffic / 0.0341:.0f}x the measured gateway traffic, {100 * traffic / 1000:.0f}% of a 1 GbE link')
    print(f'  reference hop values considered: {HOPS} ms')


if __name__ == '__main__':
    main()
