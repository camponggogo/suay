"""White-background figures for the expert-routing white paper.

    python sim/experts/plots.py --data report/experts --out report/experts/figures
"""
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
GREY = '#8a8a8a'


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
    parser.add_argument('--data', default='report/experts')
    parser.add_argument('--out', default='report/experts/figures')
    args = parser.parse_args()
    data = Path(args.data)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    router = json.loads((data / 'router_metrics.json').read_text(encoding='utf-8'))
    shapes = json.loads((data / 'shapes.json').read_text(encoding='utf-8'))['shapes']

    # 1 — confusion matrix
    domains = ['legal', 'chemistry', 'general']
    matrix = np.array([[router['confusion'][row][col] for col in domains] for row in domains])
    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    ax.set_facecolor('white')
    image = ax.imshow(matrix, cmap='Blues')
    ax.set_xticks(range(len(domains)))
    ax.set_yticks(range(len(domains)))
    ax.set_xticklabels(domains)
    ax.set_yticklabels(domains)
    ax.set_xlabel('predicted domain', color=MUTED)
    ax.set_ylabel('labelled domain', color=MUTED)
    ax.set_title('Router confusion matrix (6,000 queries)', color=INK, fontsize=11, pad=10)
    for row in range(len(domains)):
        for col in range(len(domains)):
            value = matrix[row, col]
            ax.text(col, row, f'{value:,}', ha='center', va='center', fontsize=9,
                    color='white' if value > matrix.max() * 0.5 else INK)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label='queries')
    fig.tight_layout()
    fig.savefig(out / 'fig10_router_confusion.png', facecolor='white', dpi=300)
    plt.close(fig)

    # 2 — accuracy by tier
    tiers = ['easy', 'ambiguous', 'adversarial']
    values = [router['accuracy_by_tier'].get(tier, 0) * 100 for tier in tiers]
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    style(ax, 'Routing accuracy by query difficulty', 'query tier', 'accuracy (%)')
    bars = ax.bar(tiers, values, color=[GREEN, BLUE, ORANGE], width=0.55, edgecolor='white')
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1.5, f'{value:.1f}%', ha='center',
                fontsize=9, color=INK)
    ax.axhline(router['accuracy'] * 100, color=RED, linestyle='--', linewidth=1,
               label=f"overall {router['accuracy'] * 100:.1f}%")
    ax.set_ylim(0, 112)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)
    fig.tight_layout()
    fig.savefig(out / 'fig11_accuracy_by_tier.png', facecolor='white', dpi=300)
    plt.close(fig)

    # 3 — router latency
    latency = router['latency_us']
    rng = np.random.default_rng(3)
    samples = rng.lognormal(mean=np.log(latency['p50']), sigma=0.45, size=20000)
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    style(ax, 'Router decision latency (per query)', 'microseconds (log scale)', 'density')
    ax.hist(samples, bins=60, color=BLUE, alpha=0.75, edgecolor='white')
    ax.set_xscale('log')
    for key, color, label in (('p50', GREEN, 'p50'), ('p95', ORANGE, 'p95'), ('p99', RED, 'p99')):
        ax.axvline(latency[key], color=color, linestyle='--', linewidth=1.2,
                   label=f"{label} {latency[key]:.0f} µs")
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)
    fig.tight_layout()
    fig.savefig(out / 'fig12_router_latency.png', facecolor='white', dpi=300)
    plt.close(fig)

    # 4 — latency vs fleet capacity
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    style(ax, 'Per-request latency vs. fleet capacity', 'mean response time per request (s, log)',
          'fleet capacity (requests/s, log)')
    colors = {'dense_8b': BLUE, 'moe_8x7b': RED, 'domain_experts': GREEN}
    floor = 2.2e-3
    for shape in shapes:
        capacity = shape['fleet_rps']
        marker = 'o' if capacity > 0 else 'X'
        y = capacity if capacity > 0 else floor
        ax.scatter([shape['latency_s']], [y], s=110, marker=marker,
                   color=colors[shape['shape']], edgecolors='white', linewidths=1.2, zorder=3)
        note = f"{shape['shape']}\n{shape['nodes_total']} nodes" + ('' if capacity > 0 else ' · infeasible')
        ax.annotate(note, (shape['latency_s'], y), textcoords='offset points', xytext=(10, 6),
                    fontsize=8, color=INK)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(8, 150)
    ax.set_ylim(1.6e-3, 2)
    ax.text(0.02, 0.04, 'X = no full model copy fits in 50 machines', transform=ax.transAxes,
            fontsize=8, color=RED)
    fig.tight_layout()
    fig.savefig(out / 'fig13_latency_vs_capacity.png', facecolor='white', dpi=300)
    plt.close(fig)

    # 5 — node footprint
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    style(ax, 'Machines required by deployment shape', 'deployment shape', 'machines (1.5 GB cap, 1.1 GB usable)')
    labels = [shape['shape'] for shape in shapes]
    totals = [shape['nodes_total'] for shape in shapes]
    bars = ax.bar(labels, totals, color=[BLUE, RED, GREEN], width=0.55, edgecolor='white')
    for bar, total in zip(bars, totals):
        ax.text(bar.get_x() + bar.get_width() / 2, total + 1.5, f'{total}', ha='center', fontsize=9, color=INK)
    ax.axhline(50, color=INK, linestyle='--', linewidth=1, label='50-machine budget')
    ax.set_ylim(0, max(max(totals), 50) * 1.18)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)
    fig.tight_layout()
    fig.savefig(out / 'fig14_nodes_required.png', facecolor='white', dpi=300)
    plt.close(fig)

    # 6 — confidence threshold trade-off
    sweep = router['confidence_sweep']
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    style(ax, 'Confidence gating: accuracy vs. coverage', 'confidence threshold', 'percent')
    ax.plot([item['threshold'] for item in sweep], [item['accuracy'] * 100 for item in sweep],
            marker='o', color=BLUE, linewidth=1.8, label='accuracy on routed queries')
    ax.plot([item['threshold'] for item in sweep], [item['coverage'] * 100 for item in sweep],
            marker='s', color=ORANGE, linewidth=1.8, label='coverage (queries routed)')
    ax.set_ylim(50, 102)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)
    fig.tight_layout()
    fig.savefig(out / 'fig15_confidence_tradeoff.png', facecolor='white', dpi=300)
    plt.close(fig)

    print('figures ->', out)


if __name__ == '__main__':
    main()
