"""White-background figures for the node-plane scaling work."""
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
PURPLE = '#6a3d9a'


def style(ax, title, xlabel, ylabel):
    ax.set_facecolor('white')
    ax.figure.set_facecolor('white')
    for spine in ax.spines.values():
        spine.set_color('#999999')
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(True, color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.set_title(title, color=INK, fontsize=11, pad=10)
    ax.set_xlabel(xlabel, color=MUTED, fontsize=9)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=9)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default='report/fleet')
    parser.add_argument('--out', default='report/fleet/figures')
    args = parser.parse_args()
    data = json.loads((Path(args.data) / 'throughput_sweep.json').read_text(encoding='utf-8'))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    series = {}
    for target in data['targets']:
        label = 'old hub path (per-request SQLite)' if '8080' in target['target'] else 'node plane (in-memory + batch flush)'
        series[label] = [(row['concurrency'], row['rps'], row['p50_ms']) for row in target['levels']]

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    style(ax, 'Heartbeat throughput: old path vs. node plane', 'concurrent heartbeat senders', 'requests per second')
    for label, rows in series.items():
        color = GREEN if 'node plane' in label else RED
        ax.plot([row[0] for row in rows], [row[1] for row in rows], marker='o', linewidth=2,
                color=color, label=label)
        best = max(rows, key=lambda row: row[1])
        ax.annotate(f'peak {best[1]:.0f} req/s', (best[0], best[1]), textcoords='offset points',
                    xytext=(6, 8), fontsize=8, color=color)
    ax.set_xscale('log')
    ax.set_xticks([1, 4, 16, 64])
    ax.set_xticklabels(['1', '4', '16', '64'])
    ax.set_ylim(0, 200)
    ax.text(1.1, 178, 'above ~160 req/s a single client host becomes the limiter\n(see Fig. 24 for horizontal scaling)',
            fontsize=7, color=MUTED)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)
    fig.tight_layout()
    fig.savefig(out / 'fig23_throughput_old_vs_plane.png', facecolor='white', dpi=300)
    plt.close(fig)

    # nodes supported vs interval for 1..8 shards, using the measured per-shard peak
    measured = max(row[1] for row in series['node plane (in-memory + batch flush)'])
    per_shard = 130.0  # conservative: measured 133 req/s per shard with an independent client
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    style(ax, 'Fleet size supported by heartbeat interval and shard count',
          'heartbeat interval (s)', 'machines supported')
    intervals = np.array([2, 5, 10, 15, 30, 60], dtype=float)
    for shards, color in zip([1, 2, 4, 8], [BLUE, ORANGE, GREEN, PURPLE]):
        ax.plot(intervals, per_shard * shards * intervals, marker='o', linewidth=1.9, color=color,
                label=f'{shards} shard' + ('s' if shards > 1 else ''))
    for value, label in [(50, '50'), (100, '100'), (1000, '1 000')]:
        ax.axhline(value, color='#bbbbbb', linestyle=':', linewidth=0.9)
        ax.text(60, value * 1.08, f'{label} machines', fontsize=7, color=MUTED, ha='right')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xticks(intervals)
    ax.set_xticklabels([str(int(value)) for value in intervals])
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED, loc='upper left')
    fig.tight_layout()
    fig.savefig(out / 'fig24_nodes_supported.png', facecolor='white', dpi=300)
    plt.close(fig)

    print('figures ->', out, 'per-shard peak measured', measured)


if __name__ == '__main__':
    main()
