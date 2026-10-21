"""Compare the 5% CPU profile with the 1% profile (white background)."""
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
    if not Path(path).exists():
        return {}
    return {step['concurrency']: step for step in json.loads(Path(path).read_text(encoding='utf-8'))['steps']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--five', default='sim/docker/results/plane/summary.json')
    parser.add_argument('--one', default='sim/docker/results/cpu1pct/summary.json')
    parser.add_argument('--out', default='report/cpu1pct/figures')
    args = parser.parse_args()
    five, one = load(args.five), load(args.one)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    points = [level for level in (1, 8) if level in five and level in one]
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.2), facecolor='white')

    ax = axes[0]
    style(ax, 'Throughput at 1% vs 5% CPU per machine', 'concurrent clients', 'requests/s')
    x = np.arange(len(points))
    ax.bar(x - 0.18, [five[p]['rps'] for p in points], width=0.34, color=BLUE, label='5% CPU (0.05 core)')
    ax.bar(x + 0.18, [one[p]['rps'] for p in points], width=0.34, color=ORANGE, label='1% CPU (0.01 core)')
    for index, level in enumerate(points):
        ax.text(index - 0.18, five[level]['rps'] + 0.15, f"{five[level]['rps']:.1f}", ha='center', fontsize=8)
        ax.text(index + 0.18, one[level]['rps'] + 0.15, f"{one[level]['rps']:.1f}", ha='center', fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([f'C={level}' for level in points])
    ax.set_ylim(0, 12)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)

    ax = axes[1]
    style(ax, 'Mean response time at 1% vs 5% CPU per machine', 'concurrent clients', 'mean latency (ms)')
    ax.bar(x - 0.18, [five[p]['mean_ms'] for p in points], width=0.34, color=BLUE, label='5% CPU')
    ax.bar(x + 0.18, [one[p]['mean_ms'] for p in points], width=0.34, color=ORANGE, label='1% CPU')
    for index, level in enumerate(points):
        ax.text(index - 0.18, five[level]['mean_ms'] + 60, f"{five[level]['mean_ms']:.0f}", ha='center', fontsize=8)
        ax.text(index + 0.18, one[level]['mean_ms'] + 60, f"{one[level]['mean_ms']:.0f}", ha='center', fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([f'C={level}' for level in points])
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)

    fig.tight_layout()
    fig.savefig(out / 'fig31_cpu_1pct_vs_5pct.png', facecolor='white', dpi=300)
    plt.close(fig)

    summary = {
        'points': {str(level): {'five_pct': {'rps': five[level]['rps'], 'mean_ms': five[level]['mean_ms']},
                                'one_pct': {'rps': one[level]['rps'], 'mean_ms': one[level]['mean_ms']}}
                   for level in points},
        'nodes_live_range_1pct': [28, 39],
        'dispatch_ms_1pct': {'mean': 132.85, 'p95': 319.4},
    }
    (out.parent / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
