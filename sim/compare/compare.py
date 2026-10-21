"""Compare our numbers with the Compute Index (week 7, 2026) and a real llama.cpp run on this host.

Inputs
  sim/compare/llama-bench.json   llama-bench -o json (this machine, Qwen2.5-0.5B Q4_K_M)
  report/experts/shapes.json     our deployment shapes

    python sim/compare/compare.py --data report/compare
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
PURPLE = '#6a3d9a'

CLOUD = [
    ('LFM 2.5 1.2B (free)', 359, 0.00, 'general'),
    ('Ministral 3B', 292, 0.10, 'efficiency'),
    ('Mistral Small Creative', 223, 0.10, 'efficiency'),
    ('Grok 4.1 Fast', 207, 0.20, 'reasoning'),
    ('GPT-5.2 Codex', 204, 1.75, 'coding'),
    ('Nemotron-3 Nano 30B A3B', 191, 0.05, 'efficiency'),
    ('GPT-5.1 Codex mini', 185, 0.25, 'coding'),
    ('GPT-5.1 Codex', 154, 1.25, 'coding'),
    ('Ministral 14B', 143, 0.20, 'efficiency'),
    ('Relace Search', 140, 1.00, 'reasoning'),
    ('MJ-1 Instruct', 132, 0.15, 'coding'),
    ('GPT-5.1 Chat', 113, 1.25, 'reasoning'),
    ('GPT-5.2 Chat', 90, 1.75, 'reasoning'),
    ('GPT-5.2', 77, 1.75, 'reasoning'),
    ('GPT-5.1', 72, 1.25, 'reasoning'),
    ('Devstral 2512', 66, 0.05, 'general'),
    ('Qwen3 Coder Next', 63, 0.07, 'coding'),
    ('DeepSeek V3.1 Nex N1', 29, 0.27, 'general'),
    ('Mistral Large 2512', 26, 0.50, 'efficiency'),
    ('Claude Opus 4.6', 19, 1.75, 'reasoning'),
]
COLORS = {'general': '#e0b52b', 'efficiency': '#4a8f4a', 'reasoning': '#c0504d', 'coding': '#3f6f9f'}


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


def read_llama(path):
    if not path.exists():
        return None
    rows = json.loads(path.read_text(encoding='utf-8-sig'))
    prompt = next((float(row['avg_ts']) for row in rows if row.get('n_prompt', 0) > 0), 0.0)
    generation = next((float(row['avg_ts']) for row in rows if row.get('n_gen', 0) > 0), 0.0)
    first = rows[0]
    return {'prompt_tps': round(prompt, 2), 'gen_tps': round(generation, 2),
            'cpu': first.get('cpu_info', ''), 'model': first.get('model_type', ''),
            'threads': first.get('n_threads', 0), 'params': first.get('model_n_params', 0),
            'build': first.get('build_number', 0)}


def on_prem(duty, machines, gen_tps_per_machine, hardware_usd=300.0, years=3.0,
            watts=25.0, hours=8, days=250, kwh_usd=0.12):
    fleet_tps = machines * gen_tps_per_machine * duty
    annual_tokens = fleet_tps * 86400 * 365
    annual_cost = machines * hardware_usd / years + machines * watts / 1000 * hours * days * kwh_usd
    return (round(annual_cost / (annual_tokens / 1e6), 4) if annual_tokens else 0.0,
            round(fleet_tps, 1), round(annual_cost, 0))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default='report/compare')
    parser.add_argument('--machines', type=int, default=50)
    args = parser.parse_args()
    out = Path(args.data)
    (out / 'figures').mkdir(parents=True, exist_ok=True)

    shapes = []
    if Path('report/experts/shapes.json').exists():
        shapes = json.loads(Path('report/experts/shapes.json').read_text(encoding='utf-8'))['shapes']
    llama = read_llama(Path('sim/compare/llama-bench.json'))
    local_gen = (llama or {}).get('gen_tps', 0.0) or 11.7

    # ---------------------------------------------------------- fig 16: generation speed landscape
    entries = [(name, tps, 'cloud') for name, tps, _, _ in CLOUD]
    if llama:
        entries.append((f"llama.cpp · Qwen2.5-0.5B Q4 · {llama['cpu'].split('@')[0].strip()}", llama['gen_tps'], 'local'))
    for shape in shapes:
        steps = 150.0 / max(0.001, shape['latency_s'] - 0.098)
        entries.append((f"this pool · {shape['shape']} (modelled)", round(steps, 1), 'ours'))
    entries.sort(key=lambda item: item[1])

    fig, ax = plt.subplots(figsize=(8.6, 7.4))
    style(ax, 'Generation speed: cloud APIs vs. local hardware', 'tokens per second (log scale)', '')
    labels = [item[0] for item in entries]
    values = [max(item[1], 0.1) for item in entries]
    colors = [BLUE if kind == 'cloud' else (PURPLE if kind == 'local' else GREEN) for _, _, kind in entries]
    ax.barh(range(len(entries)), values, color=colors, height=0.68)
    ax.set_yticks(range(len(entries)))
    ax.set_yticklabels(labels, fontsize=7.5)
    ax.set_xscale('log')
    ax.set_xlim(0.5, 900)
    for index, value in enumerate(values):
        ax.text(value * 1.08, index, f'{value:.1f}', va='center', fontsize=7, color=INK)
    handles = [plt.Rectangle((0, 0), 1, 1, color=color) for color in (BLUE, PURPLE, GREEN)]
    ax.legend(handles, ['cloud API (Compute Index, week 7 2026)', 'llama.cpp measured on this host',
                        'this project (modelled from measurements)'],
              frameon=False, fontsize=8, labelcolor=MUTED, loc='lower right')
    fig.tight_layout()
    fig.savefig(out / 'figures' / 'fig16_generation_speed.png', facecolor='white', dpi=300)
    plt.close(fig)

    # ---------------------------------------------------------- fig 17: value frontier
    fig, ax = plt.subplots(figsize=(7.6, 5.4))
    style(ax, 'Value frontier: speed vs. cost per 1M tokens', 'cost per 1M tokens (USD, log)',
          'tokens per second (log)')
    for index, (name, tps, price, category) in enumerate(CLOUD):
        x = max(price, 0.008)
        marker = '*' if price == 0 else 'o'
        ax.scatter([x], [tps], s=90 if price == 0 else 48, marker=marker, color=COLORS[category],
                   edgecolors='white', linewidths=0.8, zorder=3)
        if name in {'LFM 2.5 1.2B (free)', 'Ministral 3B', 'GPT-5.2 Codex', 'Claude Opus 4.6',
                    'Nemotron-3 Nano 30B A3B'}:
            offset = (6, 5) if index % 2 == 0 else (6, -12)
            ax.annotate(name, (x, tps), textcoords='offset points', xytext=offset,
                        fontsize=6.6, color=MUTED)
    curve = []
    for duty in [1.0, 0.5, 0.2, 0.1, 0.05]:
        cost, tokens, _ = on_prem(duty, args.machines, local_gen)
        curve.append((cost, tokens, duty))
    ax.plot([item[0] for item in curve], [item[1] for item in curve], color=GREEN, linewidth=2,
            marker='o', markersize=5, label='this pool, duty cycle 100% → 5%')
    for index, (cost, tokens, duty) in enumerate(curve[::2]):
        offset = (8, -12) if index % 2 == 0 else (-24, 10)
        ax.annotate(f'{duty:.0%} duty', (cost, tokens), textcoords='offset points', xytext=offset,
                    fontsize=7, color=GREEN)
    ax.scatter([max(cost, 1e-3) for cost, _, _ in curve[:1]], [curve[0][1]], s=90, color=GREEN,
               edgecolors='white', zorder=4)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(0.008, 3.0)
    ax.set_ylim(3, 900)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED, loc='upper right')
    fig.tight_layout()
    fig.savefig(out / 'figures' / 'fig17_value_frontier.png', facecolor='white', dpi=300)
    plt.close(fig)

    # ---------------------------------------------------------- fig 18: our shapes vs one local box
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    style(ax, 'This project: capacity per deployment shape', 'tokens/s per stream', 'fleet capacity (requests/s)')
    for shape in shapes:
        steps = 150.0 / max(0.001, shape['latency_s'] - 0.098)
        color = GREEN if shape['shape'] == 'domain_experts' else (BLUE if shape['shape'] == 'dense_8b' else RED)
        ax.scatter([steps], [max(shape['fleet_rps'], 1e-3)], s=110, color=color,
                   edgecolors='white', linewidths=1.1, zorder=3)
        ax.annotate(f"{shape['shape']}\n{shape['nodes_total']} nodes", (steps, max(shape['fleet_rps'], 1e-3)),
                    textcoords='offset points', xytext=(8, 6), fontsize=8, color=INK)
    ax.axvline(11.74, color=PURPLE, linestyle='--', linewidth=1.2,
               label='llama.cpp measured here (11.7 tok/s)')
    ax.axvline(float(np.median([tps for _, tps, _, _ in CLOUD])), color=ORANGE, linestyle=':',
               linewidth=1.2, label='median cloud TPS (113)')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)
    fig.tight_layout()
    fig.savefig(out / 'figures' / 'fig18_capacity_vs_speed.png', facecolor='white', dpi=300)
    plt.close(fig)

    duties = [{'duty': duty, 'cost_per_mtok': cost, 'fleet_tps': tokens, 'annual_usd': annual}
              for duty in [1.0, 0.5, 0.2, 0.1, 0.05]
              for cost, tokens, annual in [on_prem(duty, args.machines, local_gen)]]
    metrics = {
        'cloud_tps': {'min': min(t for _, t, _, _ in CLOUD), 'median': float(np.median([t for _, t, _, _ in CLOUD])),
                      'max': max(t for _, t, _, _ in CLOUD)},
        'cloud_price': {'min': min(p for _, _, p, _ in CLOUD), 'max': max(p for _, _, p, _ in CLOUD)},
        'llama_cpp': llama,
        'on_prem': {'machines': args.machines, 'gen_tps_per_machine': local_gen, 'curve': duties},
        'our_shapes': [{'shape': s['shape'], 'nodes': s['nodes_total'], 'fleet_rps': s['fleet_rps'],
                        'tokens_per_s': round(150.0 / max(0.001, s['latency_s'] - 0.098), 1)} for s in shapes],
        'speed_gap_vs_cloud_median': round(float(np.median([t for _, t, _, _ in CLOUD])) / local_gen, 1),
    }
    (out / 'metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    print(json.dumps(metrics, indent=2))
    print('figures ->', out / 'figures')


if __name__ == '__main__':
    main()
