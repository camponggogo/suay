"""Compare gateway worker configurations (white background)."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

INK = '#1a1a1a'
MUTED = '#5a5a5a'
GRID = '#e3e3e3'
BLUE = '#1f4e79'
ORANGE = '#c55a11'
GREEN = '#2e7d32'
RED = '#b00020'


def style(ax, title, xlabel, ylabel):
    ax.set_facecolor('white')
    ax.figure.set_facecolor('white')
    for spine in ax.spines.values():
        spine.set_color('#999999')
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(True, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.set_title(title, color=INK, fontsize=10.5, pad=10)
    ax.set_xlabel(xlabel, color=MUTED, fontsize=9)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=9)


def load(path):
    p = Path(path)
    if not p.exists():
        return {}
    return {step['concurrency']: step for step in json.loads(p.read_text(encoding='utf-8'))['steps']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='report/gateway/figures')
    args = parser.parse_args()
    runs = {
        '1 worker': load('sim/docker/results/opt5/summary.json'),
        '2 workers': load('sim/docker/results/opt2/summary.json'),
        '4 workers': load('sim/docker/results/opt4/summary.json'),
        '2 workers (after cache patch)': load('sim/docker/results/opt3/summary.json'),
    }
    levels = [8, 16, 32]
    colors = [BLUE, GREEN, ORANGE, RED]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.4), facecolor='white')
    width = 0.2
    positions = np.arange(len(levels))

    ax = axes[0]
    style(ax, 'Gateway throughput by worker count', 'concurrent clients', 'requests/s')
    for index, (label, data) in enumerate(runs.items()):
        values = [data.get(level, {}).get('rps', 0) for level in levels]
        ax.bar(positions + (index - 1.5) * width, values, width=width, color=colors[index], label=label)
    ax.set_xticks(positions)
    ax.set_xticklabels([f'C={level}' for level in levels])
    ax.set_ylim(0, 20)
    ax.legend(frameon=False, fontsize=7.5, labelcolor=MUTED)

    ax = axes[1]
    style(ax, 'Gateway latency by worker count', 'concurrent clients', 'mean latency (ms)')
    for index, (label, data) in enumerate(runs.items()):
        values = [data.get(level, {}).get('mean_ms', 0) for level in levels]
        ax.bar(positions + (index - 1.5) * width, values, width=width, color=colors[index], label=label)
    ax.set_xticks(positions)
    ax.set_xticklabels([f'C={level}' for level in levels])
    ax.set_yscale('log')
    ax.legend(frameon=False, fontsize=7.5, labelcolor=MUTED)

    fig.tight_layout()
    fig.savefig(out / 'fig33_gateway_workers.png', facecolor='white', dpi=300)
    plt.close(fig)
    print('figure ->', out)


if __name__ == '__main__':
    main()
