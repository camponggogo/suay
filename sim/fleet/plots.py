"""White-background figures for the i3 / 8 GB / 120 GB fleet study (50-100 machines)."""
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
MODEL_COLORS = [GREEN, BLUE, ORANGE, RED]


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
    data = json.loads((Path(args.data) / 'fleet_model.json').read_text(encoding='utf-8'))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = data['rows']
    models = []
    for row in rows:
        if row['model'] not in models:
            models.append(row['model'])
    fleets = sorted({row['fleet'] for row in rows})

    # 1 — capacity vs fleet size
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    style(ax, 'Fleet capacity by model class (dedicated mode, 4 GB cap)',
          'machines in the fleet', 'requests per second (150-step answers)')
    for index, model in enumerate(models):
        series = [row for row in rows if row['model'] == model]
        ax.plot([row['fleet'] for row in series], [row['capacity_dedicated_rps'] for row in series],
                marker='o', linewidth=1.9, color=MODEL_COLORS[index], label=model)
    ax.axhline(data['anchors']['gateway_ceiling_rps'], color=INK, linestyle='--', linewidth=1.1,
               label=f"gateway ceiling {data['anchors']['gateway_ceiling_rps']:.1f} req/s (measured)")
    ax.axvspan(50, 55, color=RED, alpha=0.06)
    ax.text(55.6, ax.get_ylim()[1] * 0.62, 'single hub\nstops keeping up\n(see Fig. 20)', fontsize=7, color=RED)
    ax.set_yscale('log')
    ax.set_xlim(48, 102)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED, loc='lower right')
    fig.tight_layout()
    fig.savefig(out / 'fig19_capacity_vs_fleet.png', facecolor='white', dpi=300)
    plt.close(fig)

    # 2 — measured heartbeat stress
    stress = data['heartbeat_stress']
    if stress:
        fig, ax = plt.subplots(figsize=(7.0, 4.4))
        style(ax, 'Measured heartbeat handling by fleet size (single hub worker)',
              'simulated machines', 'response time (ms)')
        xs = [item['machines'] for item in stress]
        width = 5.0
        ax.bar([x - width for x in xs], [item['p50_ms'] for item in stress], width=width * 1.6,
               color=BLUE, label='p50')
        ax.bar([x + width * 0.6 for x in xs], [item['p95_ms'] for item in stress], width=width * 1.6,
               color=ORANGE, label='p95')
        ax.set_yscale('log')
        ax.set_ylim(80, 6000)
        ax.set_xticks(xs)
        ax.legend(frameon=False, fontsize=8, labelcolor=MUTED, loc='lower left')
        twin = ax.twinx()
        twin.plot(xs, [item['achieved_share_pct'] for item in stress], color=GREEN, marker='o', linewidth=1.8)
        twin.set_ylabel('heartbeats delivered (%)', color=GREEN, fontsize=9)
        twin.tick_params(colors=GREEN, labelsize=9)
        twin.set_ylim(40, 105)
        for spine in twin.spines.values():
            spine.set_color('#999999')
        fig.tight_layout()
        fig.savefig(out / 'fig20_heartbeat_stress.png', facecolor='white', dpi=300)
        plt.close(fig)

    # 3 — largest model that still yields >= 1 req/s
    best = []
    for fleet in fleets:
        candidates = [row for row in rows if row['fleet'] == fleet and row['capacity_dedicated_rps'] >= 1.0]
        best.append((fleet, candidates[-1]['model'] if candidates else 'none'))
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    style(ax, 'Largest model that still serves at least 1 req/s', 'machines in the fleet', 'model class')
    labels = [item[1] for item in best]
    ax.bar([item[0] for item in best], range(1, len(best) + 1), color=BLUE, width=6)
    ax.set_yticks(range(1, len(best) + 1))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(44, 106)
    fig.tight_layout()
    fig.savefig(out / 'fig21_best_model_by_fleet.png', facecolor='white', dpi=300)
    plt.close(fig)

    # 4 — cost per 1M tokens
    hardware, years, watts, hours, days, kwh = 200.0, 3.0, 65.0, 8, 250, 0.12
    annual_per_machine = hardware / years + watts / 1000 * hours * days * kwh
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    style(ax, 'Amortised cost per 1M output tokens (i3, $200 used PC)',
          'model class', 'USD per 1M tokens')
    positions = np.arange(len(models))
    for offset, duty, color in ((-0.18, 0.2, BLUE), (0.18, 1.0, GREEN)):
        costs = []
        for model in models:
            row = next(item for item in rows if item['model'] == model and item['fleet'] == 100)
            tokens_per_year = row['tps_per_stream'] * duty * 86400 * 365
            costs.append(annual_per_machine * 1e6 / tokens_per_year)
        ax.bar(positions + offset, costs, width=0.32, color=color, label=f'duty {duty:.0%}')
        for x, value in zip(positions + offset, costs):
            ax.text(x, value * 1.06, f'${value:.2f}', ha='center', fontsize=7, color=INK)
    ax.axhline(0.10, color=RED, linestyle='--', linewidth=1.1, label='cloud flash tier ($0.10/1M)')
    ax.set_yscale('log')
    ax.set_xticks(positions)
    ax.set_xticklabels([model.replace(' Q4', '') for model in models], fontsize=8)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)
    fig.tight_layout()
    fig.savefig(out / 'fig22_cost_per_mtok.png', facecolor='white', dpi=300)
    plt.close(fig)

    print('figures ->', out)


if __name__ == '__main__':
    main()
