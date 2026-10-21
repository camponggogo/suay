# Why throughput stops at ~16 req/s, and how far it can be pushed

**Diagnosis note · 2026-10-21** · probe: `sim/gateway/ceiling_probe.py` · runs: `sim/docker/results/{best2,w2b,w4b}`

## 1. Decompose the ceiling, layer by layer

Same client, C=16, 6 s per probe, one gateway worker:

| layer | req/s | p50 | what it contains |
|---|---:|---:|---|
| `/api/health` (raw loop) | 58.7 | 135 ms | uvicorn + routing + JSON only |
| `/v1/models` (auth) | 71.2 | 108 ms | token lookup, scope check, no inference |
| `/v1/chat/completions` | **7.7–15.7** | 994–2 658 ms | policy write + dispatch + upstream + accounting |

The upstream is *not* the limit: the mock answers immediately (its handler has no sleep and no I/O), and it uses
**0.8 % CPU**. The gateway is not network-bound either: 0.078 Mbit/s at 25 req/s is 0.008 % of a 1 GbE link.

The gap between 58–71 req/s (raw) and 15.7 (completion) is the **per-request work executed on the event loop**:
the token-policy write, the dispatch decision, the response accounting and the audit path. At 15.7 req/s with
p50 ≈ 1 000 ms, Little's law gives ~15 in flight, but the loop can only retire ~16 per second — so each request
holds the loop for roughly **60 ms**.

## 2. Proof: workers scale, until the host does not

| configuration | C=8 | C=16 | C=32 | errors |
|---|---:|---:|---:|---:|
| 1 worker (baseline) | 15.0 req/s · 527 ms | 15.7 · 994 ms | — | 0 |
| **2 workers** | **22.3 · 353 ms** | **24.8 · 631 ms** | — | **0** |
| 4 workers | 29.1 · 272 ms | 23.7 · 656 ms | 20.5 · 1 399 ms | 0 |

Two workers add **+48 % at C=8 and +58 % at C=16** with zero errors. Four workers peak higher at C=8 (29.1) but
fall below two workers at C=16 and C=32, and the hub container already sits at **51 % CPU of one core** on an
8-vCPU host shared with 53 other containers.

![fig39](figures/fig39_rps_ceiling.png)

**Figure 39.** Throughput against concurrency for 1, 2 and 4 gateway workers, with the raw-loop ceiling
(58–71 req/s) as a dashed line.

## 3. What the numbers say the limits are, in order

1. **Event-loop time per request (~60 ms)** — the binding constraint at 1 worker.
2. **Host CPU / number of worker processes** — 2 workers ≈ 1.5×, 4 workers ≈ 2× at low load, then flat.
3. **SQLite write serialisation** — not visible up to 4 workers at C≤16 with the 2 s token cache, but it is the
   next wall: every request still performs one budget `UPDATE`.
4. **Upstream** — irrelevant here (mock, 0.8 % CPU). With a real model this becomes the dominant term and the
   gateway ceiling stops mattering.

## 4. Improvement ladder (measured items marked ✓)

| # | Change | Expected | Status |
|---|---|---|---|
| 1 | Node-list cache 5 s (remove one HTTP per request) | 3× | ✓ measured (4.9 → 15.0 at C=8) |
| 2 | **2 gateway workers** | +48–58 % | ✓ measured (15.0/15.7 → 22.3/24.8) |
| 3 | 4 workers for bursty low-concurrency traffic | +16 % at C=8 | ✓ measured (29.1), worse at C≥16 |
| 4 | Move accounting to a bounded queue, flush every 100–200 ms | removes the last blocking write from the loop | not implemented |
| 5 | WAL + `busy_timeout` + a single writer thread | needed before 4+ workers at C≥32 | not implemented |
| 6 | shard the store by token hash across N SQLite files | linear writes | not implemented, only worth it if #4/#5 saturate |
| 7 | `uvloop` in the container | 5–10 % typically | not tested |

The honest expectation for this host: **~25 req/s is the practical ceiling** with 2 workers, ~29 in bursts with
4, and the next real gain (+20–40 %) requires taking the write out of the request path (#4), not more workers.

## 4b. Side effects of N workers (measured)

Ten fresh connections to the 2-worker hub: nine read `events=60, requests=30`, one read `events=2, requests=1`.
Counters and the event deque live in process memory, so they are **divided by N** and worker-dependent; the audit
log, budgets and node liveness are shared and correct. Dashboard sessions see only their own worker's pulses;
revocation lags up to the 2 s cache TTL per worker. Keep 2 workers for throughput, and move counters/events to a
shared table before treating the dashboard as a live monitor.

## 5. What this does *not* mean
The load test uses a mock backend. With a real 0.5B model (21 tok/s, 7.1 s per 150-token answer) a single machine
serves 0.14 req/s, so 50 machines deliver ~7 req/s and the gateway ceiling is irrelevant — the fleet becomes the
limit again. The gateway ceiling matters for short answers, cached prefixes and many small models, which is
exactly the regime this project targets.
