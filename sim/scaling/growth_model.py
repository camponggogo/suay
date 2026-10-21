"""Growth model: N+1 nodes vs N·log2(N) nodes, with the obstruction factors measured in this project.

Measured inputs (all from earlier reports):
  * per-node service rate     0.141 req/s  (150 tokens at 21.13 tok/s on an i3-class machine)
  * gateway ceiling           15.7 req/s   (best stable configuration, one worker)
  * heartbeat delivery        0.833 @50 nodes, 0.704 @75, 0.547 @100  -> exp decay ~0.0085/node above 30
  * node-plane capacity       130 req/s per shard (measured), one heartbeat per node per 10 s
  * dispatch RTT              28 ms @50 nodes, 40 ms @80 (CPU sweep with 10 % CPU)

    python sim/scaling/growth_model.py --out report/growth
"""
import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

S_NODE = 150.0 / (150.0 / 21.13)      # requests per second one machine can finish, sequentially
S_NODE = 21.13 / 150.0                # = 0.1409 req/s
GATEWAY = 15.7                        # measured stable ceiling
DELIVERY_DECAY = 0.0085               # per node above 30, fitted to 0.833/0.704/0.547
SHARD_RPS = 130.0                     # node-plane capacity per shard
HEARTBEAT_S = 10.0


def delivery(nodes):
    if nodes <= 30:
        return 1.0
    return max(0.35, math.exp(-DELIVERY_DECAY * (nodes - 30)))


def dispatch_ms(nodes):
    return 28.0 + max(0.0, nodes - 50) * 0.4


def evaluate(nodes):
    node_capacity = nodes * S_NODE * delivery(nodes)
    effective = min(GATEWAY, node_capacity)
    heartbeat = nodes / HEARTBEAT_S
    return {
        'nodes': nodes,
        'node_capacity_rps': round(node_capacity, 2),
        'gateway_bound': node_capacity > GATEWAY,
        'delivery_factor': round(delivery(nodes), 3),
        'effective_rps': round(effective, 2),
        'capacity_per_100_nodes': round(100 * effective / nodes, 2),
        'heartbeat_rps': round(heartbeat, 1),
        'shards': math.ceil(heartbeat / SHARD_RPS),
        'dispatch_ms': round(dispatch_ms(nodes), 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='report/growth')
    args = parser.parse_args()
    out = Path(args.out)
    (out / 'figures').mkdir(parents=True, exist_ok=True)

    bases = [10, 25, 50, 100, 200, 500]
    rows = []
    for base in bases:
        linear = base + 1
        growth = int(round(base * math.log2(base)))
        rows.append({'base': base, 'law': 'N+1', 'result': evaluate(linear)})
        rows.append({'base': base, 'law': 'N·log2(N)', 'result': evaluate(growth)})

    # closed-form crossovers
    n_saturate = GATEWAY / S_NODE                     # nodes whose compute fills the gateway
    n_collapse = 30 + math.log(0.35) / -DELIVERY_DECAY  # where delivery hits its floor
    summary = {
        'per_node_rps': round(S_NODE, 4),
        'gateway_rps': GATEWAY,
        'nodes_to_saturate_gateway': round(n_saturate, 1),
        'delivery_floor_node': round(n_collapse, 1),
        'table': rows,
    }
    (out / 'growth.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'table'}, indent=2))
    for row in rows:
        r = row['result']
        print(f"base {row['base']:>4} {row['law']:<9} nodes {r['nodes']:>5}  eff {r['effective_rps']:>7} rps  "
              f"delivery {r['delivery_factor']:>5}  shards {r['shards']:>2}  dispatch {r['dispatch_ms']:>5} ms")

    # figure
    INK, MUTED, GRID = '#1a1a1a', '#5a5a5a', '#e3e3e3'
    BLUE, ORANGE = '#1f4e79', '#c55a11'

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

    xs = np.arange(2, 501)
    linear_eff = np.array([evaluate(int(x))['effective_rps'] for x in xs])
    growth_nodes = np.round(xs * np.log2(xs)).astype(int)
    growth_eff = np.array([evaluate(int(n))['effective_rps'] for n in growth_nodes])

    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.4), facecolor='white')
    ax = axes[0]
    style(ax, 'Effective throughput by growth law (measured factors)', 'base N', 'effective requests/s')
    ax.plot(xs, linear_eff, color=BLUE, linewidth=2, label='nodes = N+1')
    ax.plot(xs, growth_eff, color=ORANGE, linewidth=2, label='nodes = N·log₂(N)')
    ax.axhline(GATEWAY, color='#999999', linestyle='--', linewidth=1, label=f'gateway ceiling {GATEWAY} req/s')
    ax.axvline(n_saturate, color='#bbbbbb', linestyle=':', linewidth=1)
    ax.text(n_saturate + 6, 3, f'compute fills gateway\nat N≈{n_saturate:.0f}', fontsize=7, color=MUTED)
    ax.set_xlim(0, 500)
    ax.set_ylim(0, 18)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)

    ax = axes[1]
    style(ax, 'Efficiency and heartbeat cost', 'nodes', 'delivery factor / shards')
    nodes = np.arange(10, 501)
    ax.plot(nodes, [delivery(n) for n in nodes], color=BLUE, linewidth=2, label='heartbeat delivery factor')
    ax.plot(xs, [evaluate(int(x))['shards'] / 10 for x in xs], color=ORANGE, linewidth=2,
            label='node-plane shards / 10')
    ax.set_xlim(0, 500)
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)

    fig.tight_layout()
    fig.savefig(out / 'figures' / 'fig37_growth_laws.png', facecolor='white', dpi=300)
    plt.close(fig)
    print('figure ->', out / 'figures' / 'fig37_growth_laws.png')


if __name__ == '__main__':
    main()
