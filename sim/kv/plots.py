"""White-background figures for the prefix-cache / KV-aware routing result."""
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
    parser.add_argument('--data', default='report/kv')
    parser.add_argument('--out', default='report/kv/figures')
    args = parser.parse_args()
    rows = json.loads((Path(args.data) / 'bench.json').read_text(encoding='utf-8'))['rows']
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    sizes = sorted({row['size_tokens'] for row in rows})
    ratios = sorted({round(row['repeat_ratio'] * 100) for row in rows})
    size_color = {sizes[0]: BLUE, sizes[1]: ORANGE}

    # 1 — TTFT p50
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    style(ax, 'Time to first token vs. document reuse (p50)', 'requests reusing a popular document (%)',
          'TTFT (s, log)')
    for size in sizes:
        base = [next(row for row in rows if row['size_tokens'] == size and round(row['repeat_ratio'] * 100) == ratio
                     and row['policy'] == 'round_robin')['ttft_p50_s'] for ratio in ratios]
        aware = [next(row for row in rows if row['size_tokens'] == size and round(row['repeat_ratio'] * 100) == ratio
                      and row['policy'] == 'cache_aware')['ttft_p50_s'] for ratio in ratios]
        ax.plot(ratios, base, marker='o', linestyle='--', linewidth=1.6, color=size_color[size],
                label=f'{size}-token doc · round-robin (no cache)')
        ax.plot(ratios, aware, marker='s', linewidth=2.2, color=size_color[size],
                label=f'{size}-token doc · prefix cache + KV-aware routing')
    ax.set_yscale('log')
    ax.xaxis.set_major_locator(FixedLocator(ratios))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.legend(frameon=False, fontsize=7.5, labelcolor=MUTED)
    fig.tight_layout()
    fig.savefig(out / 'fig28_ttft_vs_reuse.png', facecolor='white', dpi=300)
    plt.close(fig)

    # 2 — throughput
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    style(ax, 'Throughput vs. document reuse', 'requests reusing a popular document (%)',
          'requests per minute')
    for size in sizes:
        base = [next(row for row in rows if row['size_tokens'] == size and round(row['repeat_ratio'] * 100) == ratio
                     and row['policy'] == 'round_robin')['throughput_rpm'] for ratio in ratios]
        aware = [next(row for row in rows if row['size_tokens'] == size and round(row['repeat_ratio'] * 100) == ratio
                      and row['policy'] == 'cache_aware')['throughput_rpm'] for ratio in ratios]
        ax.plot(ratios, base, marker='o', linestyle='--', linewidth=1.6, color=size_color[size],
                label=f'{size}-token doc · no cache')
        ax.plot(ratios, aware, marker='s', linewidth=2.2, color=size_color[size],
                label=f'{size}-token doc · prefix cache')
        for ratio, value in zip(ratios, aware):
            ax.annotate(f'{value:.1f}', (ratio, value), textcoords='offset points', xytext=(0, 6),
                        ha='center', fontsize=6.5, color=size_color[size])
    ax.xaxis.set_major_locator(FixedLocator(ratios))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.legend(frameon=False, fontsize=7.5, labelcolor=MUTED, loc='upper left')
    fig.tight_layout()
    fig.savefig(out / 'fig29_throughput_vs_reuse.png', facecolor='white', dpi=300)
    plt.close(fig)

    # 3 — cache effectiveness
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    style(ax, 'Cache effectiveness (prefix-cache policy)', 'requests reusing a popular document (%)',
          'percent of prompt tokens served from cache')
    for size in sizes:
        reuse = [next(row for row in rows if row['size_tokens'] == size and round(row['repeat_ratio'] * 100) == ratio
                      and row['policy'] == 'cache_aware')['block_reuse_pct'] for ratio in ratios]
        ax.plot(ratios, reuse, marker='o', linewidth=2, color=size_color[size], label=f'{size}-token doc')
    ax.plot(ratios, ratios, color='#bbbbbb', linestyle=':', linewidth=1, label='perfect reuse (1:1)')
    ax.xaxis.set_major_locator(FixedLocator(ratios))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=7.5, labelcolor=MUTED)
    fig.tight_layout()
    fig.savefig(out / 'fig30_cache_effectiveness.png', facecolor='white', dpi=300)
    plt.close(fig)

    print('figures ->', out)


if __name__ == '__main__':
    main()
