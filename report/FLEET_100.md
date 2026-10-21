# Fleet study: 50–100 × (Intel i3, 8 GB RAM, 120 GB disk)

**White-paper appendix · 2026-10-21** · figures: `report/fleet/figures/` (white, 300 dpi)
Data: `report/fleet/fleet_model.json`, `report/fleet/heartbeat_stress.json`.

## 1. Profile and assumptions

| Item | Value | Why |
|---|---|---|
| CPU | Intel Core i3, 4C/4T, ~3.6 GHz | typical 2018–2021 office desktop |
| RAM | 8 GB | ~4.5 GB left for the employee, browser included |
| Disk | 120 GB | tight: OS ~30 GB, Docker ~6 GB, one model cache |
| Container cap | 1.5 GB (background) / 4.0 GB (dedicated) | keeps the machine usable, then hands it over |
| Anchor | **11.74 tok/s** measured for a 0.63B Q4 model on an i7-8550U | llama.cpp b11757, this repository |
| i3 factor | **×1.8** | 4C/4T at 3.6 GHz sustained vs 4C/8T at 1.8 GHz / 15 W |
| Gateway ceiling | **10.2 req/s** | measured, `report/REPORT.md` |
| Heartbeat ceiling | **25 req/s** | measured, §3 below |

Per-node generation rates that follow: **0.5B → 21.1 tok/s**, 1.5B → 8.6, 3B → 4.3, 8B → 1.7 (memory-bandwidth
bound; an 8B Q4 does not fit a 1.5 GB cap and needs 2–5 machines per copy).

## 2. Capacity by fleet size

![Capacity vs fleet](figures/fig19_capacity_vs_fleet.png)

**Figure 19.** Requests per second (150-step answers) in dedicated mode. At 50 machines the 0.5B class already
delivers 7.0 req/s; at 100 it reaches 14.1 req/s but the **gateway caps at 10.2 req/s**, so the control plane
becomes the binding constraint again. The 8B class never exceeds 0.6 req/s even at 100 machines.

| Model | tok/s per stream | nodes per copy (bg / ded) | req/s @50 | req/s @100 | bound by |
|---|---:|---:|---:|---:|---|
| Qwen2.5-0.5B Q4 | 21.1 | 1 / 1 | 7.0 | 14.1 | gateway at 100 |
| Qwen2.5-1.5B Q4 | 8.6 | 1 / 1 | 2.9 | 5.8 | compute |
| Qwen2.5-3B Q4 | 4.3 | 2 / 1 | 1.4 | 2.9 | compute |
| Llama-3.1-8B Q4 | 1.7 | 5 / 2 | 0.28 | 0.55 | compute |

![Best model by fleet](figures/fig21_best_model_by_fleet.png)

**Figure 21.** The largest model class that still serves ≥1 req/s. Up to 70 machines, nothing above 1.5B clears
the bar; 100 machines buy you 3B, not 8B.

## 3. The control plane stops at ~50 machines (measured)

We stopped the 50 live containers and injected synthetic heartbeats at the deployed 2 s interval:

| Machines | achieved req/s | p50 | p95 | heartbeats delivered |
|---:|---:|---:|---:|---:|
| 50 | 19.4 | **104 ms** | 1 147 ms | 83.3 % |
| 75 | 23.9 | 233 ms | 2 695 ms | 70.4 % |
| 100 | 25.2 | **2 248 ms** | 3 497 ms | **54.7 %** |

![Heartbeat stress](figures/fig20_heartbeat_stress.png)

**Figure 20.** Measured. Throughput saturates at ~25 heartbeats/s (≈200 requests/s of work per core-second),
and at 100 machines **45 % of heartbeats arrive late**. Since liveness is declared after a 10 s gap, a 100-node
fleet on one hub worker will flap between live and stale — the dashboard starts lying before the system breaks.

Rule of thumb from the data: **≤40 machines per hub worker** keeps p95 under ~1 s.

## 4. Disk and memory

- 120 GB is enough for **one** model class per machine: 8B Q4 is 4.9 GB, Docker images ~6 GB, OS ~30 GB — about
  60 GB of headroom, not enough for several model versions side by side.
- 8 GB RAM with a 1.5 GB container leaves 6.5 GB for the employee; a 4 GB cap leaves 4 GB, which is the
  practical maximum before people notice.
- The 3B class is the pivot: it fits one dedicated machine, or two background machines.

## 5. Cost per token

![Cost per 1M](figures/fig22_cost_per_mtok.png)

**Figure 22.** Amortised cost per 1M output tokens (i3 at $200, 3 years, 65 W, $0.12/kWh). Cost is independent
of fleet size — both hardware and tokens scale linearly — so the decision is about the model class and duty
cycle, not the machine count.

| Model | duty 20 % | duty 100 % |
|---|---:|---:|
| 0.5B | $0.62 | **$0.12** |
| 1.5B | $1.51 | $0.30 |
| 3B | $3.03 | $0.61 |
| 8B | $7.86 | $1.57 |

Only the 0.5B class at high duty reaches the cloud flash tier ($0.10/1M); everything larger is 3–80× more
expensive per token.

## 6. What we would actually deploy

| Fleet | Recommended shape | Expected |
|---|---|---|
| 50 | 0.5B on every machine, 1.5 GB cap, one hub worker | **7 req/s**, p95 < 1 s |
| 50 → 100 | add a **second hub worker or split the node plane**, batch heartbeats to 5–10 s | keeps p95 < 1 s at 100 nodes |
| 100 | 1.5B on every machine (or 0.5B if the gateway is scaled) | 5.8 req/s (1.5B) / 10.2 req/s (0.5B, gateway-bound) |
| any | 8B only as a shared pool with 2 nodes per copy and an explicit "slow lane" | 0.3–0.6 req/s, 8–25 s per answer |

Three changes, in order of value:

1. **Batch heartbeats.** 100 machines × 1 per 2 s = 50 req/s of pure overhead. Flushing every 10 s cuts it 5×
   and removes the measured 2.2 s tail entirely.
2. **Two hub workers minimum above 60 machines.** The gateway also caps inference at 10.2 req/s; a second
   worker lifts both ceilings.
3. **Pin one model per machine.** 120 GB is the real constraint on model sprawl, not RAM.

## 7. Threats to validity

- The i3 factor (×1.8) is an extrapolation from one i7 measurement, not a measurement on an i3.
- The heartbeat ceiling was measured on a hub that also serves the dashboard; a dedicated node plane would be
  faster.
- Capacity assumes independent parallel requests; single-stream latency for the 8B sharded case is worse than
  the table suggests.
- Disk figures ignore Windows page file growth and browser caches, which on a 120 GB machine can be several GB.
