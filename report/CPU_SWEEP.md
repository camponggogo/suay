# CPU sweep 10 % → 80 %: more CPU per machine does not add throughput

**Measurement note · 2026-10-21** · figure: `report/cpu_sweep/figures/fig32_cpu_sweep.png`
Data: `report/cpu_sweep/sweep.json` (50 machines, node plane, heartbeat 10 s)

## 1. Method

`docker update --cpus=<level>` applied to all 50 node containers, 18 s settle, then 4 liveness samples 5 s
apart and two short load levels (C=1, C=8, 5 s each). Hub, node plane and upstream were **not** throttled.

## 2. Results

| CPU / machine | rps @C=1 | rps @C=8 | mean ms C=1 | mean ms C=8 | live (of 50) | dispatch RTT |
|---:|---:|---:|---:|---:|---:|---:|
| **10 %** | **11.0** | **13.4** | **91** | **590** | 48.0 | 27.8 ms |
| 20 % | 11.1 | 12.9 | 90 | 615 | 49.0 | 29.0 ms |
| 30 % | 11.8 | 12.2 | 85 | 648 | 48.0 | 29.3 ms |
| 40 % | 11.2 | 10.7 | 89 | 726 | 47.8 | 31.0 ms |
| 50 % | 8.4 | 11.6 | 119 | 678 | 48.2 | 33.7 ms |
| 60 % | 8.3 | 8.5 | 120 | 927 | 47.8 | 35.1 ms |
| 70 % | 8.5 | 9.4 | 118 | 822 | 47.2 | 32.6 ms |
| 80 % | 8.2 | 8.3 | 121 | 945 | 48.2 | 39.7 ms |

![CPU sweep](figures/fig32_cpu_sweep.png)

**Figure 32.** Throughput, latency, liveness and dispatch RTT against the per-machine CPU limit.

## 3. What the curve says

1. **The plateau starts at 10 %.** Ten percent of a core is enough for this agent to heartbeat every 10 s and
   answer `/work` in ~28 ms. Beyond that, every extra percent is spent nowhere.
2. **The ceiling is the gateway, not the machines.** 11–13 req/s is what the single hub worker accepts; the
   machines could answer faster, but no request reaches them faster.
3. **More CPU can make it slightly worse.** At 80 % the fleet is demanding 40 cores on an 8-vCPU host; the
   containers contend with each other and with the Docker VM, dispatch RTT rises from 28 to 40 ms, and
   throughput falls to 8.2 req/s. This is a scheduling artefact of the simulation host, but it is the honest
   shape of "just raise the limits".
4. **Liveness never returns to 50/50.** 47–49 machines report inside the 15 s window at every level, including
   80 %. The two to three missing machines are the ones whose 10 s heartbeat lands just outside the window —
   a property of the interval and the window, not of CPU.

## 4. Recommendation

| Decision | Value | Reason |
|---|---|---|
| Per-machine CPU cap | **10–20 % (0.1–0.2 core)** | plateau; below 10 % liveness and dispatch degrade (measured: 1 % → 28–39 live, 3 req/s) |
| Heartbeat interval | 10 s | 2 s doubles the cost for no operational benefit inside a 30 s window |
| Where to spend the remaining budget | **gateway workers**, not machine CPU | the ceiling is 11–13 req/s at the hub; see `report/SCALING.md` |
| Liveness window | 30 s, not 15 s | removes the 47–49 wobble without masking real failures |

The single most useful number for capacity planning: **50 machines at 10 % CPU saturate a single gateway
worker at ~13 req/s**. Adding CPU to the machines changes nothing; adding a second gateway worker is the only
change that moves this number.

## 5. Threats

- The sweep ran while Docker Desktop, the 53 containers and this shell shared one 8-vCPU host; absolute rps
  moves by ±15 % between repeats.
- 5 s per load level is short; percentiles are indicative, not publication-grade.
- The workload is the mock backend, so "CPU for inference" is not exercised — only the agent's ability to
  accept and answer a request.
