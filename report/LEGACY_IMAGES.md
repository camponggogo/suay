# Facts preserved from three figures that were replaced by placeholders

The chat context dropped three screenshots. Everything that mattered from them is recorded here and in the
reports they came from.

## 1. `sim/docker/results/response_time_report.png` — 50-machine load test (dark theme)

Three stacked panels: p50/p95/p99 vs concurrency (log-log), throughput vs concurrency, and a box plot of the
latency distribution per concurrency. Values (identical to `report/REPORT.md`):

| C | rps | p50 ms | p95 ms | p99 ms |
|---:|---:|---:|---:|---:|
| 1 | 4.9 | 166 | 419 | 542 |
| 5 | 7.3 | 695 | 939 | 988 |
| 10 | 8.1 | 1 125 | 1 787 | 1 920 |
| 25 | 9.1 | 2 589 | 2 959 | 2 984 |
| 50 | 12.0 | 3 811 | 5 364 | 5 509 |

Caption facts: 50/50 machines live, 0 errors, throughput plateaus ≈12 req/s, latency grows roughly linearly
with concurrency — the signature of a single serialisation point, not of network saturation.

## 2. `sim/docker/results/neural-view.png` — 2D "neural fabric" admin view

- 50 dots on three concentric bands (one band per zone: floor-1, floor-2, floor-3 = 20/20/10).
- Dashed curved fibres from every dot to the violet `SUAY CORE`; lateral fibres between neighbours in a zone;
  pulses travelling outward/inward along the fibres.
- HUD: 50 live / 50 total, 26.3 signals per second, 3 zones, legend for live/stale/offline/core.
- Served at `/neural-flat`; the same page is the visual language used by the 3D view.

## 3. `sim/docker/results/neural-3d.png` — 3D page, headless capture

- The page loads, fetches the topology (50 nodes, 50 uplink fibres) and builds the scene; `?debug=1` reported
  **161 draw calls / 4,646 triangles on a 1 578 × 846 canvas**.
- Headless Chrome/Edge in this sandbox composite the DOM but **not** the WebGL canvas, so the screenshot shows
  only the HUD and, at best, a faint core glow. The geometry itself is previewed in
  `report/figures/fig9_pipeline_economics.png` and `report/experts/figures/*` style plots.
- Practical consequence: for figures in the paper, use the matplotlib previews; the interactive scene must be
  shown live at `/neural` (three.js r180, vendored, CSP-safe).

## Where the numbers live now

`report/REPORT.md` (load test), `report/SCALING.md` (node plane), `report/KV_CACHE.md` (prefix cache),
`report/GATEWAY_OPT.md` (workers), `report/CPU_1PCT.md` and `report/CPU_SWEEP.md` (CPU limits).
