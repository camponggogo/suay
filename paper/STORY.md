# SUAY: what 50 office machines actually taught us about serving LLMs

**A storytelling paper · 2026-10-19 → 2026-10-21**

*Every number below was measured on the project's own harness. Negative results are kept on purpose.*

---

## Prologue — the promise

The project began with a seductive arithmetic: 50 office PCs × 1.5 GB of spare RAM = 75 GB, enough to hold a
70-billion-parameter model if you slice it thin enough. Petals already knew how to slice models across machines.
All that was missing was the glue: discovery, election, a dashboard, and a way to hand developers a key instead
of a shell.

That arithmetic turned out to be wrong in an interesting way — not about RAM, but about **where the time goes**.

## Chapter 1 — The first measurement (2026-10-19)

Fifty containers, a mock backend, ten concurrency levels. The result looked like a textbook queue:

| clients | req/s | p50 |
|---:|---:|---:|
| 1 | 4.9 | 166 ms |
| 10 | 8.1 | 1 125 ms |
| 50 | 12.0 | 3 811 ms |

Throughput sat at ~10 req/s while latency grew linearly. We fitted `T = C·10.18/(C+0.86)`; the knee was at
**C=2**. At C=50, **96.5 % of the response time was queueing** above a 174 ms service floor, and the payload
bandwidth was **0.034 Mbit/s** — 0.003 % of a 1 GbE link.

**Lesson 1: the network was never the bottleneck. One Python process was.**

## Chapter 2 — The honest comparison (still 2026-10-19)

We downloaded llama.cpp (b11757) and a 0.5B model and ran it on the same laptop-class CPU:

```
prompt 512 tokens → 72.25 tok/s      generation 128 tokens → 11.74 tok/s
```

The Cloud's median model in the same week's Compute Index generated **136 tok/s** for $0.05–1.75 per million
input tokens. Our 50-machine pool, amortised, cost **$0.29–2.86 per million output tokens** depending on duty
cycle — and was 11.6× slower per stream.

**Lesson 2: an office pool cannot win on tokens per second or on cost per token. It can only win on residency,
offline operation and control.** Writing that down honestly was more valuable than a flattering benchmark.

## Chapter 3 — The bottleneck moves (2026-10-21)

With 100 simulated machines, only **54.7 %** of heartbeats arrived inside the liveness window, and p50 for a
heartbeat reached **2.2 seconds**. The control plane was drowning in bookkeeping: five serial operations per
heartbeat, in the same process that served inference.

The fix was architectural, not micro: a **node plane** — a separate process, state in a dictionary, one batched
SQLite flush every 10 seconds, sharded by `crc32(node_id)`.

| | old path | node plane |
|---|---:|---:|
| peak throughput | 44 req/s | **161 req/s** per shard |
| serial p50 | 67 ms | **3.1 ms** |
| two shards, two clients | — | **266.7 req/s** (linear) |

With heartbeats gone from the gateway, single-client inference latency at C=1 fell from **210 ms to 105 ms**.

**Lesson 3: separate the data plane from the decision plane before optimising either.**

## Chapter 4 — The counter-intuitive CPU sweep

We expected more CPU per machine to help. It did not:

| CPU per machine | req/s @C=1 | req/s @C=8 | live /50 |
|---:|---:|---:|---:|
| 10 % | **11.0** | **13.4** | 48 |
| 40 % | 11.2 | 10.7 | 47.8 |
| 80 % | 8.2 | 8.3 | 48.2 |

At 80 % the 50 containers demanded 40 cores from an 8-vCPU host and thrashed. At **1 %** the fleet fell apart:
28–39 of 50 machines stayed live, throughput dropped to 3 req/s, dispatch RTT rose to 133 ms.

**Lesson 4: there is a floor (≈10 % of a core for a Python agent) and a plateau. More is not better.**

## Chapter 5 — The 157× that came from reusing work

The 2025–2026 literature converged on one idea: the KV cache is the resource to schedule. We implemented
content-addressed 256-token blocks, a registry of which machine holds which block, and **longest-prefix
routing**.

An 8 000-token document, reused by 90 % of requests:

| | no cache | prefix cache |
|---|---:|---:|
| TTFT p50 | 111.4 s | **0.71 s** (157×) |
| throughput | 0.5 req/min | **2.3 req/min** |
| prompt tokens served from cache | 0 % | **88.2 %** |

At 50 % reuse the median did not move; p95 never moved. **The cache fixes the median, not the tail.**

**Lesson 5: the biggest win was not faster compute — it was not computing the same thing twice.**

## Chapter 6 — Specialists beat one big generalist

A router that reads the question *and the document the user attached* sends legal work to a legal expert and
chemistry to a chemistry expert. On 6 000 labelled queries it reached **90.15 %** accuracy (100 % on clear and
ambiguous questions, **50.75 %** on adversarial substring traps such as "สัญญาณ NMR" containing "สัญญา"), in
**31.5 µs**.

The capacity arithmetic then favoured specialisation: a dense 8B needs 15 machines for 0.06 req/s; a mixture of
experts of the same quality class needs **86 machines and does not fit**; eight 1B domain experts plus a shared
backbone fit in **32 machines and deliver 0.64 req/s (10.7×)**.

**Lesson 6: at office scale, expert *routing* beats expert *mixing* — and the router is the weakest link.**

## Chapter 7 — Everything that did not work

| Attempt | Outcome | Why it failed |
|---|---|---|
| 50-way pipeline sharding | ≤1.3× speedup, worse at 50 chunks | CPU quota 0.05 core + coordinator upload (1.2 s for 1 MiB) |
| Postgres for the hot path | 4.5 req/s with errors | control plane's `users`/`audit` still in SQLite; schema split |
| 2–4 gateway workers on SQLite | 17.1 req/s once, 2.1 req/s next run | write-lock stalls |
| TabDAE / wavelet / DeepFilterNet gate on latency | +0.5 / +0.1 / −0.2 dB | the variance is queue ramp, not noise |
| Raising CPU to 80 % | −25 % throughput | 50 containers on 8 cores |

**Lesson 7: negative results are the cheapest documentation you will ever write.**

## Chapter 8 — The configuration that won

Combining what survived: node plane at a 10 s heartbeat, 10 % CPU per machine, one gateway worker on SQLite,
a pooled upstream client, a 2 s token cache, and a **5 s cache of the live node list**.

| point | before | after |
|---|---:|---:|
| C=8 | 4.9 req/s · 1 583 ms | **22.3 req/s · 353 ms** |
| C=16 | 5.3 req/s · 2 833 ms | **24.8 req/s · 631 ms** |

The last step was a re-test we had written off: two gateway workers. Earlier they had been unstable on SQLite, but
with the node cache and the token cache in place they ran with **zero errors** and added 48–58 %. Four workers
peaked at 29.1 req/s on C=8 and then fell over as the 8-vCPU host ran out of core.

Then the growth arithmetic: whether nodes grow as `N+1` or `N·log₂N`, capacity saturates at the same **15.7
req/s**; the superlinear law just burns 6–9× more machines (664 vs 101 at base 100) and triples dispatch latency.

**Lesson 8: grow the gateway, not the fleet — and grow the fleet linearly when you must.**

We then asked the question in the general form: what if node growth is logarithmic, linear, quadratic, exponential?
Eight classes, all normalised to the same 50 machines at n=50:

| class | nodes @n=500 | rps | $/1M |
|---|---:|---:|---:|
| O(1) | 50 | 5.94 | 0.59 |
| O(log n) | 79 | 7.34 | 0.75 |
| O(n) | 500 | 15.70 | 2.22 |
| O(2n) | 1 000 | 15.70 | 4.43 |
| O(n log n) | 794 | 15.70 | 3.52 |
| O(n²) | 5 000 | 15.70 | 22.17 |
| O(cⁿ) | 20 000 | 15.70 | 88.66 |
| O(nⁿ) | 20 000 | 15.70 | 88.66 |

Every class that reaches **319 machines** delivers the same 15.7 req/s; what changes is the bill ($0.59 → $88.66
per million tokens) and the dispatch latency (28 → 8 008 ms). Growth class is a spending decision, not a
performance decision.

## Chapter 9 — The port count trap (same day, later)

If one listening socket is good, are a hundred better? We built it: extra single-worker gateways on their own
ports, an asyncio round-robin dispatcher, and a driver that split clients across ports.

| ports | req/s | per-port req/s |
|---:|---:|---:|
| 1 | 15.7 | 15.7 |
| **2** | **26.5** | 13.25 |
| 4 | 20.8 | 5.20 |
| 8 | 23.5 | 2.94 |

The second port earned its keep. The third and fourth did not. The userspace proxy that made a hundred ports look
like one cost 25 % on its own. At a hundred ports the arithmetic is brutal: 45 MiB per process, 4.4 GiB of memory on
a host with 7.7 GiB, a hundred SQLite writers and a hundred copies of every in-process cache — for the same
24–29 req/s the machine already produced with two.

**Lesson 9: ports are for isolation, not throughput. For throughput the kernel primitive is `SO_REUSEPORT` on one
port, and the real lever is removing work from the request path.**

## Chapter 10 — What the next person inherits

A 50-machine test bed that can be started with one command, a measurement harness that reports medians and
p95 instead of anecdotes, ten reports with the numbers and the caveats, and a licence that lets anyone fork it.
The most valuable artefact is not the code: it is the list of things that looked like a good idea and measured
badly.

*Continue in [`WHITEPAPER.md`](WHITEPAPER.md) for the publication-shaped version, or
[`README`](README.md) for the file map.*
