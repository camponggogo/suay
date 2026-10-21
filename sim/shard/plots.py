"""White-background figures for the map-reduce sharding benchmark."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullFormatter

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
    ax.set_title(title, color=INK, fontsize=11, pad=10)
    ax.set_xlabel(xlabel, color=MUTED, fontsize=9)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=9)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default='report/shard')
    parser.add_argument('--out', default='report/shard/figures')
    args = parser.parse_args()
    rows = json.loads((Path(args.data) / 'bench.json').read_text(encoding='utf-8'))['rows']
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    sizes = sorted({row['size_bytes'] for row in rows})
    colors = {sizes[0]: BLUE, sizes[1]: ORANGE, sizes[2]: GREEN}
    labels = {size: f'{size / 1024:.0f} KiB' for size in sizes}

    # 1 — time vs chunks
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    style(ax, 'Map-reduce time by chunk count (server-side)', 'chunks (machines used)', 'total time (ms, log)')
    for size in sizes:
        series = [row for row in rows if row['size_bytes'] == size]
        ax.plot([row['chunks'] for row in series], [row['ms_total'] for row in series],
                marker='o', linewidth=1.9, color=colors[size], label=f'{labels[size]} document')
        baseline = next(row['ms_total'] for row in series if row['chunks'] == 1)
        ax.axhline(baseline, color=colors[size], linestyle=':', linewidth=1, alpha=0.6)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.xaxis.set_major_locator(FixedLocator([1, 2, 4, 8, 16, 32, 50]))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticklabels(['1', '2', '4', '8', '16', '32', '50'])
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)
    ax.text(1.05, ax.get_ylim()[0] * 1.25, 'dotted = single-machine baseline', fontsize=7, color=MUTED)
    fig.tight_layout()
    fig.savefig(out / 'fig25_shard_time.png', facecolor='white', dpi=300)
    plt.close(fig)

    # 2 — speedup vs chunks
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    style(ax, 'Speedup over a single machine (below 1.0 means slower)', 'chunks (machines used)', 'speedup (x)')
    for size in sizes:
        series = [row for row in rows if row['size_bytes'] == size and row['chunks'] > 1]
        ax.plot([row['chunks'] for row in series], [row['speedup'] for row in series],
                marker='s', linewidth=1.9, color=colors[size], label=f'{labels[size]}')
    ax.axhline(1.0, color=INK, linestyle='-', linewidth=1)
    ax.axhline(0.0, color='#cccccc', linewidth=0.6)
    ax.set_xscale('log')
    ax.xaxis.set_major_locator(FixedLocator([2, 4, 8, 16, 32, 50]))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticklabels(['2', '4', '8', '16', '32', '50'])
    ax.set_ylim(0, 1.5)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED, loc='upper right')
    fig.tight_layout()
    fig.savefig(out / 'fig26_shard_speedup.png', facecolor='white', dpi=300)
    plt.close(fig)

    # 3 — where a 1 MiB request spends its time (measured once, wall clock vs coordinator-side)
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    style(ax, 'A 1 MiB request: transport dominates', 'measured on this host', 'milliseconds')
    labels_bar = ['client wall clock\n(incl. upload)', 'coordinator-side\n(parse + dispatch)']
    values = [1219.0, 198.3]
    bars = ax.bar(labels_bar, values, color=[ORANGE, BLUE], width=0.5)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 20, f'{value:.0f} ms', ha='center', fontsize=9,
                color=INK)
    ax.set_ylim(0, 1400)
    fig.tight_layout()
    fig.savefig(out / 'fig27_upload_dominates.png', facecolor='white', dpi=300)
    plt.close(fig)

    print('figures ->', out)


if __name__ == '__main__':
    main()
