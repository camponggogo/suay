# 50-machine Docker simulation

Three services, one image:

| Service | Replicas | Role |
|---|---|---|
| `upstream` | 1 | Mock OpenAI-compatible backend (JSON + SSE), fixed `usage` |
| `hub` | 1 | Real SUAY control plane + token-policy middleware + node heartbeat API |
| `node-a` / `node-b` / `node-c` | 20 / 20 / 10 | Simulated office machines, heartbeat every 2 s |

Total simulated machines: **50**, across three zones (`floor-1`, `floor-2`, `floor-3`).

## Run

```sh
cd sim/docker
docker compose up -d --build
docker compose ps --format 'table {{.Service}}\t{{.Status}}' | head -8
```

Wait until `hub` is healthy, then from the repository root:

```sh
python sim/docker/loadgen.py --base http://127.0.0.1:8080 --key suay_sim_loadgen_key \
    --steps 1,5,10,25,50 --seconds 8 --out sim/docker/results
python sim/docker/plot.py --results sim/docker/results
```

Shut down:

```sh
cd sim/docker && docker compose down -v
```

## What is measured

`loadgen.py` drives the **real** gateway path — token auth, per-key model catalog, request/token budget,
usage accounting — against the mock backend, at concurrency 1, 5, 10, 25 and 50 for 8 seconds each.
For every request it records round-trip milliseconds; `summary.json` keeps p50/p95/p99, mean, max,
throughput and error count per step, together with the number of live simulated machines reported by the hub.

`plot.py` renders `results/response_time_report.png`:

1. p50 / p95 / p99 response time vs concurrency (log-log)
2. throughput vs concurrency
3. response-time distribution per concurrency (box plot)

## Neural view

The admin hub also serves a live topology view where every simulated machine is a dot and every link is a
dashed fibre — a dot-to-dot "neural fabric" of the fleet:

```
http://127.0.0.1:8080/neural
```

- 50 machines are drawn as neurons on three concentric bands, one band per zone; slight seeded jitter keeps
  the layout organic instead of clock-like.
- Each neuron has a dashed curved fibre to the core, plus lateral fibres to its two nearest neighbours in the
  same zone and a few long-range fibres across zones — the cortex is not only local.
- Small bright pulses travel along the fibres every ~120 ms; the rate reflects live heartbeats.
- Colour encodes state: teal/zone colour = live, amber = stale signal, rose = offline.
- Hover shows node id, zone, heartbeat count and age; click pins a node and dims everything outside its
  two-hop neighbourhood; `Esc` clears.
- Data comes from `GET /api/topology` (nodes + links + zone counts + stats), refreshed every 3 s.
- The renderer is plain canvas 2D, no external libraries, and honours `prefers-reduced-motion`.

Screenshot: `results/neural-view.png`.

Wiring note: the three static files live in `versions/python/control/static/` (`neural.html`, `neural.js`,
`neural.css`). The simulation hub serves them; the production control plane needs three small routes
(`/neural`, `/neural.js`, `/neural.css`) plus `/api/topology` before the same page works there — that file is
currently blocked by the workspace artifact scanner.

## Neural view (3D)

`http://127.0.0.1:8080/neural` renders the fleet with **Three.js r180** (vendored at
`versions/python/control/static/vendor/`, MIT, no CDN — works on an offline LAN):

- every machine is a glowing dot on one of three tilted orbital rings, one ring per zone;
- each dot is joined to `SUAY CORE` by a **dashed fibre**, with lateral fibres to its neighbours and a few
  long-range fibres between rings;
- pulses travel along the fibres (~120 ms apart) so the mesh reads as a firing neural network;
- drag to orbit, wheel to zoom, hover for a tooltip, click to pin a node and dim everything outside its
  two-hop neighbourhood, `Esc` to clear;

### Pulses are driven by real traffic

Nothing in the view pulses on a timer. The hub records one event per observed exchange and the page replays
them as fireballs travelling along the exact fibre, in the real direction:

| Event | Direction | Produced by | Travel time |
|---|---|---|---|
| `heartbeat` | node → core | every machine's 2 s heartbeat | fixed 0.42 s |
| `ack` | core → node | hub reply to that heartbeat | fixed 0.30 s |
| `request` | client → core | an authenticated `/v1/chat/completions` call | core flash |
| `dispatch` | core → node | the hub's real `POST http://<node-ip>:9100/work` call | from measured RTT |
| `result` | node → core | that call returning | from measured RTT |
| `response` | core → client | upstream answer relayed back | from measured RTT |

Each fireball is a white-hot additive sprite tinted with the node's zone colour; the fibre it is crossing
brightens for about 0.4 s. Because travel time comes from the measured round trip, a slow machine visibly
trails behind a fast one. The hub keeps a rolling 800-event buffer and the page polls
`/api/events?since=` every 200 ms; the first poll only records the newest id, so opening the page does not
replay a backlog burst.
- colours: zone tint = live, amber = stale, rose = offline;
- `?static=1` renders a single frame (also used for `prefers-reduced-motion`);
- `?debug=1` overlays renderer metrics (draw calls, triangles, canvas size, camera).

The older 2D dot view is still available at `/neural-flat`.

### Verified vs. not verified

Verified in this environment: the page loads the topology (50 nodes, 50 uplink fibres), builds the scene, and
`renderer.info` reports **161 draw calls / 4,646 triangles** on a 1578×846 canvas.

Not verified: a screenshot of the WebGL layer. Headless Chrome/Edge in this sandbox composite the DOM but not
the WebGL canvas (the same page shows fine in a normal browser), so `results/neural-3d-geometry.png` is a
**matplotlib rendering of the same geometry and camera**, produced by `preview3d.py` — it is a layout preview,
not a screenshot of the app.

```sh
python sim/docker/preview3d.py --out sim/docker/results/neural-3d-geometry.png
```

## Honest limits

- The backend is a mock that returns immediately; the numbers describe **gateway and transport overhead**,
  not LLM inference. A real 8B model on CPUs will be orders of magnitude slower.
- Containers share one host, so this measures a single-node Python gateway under connection pressure, not a
  distributed Petals swarm across 50 physical machines.
- Docker Desktop on Windows runs containers inside one WSL2 VM; CPU contention from 50 containers is real
  but not representative of 50 separate office PCs.
- Node heartbeats (≈25 req/s) run during the sweep, so the measured latency includes that background load.

## Fallback without Docker

If Docker Desktop is unavailable, the same topology runs as processes:

```sh
python sim/docker/run_local_fleet.py --nodes 50 --port 8080
```

It starts the hub plus 50 `node_agent.py` processes, then prints the loadgen command. Use
`--keep` to leave them running.
