# Prefix cache + KV-aware routing: the bottleneck fix that fits a CPU fleet

**Design note and measurement · 2026-10-21** · figures: `report/kv/figures/` (white, 300 dpi)
Code: `sim/docker/node_plane.py` (`/api/serve`, `/api/cache_stats`, `/api/cache_reset`), `sim/kv/bench.py`

## 1. Where the research is

The 2025–2026 literature has converged on one answer for serving bottlenecks: **the KV cache is the resource to
schedule, not the GPU**. Four threads, all current:

| Thread | What it changes | Representative work |
|---|---|---|
| **Automatic prefix caching** | reuse KV blocks for shared prompt prefixes instead of recomputing | vLLM APC docs (`docs.vllm.ai/en/stable/design/prefix_caching`) |
| **KV-aware routing** | send a request to the replica that already holds its prefix | llm-d reports **57× faster responses and 2× throughput** in production (`llm-d.ai/blog/kvcache-wins-you-can-see`) |
| **KV as a first-class tier** | offload / share / persist KV across requests and nodes | Modular, "The Five Eras of KVCache", Feb 2026 |
| **KV memory as the primary limit** | new attention layouts to fit more sessions | arXiv 2606.02964, "Multi-Segment Attention", Jun 2026 |

Why this one fits SUAY and the others do not:

- Disaggregated prefill/decode needs fast KV transfer and GPUs — out of reach for 50 office PCs.
- Speculative decoding needs a draft model per machine and re-training of the serving path.
- MoE expert parallelism needs a model far larger than 1.5 GB per machine can hold.
- **Prefix reuse needs nothing but bookkeeping** — and our fleet's dominant cost is prefill on CPU.

Measured on this host: **72.25 tok/s prefill vs 11.74 tok/s decode** (llama.cpp, 0.5B Q4). A 8 000-token
document costs 111 s of prefill before the first token; decoding 150 tokens costs 12.8 s. The expensive part is
exactly the part a prefix cache can skip.

## 2. What was implemented

```
prompt ──▶ content-addressed blocks (256 tokens) ──▶ block_key = sha256(doc_id:index)
                                                        │
                 registry: block_key ──▶ {machines that hold it}
                                                        │
      request ──▶ longest contiguous prefix any machine holds ──▶ route there
                                                        │
                        prefill only the uncached suffix; remember the new blocks
```

- **Content-addressed blocks**, 256 tokens each, so two documents sharing a header share blocks.
- **Longest-prefix routing** across the live fleet; ties fall back to round-robin.
- **Bounded registry** (20 000 blocks, LRU on overflow) so memory stays flat.
- **Hit accounting** per request: cached tokens, prefill tokens, hit flag, owning machine.
- Timing uses the measured prefill/decode rates, so the reported TTFT is the number this hardware would see;
  routing, ownership and hit rate are real state.

Release: MIT, no external dependencies, offline. Knobs: `SUAY_BLOCK_TOKENS`, `SUAY_PREFILL_TPS`,
`SUAY_DECODE_TPS`, `SUAY_LIVE_WINDOW_S`.

## 3. Results

Workload: 240 requests per point, document Q&A shape (shared document + 50-token question + 150-token answer);
`reuse %` = share of requests that hit one of three popular documents.

![TTFT](figures/fig28_ttft_vs_reuse.png)

**Figure 28.** Time to first token. The step at 75 % is the median crossing from a cache miss to a hit: once
more than half of requests reuse a document, the typical request is a hit.

| Document | Reuse | TTFT p50 — no cache | TTFT p50 — prefix cache | Speedup |
|---|---:|---:|---:|---:|
| 2 000 tok | 90 % | 28.4 s | **0.71 s** | **40×** |
| 8 000 tok | 90 % | 111.4 s | **0.71 s** | **157×** |
| 8 000 tok | 75 % | 111.4 s | **0.71 s** | **157×** |
| 8 000 tok | 50 % | 111.4 s | 111.4 s | 1× (median is a miss) |

![Throughput](figures/fig29_throughput_vs_reuse.png)

**Figure 29.** Throughput per single stream (60 / mean total time). At 90 % reuse the 8 000-token workload goes
from **0.5 to 2.3 requests/min (4.6×)**; the 2 000-token workload from 1.5 to **3.6 req/min (2.4×)**.

![Effectiveness](figures/fig30_cache_effectiveness.png)

**Figure 30.** Fraction of prompt tokens served from cache, against the ideal 1:1 line. The mechanism recovers
**86–88 %** of prompt tokens at 90 % reuse — the gap is the unique documents and the questions.

## 4. What this fixes and what it does not

| Symptom from our earlier measurements | Effect |
|---|---|
| 96.5 % of latency was queueing at the gateway | **Indirectly fixed**: requests are 9× cheaper, so the same 10.2 req/s gateway now serves ~9× more work |
| 8 000-token documents needed 111 s before the first token | **Fixed for repeats**: 0.71 s |
| p95 latency | **Unchanged** — the 10–25 % of unique requests still pay full prefill; the cache moves the median, not the tail |
| Inference gateway ceiling (10.2 req/s) | Unchanged; this reduces work per request, not the cost of accepting one |

## 5. Operating guidance

1. **Turn it on when the workload repeats**: document Q&A, policy lookup, contract review with a shared
   template, multi-turn chat. Below ~50 % reuse the p50 does not move.
2. **Cache at the block level, not the request level**: two documents that share a preamble share blocks.
3. **Route by prefix, not by load**: a hit on a loaded machine beats a miss on an idle one by an order of
   magnitude on this hardware.
4. **Report hit rate, not hit count** — it is the only number that predicts the benefit.
5. **Do not market p95**: the tail belongs to unique documents. Pair this with admission control if p95 matters.

## 6. Honest limits

- **The KV tensors are not materialised.** The registry tracks ownership exactly, but the attention state is
  modelled with the measured rates rather than stored; on a real deployment the cache consumes memory per block
  (~2 × 32 × 1024 × 256 × 2 B ≈ 32 MiB per 256-token block at 1k context for a 0.5B model), which caps how many
  blocks a machine can hold.
- One machine's cache is assumed durable while it is live; a reboot loses it and the next request pays full
  prefill.
- No eviction by memory pressure yet — only the registry's block cap.
- Measured rates come from a single 0.5B model on one laptop-class CPU; larger models shift the ratio toward
  decode, reducing the relative gain.
- The workload is synthetic: three popular documents and a uniform unique tail.

## 7. Why release it

The mechanism is ~120 lines, dependency-free, and gives the largest single improvement measured in this project
(157× on the dominant latency term) without new hardware. It is MIT-licensed with the rest of the repository, so
any office that already runs the control plane can enable it with two environment variables.
