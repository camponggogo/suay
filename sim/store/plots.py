"""White-background figure: SQLite vs PostgreSQL on the hot path."""
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default='report/store/bench.json')
    parser.add_argument('--out', default='report/store/figures')
    args = parser.parse_args()
    rows = json.loads(Path(args.data).read_text(encoding='utf-8'))['rows']
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    levels = sorted({row['concurrency'] for row in rows})
    series = {}
    for backend in ('sqlite', 'postgresql'):
        series[backend] = {row['concurrency']: row for row in rows if row['backend'] == backend}

    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.2), facecolor='white')
    width = 0.34
    x = np.arange(len(levels))

    ax = axes[0]
    style(ax, 'Hot-path throughput (atomic consume + usage write)', 'concurrent writers', 'operations/s')
    ax.bar(x - width / 2, [series['sqlite'][l]['ops_per_s'] for l in levels], width, color=BLUE, label='SQLite (WAL)')
    if any(l in series['postgresql'] for l in levels):
        ax.bar(x + width / 2, [series['postgresql'].get(l, {}).get('ops_per_s', 0) for l in levels],
               width, color=ORANGE, label='PostgreSQL')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{l} writer' + ('s' if l > 1 else '') for l in levels])
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)

    ax = axes[1]
    style(ax, 'Tail latency of the same operation', 'concurrent writers', 'p95 (ms)')
    ax.bar(x - width / 2, [series['sqlite'][l]['p95_ms'] for l in levels], width, color=BLUE, label='SQLite (WAL)')
    if any(l in series['postgresql'] for l in levels):
        ax.bar(x + width / 2, [series['postgresql'].get(l, {}).get('p95_ms', 0) for l in levels],
               width, color=ORANGE, label='PostgreSQL')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{l} writer' + ('s' if l > 1 else '') for l in levels])
    ax.set_yscale('log')
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)

    fig.tight_layout()
    fig.savefig(out / 'fig36_store_compare.png', facecolor='white', dpi=300)
    plt.close(fig)
    print('figure ->', out)


if __name__ == '__main__':
    main()
