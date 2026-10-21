# Can the gateway be improved further? Micro-optimisations vs. worker count

**Measurement note · 2026-10-21** · figure: `report/gateway/figures/fig33_gateway_workers.png`
Runs: `sim/docker/results/{opt,opt2,opt3,opt4,opt5}/summary.json` (50 machines at 10 % CPU)

## 1. What was changed

| Change | Rationale |
|---|---|
| One pooled `httpx.AsyncClient` per process instead of a new client per request | removes a TCP handshake from every call |
| Token identity cache, 2 s TTL (`SUAY_TOKEN_CACHE_S`) | removes a SQLite `SELECT` from every request; the atomic budget `UPDATE` still runs |
| `uvicorn --workers 2` / `4` | the actual ceiling is one event loop |

## 2. Results

![Gateway workers](figures/fig33_gateway_workers.png)

**Figure 33.** Throughput and mean latency by worker count (C=8/16/32, 6 s per point).

| Configuration | C=8 | C=16 | C=32 |
|---|---:|---:|---:|
| 1 worker (baseline) | 12.7 req/s | 9.7 | 11.3 |
| 1 worker + pooling + token cache | 9.7 – 12.7 (five runs) | — | — |
| **2 workers** (best run) | 12.9 | **17.1** | **16.3** |
| 2 workers (repeat run, same config) | 6.4 | 7.5 | 2.1 |
| 4 workers | 10.5 | 16.6 | **7.3** + 1 error |

## 3. What this means

1. **The micro-optimisations are inside the noise.** Five single-worker runs at C=8 gave 8.4, 9.7, 10.7, 11.7 and
   12.7 req/s. Pooling and the token cache do not show up above that spread on this host — loopback handshakes
   and one indexed `SELECT` were never the bottleneck.
2. **Worker count is the real lever, but it is not yet safe.** Two workers reached **17.1 req/s at C=16
   (+81 %)** and 16.3 at C=32 (+45 %) in one run; the identical configuration later collapsed to 2.1 req/s at
   C=32 with 12 s latencies. Four workers produced request errors at C=32. The cause is visible in the logs:
   several processes writing the same SQLite file serialise on the write lock, and a stalled writer blocks the
   event loop.
3. **So the honest answer to "can it be improved further?" is: yes, but not by tuning this process.** The next
   step is a shared store that does not block (SQLite in WAL mode as the minimum, Postgres/Redis for real
   scale), plus per-worker metrics aggregation. Until then, one worker is the only stable configuration.

## 4. Current state (kept)

- 1 uvicorn worker, 50 machines at 10 % CPU, node plane at a 10 s heartbeat.
- Pooled upstream client and 2 s token cache are **enabled** — they cost nothing and remove work from the path,
  even though the gain is not measurable at this load.
- Security note: a revoked token can still be accepted for up to `SUAY_TOKEN_CACHE_S` (2 s). Set it to 0 to
  disable the cache, or keep it at 1 s for stricter revocation.

## 5. Next step, in order

| Step | Expected | Why it is the right next move |
|---|---|---|
| SQLite `PRAGMA journal_mode=WAL` + one writer queue | makes 2–4 workers stable | removes the write-lock stall that broke every multi-worker run |
| Shared counters (Redis or a per-worker `/metrics` fan-in) | correct dashboard with N workers | the current counters are per process |
| Re-run this harness at 2 and 4 workers | decide the final worker count | the measurement already exists; only the store changes |
| Then, and only then, raise machine CPU above 10 % | nothing — measured plateau | `report/CPU_SWEEP.md` |

## 6. Threats

- Single host, 8 vCPU, 53 containers and Docker Desktop in the same box; run-to-run spread at C=8 is ±30 %.
- 6 s per load level; the 2-worker collapse was observed twice (C=32 and the post-patch run) but not captured
  with server-side logs at debug level.
- The mock upstream answers instantly, so these numbers isolate gateway overhead, not model serving.
