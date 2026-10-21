# Map-reduce over the fleet: does splitting a document help?

**Measurement note · 2026-10-21** · figures: `report/shard/figures/` (white, 300 dpi)
Data: `report/shard/bench.json`, `report/shard_half/bench.json`

## 1. What was built

A real map-reduce path, not a simulation:

```
document ──split──▶ N chunks ──dispatch in parallel──▶ N machines (POST :9100/work)
                                                     └── assemble: sum words/chars, hash digests
```

- `node_agent.py` gained a `process_chunk()` endpoint: tokenise, count, and mix a SHA-256 digest `rounds` times.
  Deterministic and verifiable, so a fast wrong answer cannot win.
- `node_plane.py` gained `POST /api/shard`: splits on word boundaries (separators preserved, so totals match
  exactly), dispatches with `asyncio.gather`, and assembles the partial results.
- Every sharded run is asserted against the sequential totals (`words`, `chars`) before it is accepted.

## 2. Results on the office profile (0.05 CPU per container)

![Time by chunks](figures/fig25_shard_time.png)

**Figure 25.** Server-side processing time against chunk count, with the single-machine baseline dotted.

| Document | Sequential (1 machine) | Best sharded | Speedup at best | Speedup at 50 chunks |
|---|---:|---:|---:|---:|
| 256 KiB | **466 ms** | 694 ms (2 chunks) | **0.67×** | 0.27× |
| 1 024 KiB | **865 ms** | 676 ms (4 chunks) | **1.28×** | 0.52× |
| 2 048 KiB | **1 259 ms** | 951 ms (8 chunks) | **1.32×** | 0.76× |

![Speedup](figures/fig26_shard_speedup.png)

**Figure 26.** Speedup over one machine. The best case is **1.3×**, and past ~8 chunks every additional machine
makes it *slower*. Efficiency at 16 chunks is 0.13, at 50 chunks 0.015.

## 3. Why it does not scale here

Three measured causes, in order of impact:

1. **Each container is capped at 0.05 CPU.** 50 machines therefore contribute at most ~2.5 cores of compute,
   and each chunk is dispatched to a machine that is throttled to 5 % of a core. Sharding cannot create CPU
   that the scheduler does not hand out.
2. **The coordinator is in the data path.** Uploading a 1 MiB document to the centre costs **~1 219 ms** of wall
   clock while the coordinator itself measures **198 ms** of work (Figure 27). Splitting after upload adds a
   second serialisation rather than removing one.
3. **Per-chunk fixed cost.** Each chunk costs a connection, a JSON encode/decode and a scheduler wake-up
   (~5–15 ms). A 256 KiB document split 50 ways spends more time in overhead than in hashing.

![Upload dominates](figures/fig27_upload_dominates.png)

**Figure 27.** Where a 1 MiB request spends its time: transport to the centre overshadows the compute the centre
then distributes.

## 4. When the same design *would* win

The crossover is arithmetic, and the data above pins two of the three terms:

```
T_sharded ≈ upload (S/B_link) + max_chunk_work (w·c/CPU) + assembly (k·n)

wins over  T_sequential = S·c/CPU_1     when     CPU_per_node · (upload share) is small
```

| Change | Effect on the measured bottleneck |
|---|---|
| Give each machine ≥0.5–1 core | removes cause 1; the same run at 0.5 CPU was **5.7× faster per chunk** (82 ms vs 466 ms for 256 KiB) |
| Remove the coordinator from the data path (client-side split, presigned URLs, or stream-to-node) | removes the 1.2 s upload from every request |
| Split only documents above a threshold | keeps fixed costs amortised: at 256 KiB no chunk count beats one machine; at 1–2 MiB, 4–8 chunks break even |
| Batch many documents per request | converts the per-chunk fixed cost into useful work |

Rules of thumb from this run:

- **< 256 KiB**: process on one machine; sharding is a net loss at every chunk count.
- **1–2 MiB with 0.05 CPU nodes**: 4–8 chunks, expect ≤1.3×.
- **≥ 8 MiB, nodes at ≥0.5 CPU, client-side split**: the only regime where linear speedup is plausible.

## 5. Verdict

**The measured answer to "does it help?" is: not in this deployment.** Best case 1.3×, worst case 0.27×, with
the crossover explained by CPU quota and coordinator upload — both fixable, neither fixed here.

The implementation is kept because it is the correct substrate for the regime where it does pay off: a
document-class workload (large files, batch ingestion, offline indexing) with machines that have real CPU and a
data path that bypasses the coordinator. For interactive Q&A, the shard path should stay off: it makes p95
worse without raising throughput.

## 6. Reproduce

```sh
python sim/shard/bench.py --base http://127.0.0.1:8081 \
    --sizes 262144,1048576,2097152 --chunks 2,4,8,16,32,50 --rounds 20000 --repeats 3 --out report/shard
python sim/shard/plots.py --data report/shard --out report/shard/figures
```

## 7. Threats to validity

- All 50 "machines" share one 8-vCPU host with a 0.05 CPU quota each; real office PCs would have 4 full cores.
- The 1 MiB upload figure is one measurement on Windows loopback through Docker networking.
- Work is synthetic (tokenise + hash); a real embedding job would have a different compute/transport ratio.
- No retry on a straggler: one slow chunk determines the whole request.
