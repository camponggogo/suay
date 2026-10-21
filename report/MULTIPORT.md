# Multi-port, parallel, layered transport: what it buys and what it costs

**Design + measurement note · 2026-10-21** · probes: `sim/gateway/{multiport,parallel_probe,ceiling_probe}.py`
Data: `sim/docker/results/{p1,mp2}` · Figure: `report/figures/fig40_multiport.png`

## 1. What was built

Three topologies on the same host, same 50-machine fleet, same key:

```
A. one port, one process        clients ─▶ :8080 (uvicorn, 1 worker)
B. one port, shared socket      clients ─▶ :8080 (uvicorn, 2 workers, one listen socket)
C. multi-port, parallel accept  clients ─▶ :8082 ─┐
                                clients ─▶ :8083 ─┴─ two processes, one SQLite volume
D. multi-port via L4 proxy      clients ─▶ :8090 (asyncio round-robin) ─▶ :8082 / :8083
```

C and D were added as real containers (`hub2`, `hub3`) so the comparison is measured, not simulated. The L4
dispatcher is 70 lines of asyncio: accept, pick a backend round-robin, splice both directions.

## 2. Results (6 s per point, 0 errors everywhere)

| topology | clients | aggregate req/s | p50 | p95 |
|---|---:|---:|---:|---:|
| A. 1 port, 1 worker | 16 | 15.7 | 994 ms | — |
| B. 1 port, 2 workers | 8 | 22.3 | 353 ms | 736 ms |
| B. 1 port, 2 workers | 16 | 24.8 | 631 ms | 1 317 ms |
| **C. 2 ports, direct** | 16 (8+8) | **26.5** | 567 / 582 ms | 850 ms |
| **C. 2 ports, direct** | 32 (16+16) | **28.8** | 916 / 996 ms | 2 636 ms |
| D. 2 ports via L4 proxy | 16 | 20.8 | 744 ms | 1 339 ms |
| D. 2 ports via L4 proxy | 32 | 19.2 | 1 573 ms | 3 158 ms |

![fig40](figures/fig40_multiport.png)

**Figure 40.** Same workload, four topologies. Ports help only when clients reach them directly; a userspace proxy
on the same host gives most of it back.

## 3. Reading the numbers

1. **Ports add ~16 % over shared-socket workers** (28.8 vs 24.8 at C=32). The mechanism is not "more sockets" —
   both have two processes. It is that each process owns its accept queue and its own kernel-side connection
   distribution, so a burst cannot sit behind one socket's backlog.
2. **A userspace proxy on the same host costs 25–33 %** (20.8 vs 26.5 at C=16). It copies every byte twice and
   competes for the same 8 vCPU; at 25 req/s that is pure loss. If you need fan-in, use a kernel-level load
   balancer (kube Service, haproxy with `splice`, or `SO_REUSEPORT`), not application code.
3. **The ceiling is still the host.** Four workers on one port already reached 29.1 req/s at C=8 and then fell to
   20.5 at C=32. Ports do not create cores: past ~29 req/s this machine is saturated, and the next gain must come
   from removing work per request, not from adding listeners.
4. **Per-port isolation has a non-performance value**: separate ports per tenant or per zone make blast radius and
   traffic accounting obvious, and let one tenant's burst be shaped without touching the others.

## 4. The layered design (L1 / L2 / L3)

The "multi-layer" part is the more interesting half. Split the request path so each layer scales on its own axis:

| layer | responsibility | scaling axis | state in this project |
|---|---|---|---|
| **L1 transport** | accept, HTTP framing, keep-alive, ports | processes × ports, `SO_REUSEPORT` | uvicorn; measured here |
| **L2 policy** | identity, scopes, budgets, model allow-list | cache + stateless workers | 2 s identity cache, atomic `UPDATE` in SQLite |
| **L3 work** | dispatch to machines, upstream call, accounting | async pool + queue | upstream pooled; accounting still synchronous |

What the measurements say about each:

- **L1**: adding ports/processes is linear until CPU saturates (15.7 → 24.8 → 28.8). Beyond that, L1 is not the
  lever.
- **L2**: the policy layer already stops being a bottleneck when identity is cached — `/v1/models` served 71.2
  req/s on one loop versus 15.7 for a completion. The remaining per-request cost sits in L3.
- **L3**: this is where the 60 ms of loop time lives. Moving the budget `UPDATE` and the audit insert to a bounded
  queue with a 100–200 ms flush is the next step; expected **+20–40 %** (not yet measured), and it also makes the
  layer stateless, which is what lets L1 add ports safely.

Recommended composition for this project:

```
clients → kube Service / SO_REUSEPORT          (L1, N ports, no app proxy)
        → gateway worker (stateless)           (L2 policy, 2 s cache)
        → accounting queue → single writer     (L3, batched, off the hot path)
        → node plane / machines                (dispatch)
```

## 5. Production recipe

| goal | configuration | measured / expected |
|---|---|---|
| simplest, one operator | 1 port, 2 workers | 22.3–24.8 req/s |
| max throughput on this host | 2–4 ports, direct clients, 1 worker each | **26.5–28.8 req/s** measured |
| never use | app-level proxy in front on the same host | −25 % (19–21 req/s) |
| next step | L3 accounting queue + single writer | +20–40 % (expected) |

On Linux the same result is achieved with `--workers N` plus `reuse_port=True` (uvicorn ≥ 0.30) — the kernel then
gives each process its own accept queue without extra containers. Windows/Docker Desktop, used here, has no
`SO_REUSEPORT`, which is exactly why separate ports had to be measured explicitly.

## 6. Limits

- Two ports only; 4 and 8 ports would need more vCPU than this host has, so the curve beyond 28.8 rps is unknown.
- The proxy was tested on the same host. A proxy on a separate host would not steal CPU, but would still add a hop.
- All numbers use the mock backend; with a real model the gateway ceiling is irrelevant at 50 machines (≈7 req/s).
- Fairness across ports depends on the client-side distribution (round-robin here, not a real DNS or Service).
