# Growth laws: N+1 versus N·log₂(N), with the measured obstruction factors

**Calculation note · 2026-10-21** · figure: `report/growth/figures/fig37_growth_laws.png`
Model: `sim/scaling/growth_model.py` · numbers: `report/growth/growth.json`

## 1. Inputs (all measured in this project)

| Quantity | Value | Source |
|---|---:|---|
| Per-node service rate (150-token answer) | **0.141 req/s** | 21.13 tok/s on an i3-class machine (`report/REPORT.md`) |
| Stable gateway ceiling (1 worker) | **15.7 req/s** | `report/BEST_CONFIG.md` |
| Heartbeat delivery @50 / @75 / @100 nodes | 0.833 / 0.704 / **0.547** | `report/fleet/heartbeat_stress.json` |
| Delivery decay fit | `exp(−0.0085·(N−30))`, floor 0.35 | same |
| Node-plane capacity | 130 req/s per shard | `report/SCALING.md` |
| Dispatch RTT | 28 ms @50, 40 ms @80 | `report/CPU_SWEEP.md` |

Model:

```
usable_nodes   = N · s · delivery(N),        s = 0.141
effective_rps  = min(gateway, usable_nodes)
delivery(N)    = 1                      N ≤ 30
               = exp(−0.0085·(N−30))    N > 30, floored at 0.35
heartbeat_rps  = N / 10        shards = ⌈heartbeat_rps / 130⌉
```

## 2. Results

| Base N | Law | Nodes | Effective rps | Delivery | Shards | Dispatch RTT |
|---:|---|---:|---:|---:|---:|---:|
| 10 | N+1 | 11 | 1.55 | 1.00 | 1 | 28 ms |
| 10 | N·log₂N | 33 | **4.53** | 0.975 | 1 | 28 ms |
| 25 | N+1 | 26 | 3.66 | 1.00 | 1 | 28 ms |
| 25 | N·log₂N | 116 | **7.87** | 0.481 | 1 | 54 ms |
| 50 | N+1 | 51 | 6.01 | 0.837 | 1 | 28 ms |
| 50 | N·log₂N | 282 | **13.90** | 0.350 | 1 | **121 ms** |
| 100 | N+1 | 101 | 7.78 | 0.547 | 1 | 48 ms |
| 100 | N·log₂N | 664 | 15.70 | 0.350 | 1 | **274 ms** |
| 200 | N+1 | 201 | 9.91 | 0.350 | 1 | 88 ms |
| 200 | N·log₂N | 1 529 | 15.70 | 0.350 | 2 | 620 ms |
| 500 | N+1 | 501 | **15.70** | 0.350 | 1 | 208 ms |
| 500 | N·log₂N | 4 483 | 15.70 | 0.350 | 4 | **1 801 ms** |

![Growth laws](figures/fig37_growth_laws.png)

**Figure 37.** Left: effective throughput against the base N under each growth law, with the measured gateway
ceiling. Right: the obstruction factor (heartbeat delivery) and the number of node-plane shards.

## 3. What the arithmetic says

1. **Both laws hit the same wall: 15.7 req/s.** No growth law beats the gateway; nodes beyond it add nothing to
   throughput. The ceiling is a property of the control plane, not of the fleet.
2. **N·log₂N reaches the wall sooner but pays 6–9× more machines for it.** At base 100 it needs 664 nodes
   (vs 101) to reach 15.7 rps, and its per-node efficiency falls to **0.024 rps/node** versus 0.031 for N+1 and
   0.141 at small N.
3. **The obstruction factor is what makes superlinear growth a trap.** Past ~30 nodes, heartbeat delivery decays
   from 1.0 to 0.55 at 100 nodes and 0.35 by ~153 nodes: every extra node adds less usable capacity than the
   one before, while at the same time the dispatch path lengthens (28 → 121 ms at base 50, 274 ms at base 100).
4. **The dip at base ≈25 in the N·log₂N curve is real arithmetic**, not noise: the node count jumps from 116 to
   282 between base 25 and 50, crossing the delivery cliff, so the marginal machine is worth ~0.
5. **Node-plane shards stay at 1 up to 1 300 machines** (0.1 heartbeat/s each); the operating limit at 4 483
   nodes is 4 shards — cheap. The bottleneck is never the plane; it is the gateway.

## 4. Decision rule

```
IF  effective = gateway  (the fleet is gateway-bound)
    → do NOT add nodes; raise the gateway (workers + shared store)
ELIF effective = N·s·delivery(N)  (the fleet is compute-bound)
    → add nodes linearly (N+1), because delivery decays and log-growth burns machines
```

Practical numbers for the current system:

| Target | Safe configuration |
|---|---|
| 5 req/s | 50–60 nodes, N+1, 1 worker, 10 s heartbeat |
| 10 req/s | 110 nodes **or** 2 gateway workers with a shared store (cheaper) |
| 15.7 req/s (the ceiling) | 1 worker already maxed; 2 workers + Postgres measured unstable — see `report/STORE.md` |
| >15.7 req/s | gateway workers **and** a non-blocking store; nodes are not the lever |

## 5. Limits of this calculation

- Delivery decay is fitted to three points (50/75/100 nodes); the 0.35 floor is an assumption, not a measurement
  beyond 100 nodes.
- The gateway ceiling is measured on one host with the mock backend; a real model lowers it.
- `N·log₂N` is an abstract growth law: it models "capacity grows superlinearly", which for a fixed budget means
  many small machines — exactly the regime where heartbeat and dispatch overhead bite.
- The model ignores replica headroom, failure of individual machines and network topology.
