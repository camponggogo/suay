# Scaling the node plane: from 50 machines to an unbounded fleet

**Engineering note · 2026-10-21** · figures: `report/fleet/figures/fig23..fig24` (white, 300 dpi)
Data: `report/fleet/throughput_sweep.json`, `report/fleet/scale_test.json`, `report/fleet/plane*.db`

## 1. The problem we measured

The previous note showed the control plane topping out at **~25 heartbeats/s** with a single worker: at 100
machines only **54.7 %** of heartbeats arrived on time, p50 rose to **2.2 s**, and the dashboard would start
flapping nodes between `live` and `stale`.

Root causes, all on the hot path of every heartbeat: JSON parse → SHA-256 key compare → SQLite read → SQLite
write ×2 → audit row → response. Five serial operations per machine per interval, in one Python process, mixed
with inference traffic.

## 2. The fix: a separate, memory-first node plane

| Change | Why it removes the ceiling |
|---|---|
| **Own process and port** (`nodeplane:8081`) | inference traffic and 10 000 heartbeats no longer share one event loop |
| **State in memory** (`dict[node_id] = {...}`) | a heartbeat is a dict update, not a transaction |
| **Batched flush** every 10 s, one transaction | SQLite sees 1 write per 10 s instead of 2 per heartbeat |
| **Batch payloads** (`{"nodes": [...]}`) | a site collector can register 100 machines with one request |
| **Shard by `crc32(node_id) % n`** | capacity grows linearly: add a replica, move a slice of the fleet |
| **`/aggregate`** merges shards | the dashboard still sees one fleet |

The change is **opt-in**: `SUAY_PLANE=http://nodeplane:8081` switches a machine over; unset it and the old path
is used. The compose file now enables it for the 50-machine fleet, with heartbeats at **10 s** instead of 2 s
(5× less traffic, and 10 s is still inside the 30 s staleness window).

## 3. What we measured

![Throughput old vs plane](figures/fig23_throughput_old_vs_plane.png)

**Figure 23.** Heartbeat throughput against concurrent senders. The old path peaks at **44 req/s** and then
*falls* as the single worker thrashes; the node plane peaks at **161 req/s** and only drops when the load
generator itself saturates (annotated).

| Path | Serial latency (p50) | Peak throughput (one client) |
|---|---:|---:|
| Old hub path (SQLite per request) | 67 ms | **44 req/s** |
| Node plane (memory + batch flush) | **3.1 ms** | **161 req/s** |

Measured with independent processes, so the *server* is the only variable:

```
shard 1 (port 8081), 4 concurrent clients   -> 133.0 req/s, p50 28 ms
shard 2 (port 8082), 4 concurrent clients   -> 133.7 req/s, p50 27 ms
combined                                    -> 266.7 req/s   (linear, no shared lock)
```

![Nodes supported](figures/fig24_nodes_supported.png)

**Figure 24.** Machines supported = `130 req/s per shard × shards × interval`. One shard carries **1 300
machines** at a 10 s interval; four shards carry **5 200**; at the original 2 s interval you need four shards
for 1 000 machines. Memory per node is a few hundred bytes, so 10 000 nodes is single-digit megabytes.

### End-to-end effect on the running fleet

With 50 containers switched to the plane at a 10 s interval:

| Metric | Before (2 s, hub path) | After (10 s, node plane) |
|---|---:|---:|
| Heartbeat load on the hub | 24.6 req/s | **0** (moved to the plane) |
| Inference at C=1 (mean) | 210 ms | **105 ms** |
| Nodes visible to the dashboard | 50 | 50 (via `/aggregate` proxy) |

The gateway still saturates at ~10 req/s at higher concurrency — that is the inference ceiling measured in
`report/REPORT.md`, a separate fix (worker count, connection pooling, token cache). The node plane deliberately
does **not** pretend to solve it.

## 4. Operating envelope

| Fleet | Interval | Shards | Expected p95 |
|---:|---:|---:|---|
| 50 | 10 s | 1 | < 50 ms |
| 1 000 | 10 s | 1–2 | < 100 ms |
| 5 000 | 10 s | 4 | < 150 ms |
| 10 000 | 10 s | 8 | < 200 ms |
| 1 000 | 2 s | 4 | < 100 ms |

Rules of thumb:

1. **One shard per ~130 req/s of heartbeat traffic**, with 2× headroom (the measured peak).
2. Keep the interval ≥10 s; below that you pay 5× for no operational benefit inside a 30 s staleness window.
3. Put the plane on its own process, never inside the inference gateway.
4. Alert on `flush_count` stalling: a failed flush is silent by design (memory keeps serving), so the database
   is the thing that can rot unnoticed.

## 5. What still does not scale

- **The inference gateway** (10.2 req/s measured) is unchanged. At 1 000 machines, the node plane is no longer
  the bottleneck; the gateway is.
- **SQLite as a shared store** is fine for one plane, not for eight writing concurrently. Shards write to their
  own file, or to Postgres/Redis at real scale.
- **`/aggregate` fan-out** is O(shards) per dashboard refresh; at 8 shards it is still trivial, at 64 you want a
  pre-aggregated rollup.

## 6. How to enable / roll back

```yaml
# docker-compose.yml (already applied)
nodeplane:
  command: ["uvicorn", "node_plane:app", "--host", "0.0.0.0", "--port", "8081"]
  environment: { SUAY_FLUSH_S: "10", SUAY_SWARM_KEY: sim-swarm-key }
node-a:
  environment: { SUAY_PLANE: "http://nodeplane:8081", SUAY_HEARTBEAT_S: "10" }
hub:
  environment: { SUAY_NODE_PLANE: "http://nodeplane:8081" }
```

Roll back by removing `SUAY_PLANE` from the node services and `SUAY_NODE_PLANE` from the hub; no schema change
is involved, and the plane's SQLite rows are the same shape as before.

## 7. Threats to validity

- Peak throughput was measured on one 4-core laptop also running 50 containers; a dedicated host will do better.
- The 130 req/s per shard is a planning number with 20 % headroom below the 161 req/s measured peak.
- Batch payloads are supported but not exercised at scale in this test (machines posted individually).
- No auth beyond the shared swarm key; a public deployment needs per-node credentials and rate limits.
