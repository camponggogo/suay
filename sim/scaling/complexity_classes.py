"""Node-count growth classes, evaluated with the constants measured in this project.

Every law is normalised to the same fleet at n = 50 (50 machines), then followed as the base n grows:
    O(1)         nodes = 50
    O(log n)     nodes = 50 · log2(n)/log2(50)
    O(n)         nodes = n
    O(2n)        nodes = 2n                (linear with a constant factor)
    O(n log n)   nodes = n · log2(n)/log2(50)
    O(n²)        nodes = 50 · (n/50)²
    O(cⁿ)        nodes = 50 · 1.05^(n−50)
    O(nⁿ)        nodes = 50 · (n/50)^(n−50)

Effective capacity uses the measured factors:
    s = 0.141 req/s per machine, gateway = 15.7 req/s,
    delivery(N) = exp(−0.0085·(N−30)) floored at 0.35,
    dispatch(N) = 28 + 0.4·max(0, N−50) ms,
    machine cost 1.045e-5 $/machine-second (from $0.29 per 1M tokens over 50 machines).

    python sim/scaling/complexity_classes.py --out report/growth
"""
import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

S_NODE = 21.13 / 150.0
GATEWAY = 15.7
DECAY = 0.0085
FLOOR = 0.35
MACHINE_USD_S = 0.29 / (50 * (1_000_000 / 150) / 12.0)   # $/machine-second implied by the fleet study
CAP = 20_000


def delivery(n):
    return 1.0 if n <= 30 else max(FLOOR, math.exp(-DECAY * (n - 30)))


def dispatch_ms(n):
    return 28.0 + max(0.0, n - 50) * 0.4


def nodes_for(law, n):
    if law == 'O(1)':
        raw = 50
    elif law == 'O(log n)':
        raw = 50 * math.log2(max(n, 2)) / math.log2(50)
    elif law == 'O(n)':
        raw = n
    elif law == 'O(2n)':
        raw = 2 * n
    elif law == 'O(n log n)':
        raw = n * math.log2(max(n, 2)) / math.log2(50)
    elif law == 'O(n²)':
        raw = 50 * (n / 50) ** 2
    elif law == 'O(cⁿ)':
        raw = 50 * 1.05 ** max(0, n - 50)
    elif law == 'O(nⁿ)':
        exponent = max(0, n - 50)
        raw = CAP if exponent > 12 else (50 * (n / 50) ** exponent if exponent else 50)
    else:
        raise ValueError(law)
    return min(int(round(raw)), CAP)


def evaluate(law, n):
    nodes = nodes_for(law, n)
    eff = min(GATEWAY, nodes * S_NODE * delivery(nodes))
    return {
        'law': law,
        'n': n,
        'nodes': nodes,
        'delivery': round(delivery(nodes), 3),
        'effective_rps': round(eff, 2),
        'rps_per_100_nodes': round(100 * eff / nodes, 2),
        'dispatch_ms': round(dispatch_ms(nodes), 1),
        'cost_per_mtok': round(nodes * MACHINE_USD_S * (1_000_000 / 150) / eff, 3),
        'capped': nodes >= CAP,
    }


LAWS = ['O(1)', 'O(log n)', 'O(n)', 'O(2n)', 'O(n log n)', 'O(n²)', 'O(cⁿ)', 'O(nⁿ)']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='report/growth')
    args = parser.parse_args()
    out = Path(args.out)
    (out / 'figures').mkdir(parents=True, exist_ok=True)

    points = [50, 100, 200, 500]
    table = [[evaluate(law, n) for n in points] for law in LAWS]

    # first n where the law reaches the gateway ceiling (needs >= 318 machines at the delivery floor)
    reached = {}
    for law in LAWS:
        hit = None
        for n in range(50, 2001):
            if evaluate(law, n)['effective_rps'] >= GATEWAY - 0.01:
                hit = n
                break
        reached[law] = hit

    summary = {
        'constants': {'per_node_rps': round(S_NODE, 4), 'gateway_rps': GATEWAY,
                      'delivery_floor': FLOOR, 'machine_usd_s': MACHINE_USD_S,
                      'nodes_for_ceiling': math.ceil(GATEWAY / (S_NODE * FLOOR))},
        'ceiling_reached_at_n': reached,
        'table': table,
    }
    (out / 'complexity_classes.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('nodes needed for the ceiling:', summary['constants']['nodes_for_ceiling'])
    header = f"{'law':<12}" + ''.join(f"{'n=' + str(p):>26}" for p in points)
    print(header)
    for law, row in zip(LAWS, table):
        cells = ''.join(f"{r['nodes']:>8} nd {r['effective_rps']:>7} rps {r['cost_per_mtok']:>5} $".rjust(26)
                        for r in row)
        print(f"{law:<12}{cells}")

    # figure
    INK, MUTED, GRID = '#1a1a1a', '#5a5a5a', '#e3e3e3'
    colours = {'O(1)': '#7f7f7f', 'O(log n)': '#2e75b6', 'O(n)': '#1f4e79', 'O(2n)': '#5b9bd5',
               'O(n log n)': '#c55a11', 'O(n²)': '#a61c00', 'O(cⁿ)': '#7030a0', 'O(nⁿ)': '#000000'}

    def style(ax, title, xlabel, ylabel):
        ax.set_facecolor('white')
        ax.figure.set_facecolor('white')
        for spine in ax.spines.values():
            spine.set_color('#999999')
        ax.tick_params(colors=MUTED, labelsize=8)
        ax.grid(True, color=GRID, linewidth=0.7)
        ax.set_axisbelow(True)
        ax.set_title(title, color=INK, fontsize=10, pad=9)
        ax.set_xlabel(xlabel, color=MUTED, fontsize=8.5)
        ax.set_ylabel(ylabel, color=MUTED, fontsize=8.5)

    xs = np.arange(50, 501, 5)
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.5), facecolor='white')

    ax = axes[0]
    style(ax, 'Machines demanded by each growth class', 'base n', 'nodes (log scale)')
    for law in LAWS:
        ys = [nodes_for(law, int(x)) for x in xs]
        ax.plot(xs, ys, color=colours[law], linewidth=1.7, label=law)
    ax.set_yscale('log')
    ax.axhline(318, color='#999999', linestyle='--', linewidth=1)
    ax.text(52, 360, 'machines needed for the 15.7 req/s ceiling', fontsize=7, color=MUTED)
    ax.legend(frameon=False, fontsize=7.2, ncol=2, labelcolor=MUTED)

    ax = axes[1]
    style(ax, 'Effective throughput for the same classes', 'base n', 'effective req/s')
    for law in LAWS:
        ys = [evaluate(law, int(x))['effective_rps'] for x in xs]
        ax.plot(xs, ys, color=colours[law], linewidth=1.7, label=law)
    ax.axhline(GATEWAY, color='#999999', linestyle='--', linewidth=1)
    ax.set_ylim(0, 17)
    ax.legend(frameon=False, fontsize=7.2, ncol=2, labelcolor=MUTED)

    fig.tight_layout()
    fig.savefig(out / 'figures' / 'fig38_complexity_classes.png', facecolor='white', dpi=300)
    plt.close(fig)
    print('figure ->', out / 'figures' / 'fig38_complexity_classes.png')


if __name__ == '__main__':
    main()
