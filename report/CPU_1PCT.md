# 1% CPU per machine: what breaks first

**Measurement note · 2026-10-21** · figure: `report/cpu1pct/figures/fig31_cpu_1pct_vs_5pct.png`
Data: `sim/docker/results/cpu1pct/summary.json`, with the 5% run in `sim/docker/results/plane/summary.json`

## 1. Setup

Same 50-machine stack, one change: `cpus: 0.01` (1 % of one core) per node instead of `0.05`.
Hub, node plane and upstream are unchanged (no CPU limit), so any difference comes from the machines.

## 2. Results

| Metric | 5 % (0.05 core) | 1 % (0.01 core) | Change |
|---|---:|---:|---:|
| Machines reported live | 50 / 50 | **28 – 39 / 50** | never full |
| Throughput at C=1 | 9.49 req/s | **3.04 req/s** | −68 % |
| Throughput at C=8 | 7.91 req/s | **3.69 req/s** | −53 % |
| Mean latency at C=1 | 105 ms | **329 ms** | ×3.1 |
| Mean latency at C=8 | 987 ms | **2 150 ms** | ×2.2 |
| Dispatch RTT (hub → machine) | ~31 ms | **132.9 ms mean, 319 ms p95** | ×4 |

![1% vs 5%](figures/fig31_cpu_1pct_vs_5pct.png)

**Figure 31.** Throughput and mean latency at C=1 and C=8, 1 % versus 5 % CPU per machine.

## 3. What breaks, and why

1. **Liveness first.** A heartbeat needs the Python process to wake, serialise JSON, open a socket and read the
   reply. At 1 % of a core the scheduler gives that process ~10 ms of CPU per second, so the loop drifts past the
   15 s liveness window: the fleet shows 28–39 of 50 machines at any moment, even though all 53 containers are
   `running`. The dashboard would report machines as down while they are up.
2. **Dispatch second.** Every inference request calls `/work` on a machine. That call now costs **133 ms** on
   average instead of ~31 ms, because accept + parse + respond is throttled. Mean latency at C=1 triples for a
   workload whose actual "inference" is a mock.
3. **Throughput follows.** With dispatch four times slower, the hub's worker spends its budget waiting, and
   throughput drops by half at both load levels.

Notably, this is *not* a queueing effect inside the hub — the hub is unthrottled. The ceiling moved to the
machines' ability to answer a single HTTP request.

## 4. Practical floor

| Agent implementation | Minimum CPU that keeps 50 machines alive and dispatch < 50 ms |
|---|---|
| Python agent, 10 s heartbeat, per-request `/work` (current) | **≈0.05 core (5 %)** |
| Python agent with a 60 s heartbeat and no per-request work | ~0.01 core may work; liveness becomes slow to detect |
| Compiled agent (Go/Rust) doing the same work | 0.005–0.01 core plausible — not implemented here |

So 1 % is below the floor for this implementation, not below the floor for the design. The honest statement for
the white paper: **the 1.5 GB / 1.5-core profile is a deployment choice; a 1 % CPU cap is not viable for a
Python control agent, because liveness and dispatch degrade before compute does.**

## 5. Reproduce

```sh
# in sim/docker/docker-compose.yml: cpus: 0.01 for node-a/node-b/node-c
docker compose up -d
python sim/docker/loadgen.py --base http://127.0.0.1:8080 --key suay_sim_loadgen_key \
    --model sim-model --steps 1,4,8 --seconds 6 --out sim/docker/results/cpu1pct
python sim/fleet/cpu_compare.py --out report/cpu1pct/figures
```

## 6. Threats

- The host was also running the Docker VM and 53 containers; absolute numbers move with background load.
- Liveness was sampled every 5 s for 35 s; a longer window might show a higher peak.
- The mock `/work` is a 4–10 ms sleep, so the measured dispatch penalty is scheduler overhead, not compute — a
  real model would show an even larger gap.
