"""Plot the concurrency sweep: response time percentiles, throughput and distribution.

    python sim/docker/plot.py --results sim/docker/results
"""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

BG = '#0b1020'
PANEL = '#121a33'
INK = '#e8ecff'
MUTED = '#8b93b8'
ACCENT = ['#7c5cff', '#22d3ee', '#34d399', '#fbbf24']


def style(ax):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=MUTED, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color('#243055')
    ax.grid(True, color='#1d2745', linewidth=0.8, alpha=0.8)
    ax.xaxis.label.set_color(MUTED)
    ax.yaxis.label.set_color(MUTED)
    ax.title.set_color(INK)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', default='sim/docker/results')
    args = parser.parse_args()
    root = Path(args.results)
    steps = json.loads((root / 'summary.json').read_text(encoding='utf-8'))['steps']
    xs = [step['concurrency'] for step in steps]

    fig, axes = plt.subplots(3, 1, figsize=(11, 14), facecolor=BG)
    fig.subplots_adjust(hspace=0.45, top=0.94, bottom=0.06, left=0.09, right=0.97)

    ax = axes[0]
    style(ax)
    for key, color, label in (('p50_ms', ACCENT[0], 'p50'), ('p95_ms', ACCENT[1], 'p95'),
                              ('p99_ms', ACCENT[2], 'p99')):
        ys = [step[key] for step in steps]
        ax.plot(xs, ys, marker='o', linewidth=2.2, color=color, label=label)
        for x, y in zip(xs, ys):
            ax.annotate(f'{y:.0f}', (x, y), textcoords='offset points', xytext=(0, 7),
                        ha='center', fontsize=8, color=color)
    ax.set_yscale('log')
    ax.set_xscale('log')
    ax.set_xticks(xs)
    ax.set_xticklabels([str(x) for x in xs])
    ax.set_xlabel('concurrent clients')
    ax.set_ylabel('response time (ms, log scale)')
    ax.set_title('Inference response time: p50 / p95 / p99')
    legend = ax.legend(frameon=False, fontsize=9)
    for text in legend.get_texts():
        text.set_color(INK)

    ax = axes[1]
    style(ax)
    ax.plot(xs, [step['rps'] for step in steps], marker='s', linewidth=2.2, color=ACCENT[3], label='requests/s')
    ax.set_xscale('log')
    ax.set_xticks(xs)
    ax.set_xticklabels([str(x) for x in xs])
    ax.set_xlabel('concurrent clients')
    ax.set_ylabel('throughput (requests/s)')
    ax.set_title('Throughput plateaus: the gateway, not the model, is the ceiling')
    for x, step in zip(xs, steps):
        ax.annotate(f"{step['rps']:.0f}", (x, step['rps']), textcoords='offset points', xytext=(0, 7),
                    ha='center', fontsize=8, color=ACCENT[3])
    errors = sum(step['errors'] for step in steps)
    ax.text(0.015, 0.93, f'nodes live during sweep: {steps[0]["nodes_live"]} · errors: {errors}',
            transform=ax.transAxes, fontsize=9, color=MUTED, va='top')

    ax = axes[2]
    style(ax)
    buckets = {}
    with (root / 'latency.csv').open(encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            if row['status'] != '200':
                continue
            buckets.setdefault(int(row['concurrency']), []).append(float(row['latency_ms']))
    data = [buckets.get(x, []) for x in xs]
    box = ax.boxplot(data, patch_artist=True, showfliers=False, widths=0.5)
    for index, patch in enumerate(box['boxes']):
        patch.set_facecolor(ACCENT[index % len(ACCENT)])
        patch.set_alpha(0.55)
        patch.set_edgecolor(INK)
    for element in ('whiskers', 'caps', 'medians'):
        for line in box[element]:
            line.set_color(INK)
    ax.set_xticks(range(1, len(xs) + 1))
    ax.set_xticklabels([str(x) for x in xs])
    ax.set_yscale('log')
    ax.set_xlabel('concurrent clients')
    ax.set_ylabel('response time (ms, log scale)')
    ax.set_title('Response-time distribution per concurrency (outliers hidden)')

    fig.suptitle('SUAY · 50 simulated machines · response time vs concurrency',
                 color=INK, fontsize=16, y=0.975)
    target = root / 'response_time_report.png'
    fig.savefig(target, facecolor=BG, dpi=150)
    print(f'wrote {target}')


if __name__ == '__main__':
    main()
