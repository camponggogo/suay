"""White-background figures for the CPU-limit sweep (10% to 80%)."""
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
    ax.set_title(title, color=INK, fontsize=10.5, pad=10)
    ax.set_xlabel(xlabel, color=MUTED, fontsize=9)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=9)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default='report/cpu_sweep/sweep.json')
    parser.add_argument('--out', default='report/cpu_sweep/figures')
    args = parser.parse_args()
    rows = json.loads(Path(args.data).read_text(encoding='utf-8'))['rows']
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    cpu = [row['cpu'] * 100 for row in rows]
    rps1 = [row['c1']['rps'] for row in rows]
    rps8 = [row['c8']['rps'] for row in rows]
    mean1 = [row['c1']['mean_ms'] for row in rows]
    mean8 = [row['c8']['mean_ms'] for row in rows]
    live = [row['liveness']['mean'] for row in rows]
    dispatch = [row['dispatch_ms_delta'] or 0 for row in rows]

    def ticks(ax):
        ax.xaxis.set_major_locator(FixedLocator([10, 20, 30, 40, 50, 60, 70, 80]))
        ax.xaxis.set_minor_formatter(NullFormatter())

    fig, axes = plt.subplots(2, 2, figsize=(11.4, 7.4), facecolor='white')

    ax = axes[0][0]
    style(ax, 'Throughput vs. per-machine CPU limit', 'CPU limit per machine (%)', 'requests/s')
    ax.plot(cpu, rps1, marker='o', linewidth=2, color=BLUE, label='C=1 client')
    ax.plot(cpu, rps8, marker='s', linewidth=2, color=ORANGE, label='C=8 clients')
    ax.axhline(max(rps1 + rps8), color=GREEN, linestyle=':', linewidth=1, label='observed ceiling')
    ticks(ax)
    ax.set_ylim(0, 16)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED, loc='lower left')

    ax = axes[0][1]
    style(ax, 'Mean response time vs. CPU limit', 'CPU limit per machine (%)', 'mean latency (ms)')
    ax.plot(cpu, mean1, marker='o', linewidth=2, color=BLUE, label='C=1')
    ax.plot(cpu, mean8, marker='s', linewidth=2, color=ORANGE, label='C=8')
    ticks(ax)
    ax.set_ylim(0, 1200)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)

    ax = axes[1][0]
    style(ax, 'Fleet liveness vs. CPU limit', 'CPU limit per machine (%)', 'machines reported live (of 50)')
    ax.plot(cpu, live, marker='o', linewidth=2, color=GREEN)
    ax.axhline(50, color='#bbbbbb', linestyle=':', linewidth=1, label='all machines')
    ticks(ax)
    ax.set_ylim(40, 51)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)

    ax = axes[1][1]
    style(ax, 'Dispatch round trip vs. CPU limit', 'CPU limit per machine (%)', 'hub → machine RTT (ms)')
    ax.plot(cpu, dispatch, marker='o', linewidth=2, color=RED)
    ticks(ax)
    ax.set_ylim(0, 50)

    fig.tight_layout()
    fig.savefig(out / 'fig32_cpu_sweep.png', facecolor='white', dpi=300)
    plt.close(fig)

    summary = {
        'best_throughput': {'cpu_pct': cpu[rps8.index(max(rps8))], 'rps_c8': max(rps8),
                            'rps_c1_at_that_point': rps1[rps8.index(max(rps8))]},
        'plateau_from_pct': 10,
        'liveness_min': min(live), 'liveness_max': max(live),
        'dispatch_ms_min': min(dispatch), 'dispatch_ms_max': max(dispatch),
        'throughput_at_80_pct': {'c1': rps1[-1], 'c8': rps8[-1]},
        'throughput_at_10_pct': {'c1': rps1[0], 'c8': rps8[0]},
    }
    (out.parent / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
