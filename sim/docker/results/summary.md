# 50-machine simulation — measured results

Run on 2026-10-21 (Asia/Bangkok) with Docker Desktop 29.8.2 on Windows, 8 vCPU / 8.2 GB assigned to the VM.

## Topology

| Component | Count | Notes |
|---|---|---|
| `node-a` / `node-b` / `node-c` | 20 / 20 / 10 | simulated machines in zones `floor-1`, `floor-2`, `floor-3`; heartbeat every 2 s |
| `hub` | 1 | real SUAY control plane + token-policy middleware, single uvicorn worker |
| `upstream` | 1 | mock OpenAI-compatible backend, returns immediately |

All 50 nodes reported live throughout the sweep (`nodes_live = 50`, 0 errors).

## Method

`loadgen.py` warms the path, then drives `/v1/chat/completions` for 8 s at concurrency 1, 5, 10, 25 and 50.
Each request is a real authenticated call: bearer key → scope check → per-key model catalog → atomic request
budget → upstream call → usage accounting. Latency is measured per request around the round trip.

## Results

| Concurrency | Requests | RPS | mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | Errors |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 40 | 4.9 | 202 | 166 | 419 | 542 | 542 | 0 |
| 5 | 60 | 7.3 | 675 | 695 | 939 | 988 | 992 | 0 |
| 10 | 70 | 8.1 | 1,191 | 1,125 | 1,787 | 1,920 | 1,935 | 0 |
| 25 | 89 | 9.1 | 2,508 | 2,589 | 2,959 | 2,984 | 2,992 | 0 |
| 50 | 122 | 12.0 | 3,811 | 3,811 | 5,364 | 5,509 | 5,512 | 0 |

Chart: `response_time_report.png` (percentiles, throughput, distribution). Raw samples: `latency.csv`.
Machine-readable: `summary.json`.

## What the numbers say

1. **Latency grows roughly linearly with concurrency** (166 ms → 3,811 ms p50) while **throughput plateaus at
   ~12 requests/s**. Classic queueing: clients wait behind a service that is already at capacity.
2. **The ceiling is the gateway, not the model.** The mock backend answers instantly, so essentially all of
   the 166 ms at concurrency 1 is gateway overhead: bearer hashing, SQLite read + two writes, an extra HTTP hop
   to the upstream, and response re-buffering in the middleware.
3. **Background heartbeats already consume the same budget.** 50 machines at one heartbeat per 2 s produce
   ~12–25 requests/s to the same single uvicorn worker — the same order of magnitude as the inference
   throughput. Isolation testing on an idle hub would show a higher ceiling.
4. **Zero errors up to 50 concurrent clients.** The token layer degrades by queueing, not by failing, which is
   the right failure mode for an internal gateway.

## Where the next 10x comes from

| Change | Expected effect |
|---|---|
| Run uvicorn with `--workers 4` and SQLite in WAL mode | queueing split across cores; watch for write contention |
| Move heartbeats to a cheaper path (in-memory ring, flush every 5 s) | frees ~12–25 req/s for inference |
| Cache token lookups (hash → row, 5 s TTL) | removes a DB read from every inference request |
| Keep one pooled upstream connection per worker | removes TCP setup from the critical path |
| Separate the node plane onto its own port/process | a noisy fleet cannot starve inference |

## Honest limits

- The backend is a mock; these numbers measure **gateway and transport**, not LLM inference. A real 8B model on
  CPU is orders of magnitude slower.
- 52 containers share one host and one Docker VM, so this is not 50 physical office PCs.
- Docker Desktop on Windows adds a VM network hop to every request; on a bare-metal Linux host the absolute
  numbers would be lower.
- Heartbeat traffic runs during the sweep by design; it is part of the measured load, not noise removed.
