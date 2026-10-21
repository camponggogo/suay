# The configuration that measured best

**Result note · 2026-10-21** · data: `sim/docker/results/best2/summary.json`, `report/STORE.md`, `report/GATEWAY_OPT.md`

## 1. Final stack

| Layer | Choice | Why it won |
|---|---|---|
| Node plane | separate process, in-memory state, 10 s heartbeat, batched flush | removed 25 req/s of heartbeat load from the gateway (`report/SCALING.md`) |
| Machines | **10 % CPU (0.1 core)**, 64 MB | plateau starts at 10 %; more CPU lowered throughput (`report/CPU_SWEEP.md`) |
| Gateway | **2 uvicorn workers**, SQLite (WAL) | 1 worker caps at 15.7 req/s; 2 workers measured 22.3/24.8 req/s with 0 errors (`report/RPS_LIMIT.md`) |
| Upstream client | one pooled `httpx.AsyncClient` per process | removes a handshake per request |
| Token lookup | identity cache 2 s (`SUAY_TOKEN_CACHE_S`) | removes a `SELECT` from the hot path; the atomic budget `UPDATE` still enforces |
| Node list | **5 s cache** around the node-plane lookup | the missing piece: without it every request paid a fresh HTTP call to the plane |
| KV/prefix cache | content-addressed blocks + longest-prefix routing | 157× TTFT on repeated documents (`report/KV_CACHE.md`) |

## 2. Measured effect of the last fix

`dispatch_work()` looked up the live node list on every request. Caching that list for 5 s changed the same
workload from:

| Point | Before the cache | After the cache | Change |
|---|---:|---:|---:|
| C=8 | 4.9 req/s, 1 583 ms | **15.0 req/s, 527 ms** | **3.1× / −67 %** |
| C=16 | 5.3 req/s, 2 833 ms | **15.7 req/s, 994 ms** | **3.0× / −65 %** |

Then the worker re-test, on the same configuration but with two gateway workers:

| Point | 1 worker | **2 workers** | Change |
|---|---:|---:|---:|
| C=8 | 15.0 req/s · 527 ms | **22.3 req/s · 353 ms** | +48 % / −33 % |
| C=16 | 15.7 req/s · 994 ms | **24.8 req/s · 631 ms** | +58 % / −37 % |

4 workers reached 29.1 req/s at C=8 but fell to 23.7 at C=16 and 20.5 at C=32: past two workers the host CPU, not
the loop, sets the ceiling. See `report/RPS_LIMIT.md`.

For reference, the best numbers earlier in the session were 13.4 req/s at C=8 and 17.1 req/s at C=16 (a single
lucky 2-worker run that did not reproduce). The current configuration is **faster at C=8 than anything measured
before, and reproducible**.

## 3. Why not the PostgreSQL path

Postgres + 2 workers was implemented end to end (adapter, pool, compose service, migration of the token table)
and measured, but in this repository it cannot be completed: `versions/python/control/app.py` still creates
`users`/`sessions`/`audit` in SQLite and that file is blocked by the artifact scanner. Running the hot path on
PG while the rest stays on SQLite produced 4.5 req/s at C=8 with errors — worse than the SQLite path. The
adapter stays in the tree for the day the control plane moves.

## 4. Reproduce / operate

```sh
cd sim/docker && docker compose up -d          # 1 hub worker, node plane, 50 nodes at 0.1 CPU
python sim/docker/loadgen.py --base http://127.0.0.1:8080 --key suay_sim_loadgen_key \
    --model sim-model --steps 8,16 --seconds 6 --out sim/docker/results/best2
```

Keep `SUAY_TOKEN_CACHE_S` at 1–2 s (revocation window) and the node cache at 5 s (a machine that dies is still
skipped by the liveness check on the next refresh).

## 5. Limits

- **Per-worker state.** With 2 workers the in-memory counters and the event stream are per process: ten fresh
  connections read `events=60` nine times and `events=2` once. Budgets, audit and liveness are shared and correct.
  If the dashboard must be a live monitor, pin it to one worker or move counters/events to a shared table.
- Single host: 8 vCPU shared by 53 containers, Docker Desktop and the load generator; ±15 % run-to-run.
- The mock backend answers instantly, so these numbers isolate gateway and control-plane cost.
- The 5 s node cache means a freshly started machine can wait up to 5 s before receiving work.
