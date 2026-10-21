# Expert routing for a 50-machine inference pool

**White-paper section · SUAY · 2026-10-21** · figures in `report/experts/figures/` (white background, 300 dpi)

## Abstract

Instead of serving one dense model to every request, we split the catalogue into domain experts and route each
query — plus the sources it references — to the matching expert pool. On a 6,000-query labelled benchmark a
rule-based router reaches **90.2 % accuracy** (100 % on clear and ambiguous queries, **50.8 %** on adversarial
ones), with a decision latency of **31.5 µs p50 / 93.1 µs p95**. Combining that router with a capacity model
built on the measured gateway floor (98 ms) and documented compute rates, domain routing raises fleet capacity
from **0.06 to 0.64 requests/s** (≈**10.7×**) while using **32 of the 50 machines**; a dense mixture-of-experts
catalogue of the same quality class does **not fit** the fleet at all (86 machines required).

The honest headline is twofold: routing is the only one of the three shapes that is both feasible at 1.5 GB per
machine and an order of magnitude more productive — **and** the router is the weakest link, because naive
substring matching fails on exactly the queries that matter.

## 1. Idea

A law firm does not need a chemistry expert; a chemistry lab does not need contract law. If the catalogue is
partitioned by domain, a request should load and contact only the relevant slice:

```
query + referenced sources ──▶ router ──▶ domain pool (legal | chemistry | general)
                                            └── 1B expert + 1B shared backbone, 4 GB per copy
```

Two signals decide the route: **wording** (domain terms) and **the sources the user attaches** (a `สัญญา.pdf`
is stronger evidence than a stray keyword). Source hints are weighted ×3, because users rarely attach a
contract to a chemistry question.

## 2. Method

**Measured.** A labelled set of 6,000 queries in three tiers:

| Tier | What it contains | Why it matters |
|---|---|---|
| easy | one domain, unambiguous terms | sanity floor |
| ambiguous | two domains in one query (“สัญญาซื้อขายสารเคมี…”) | real enterprise requests |
| adversarial | substring traps (“สัญญาณ NMR” contains “สัญญา”), source-only hints, short queries | where rules break |

The router is deliberately simple (term lists + source hints + a confidence margin) so the measurement shows
what a *cheap* first version buys before investing in an embedding classifier.

**Modelled.** Per-request latency and fleet capacity for three deployment shapes, using the gateway floor
measured in `report/REPORT.md` (98 ms of pure control-plane work at the 10.2 req/s ceiling) plus documented
compute rates. Model assumptions are stated in `shapes.json`; nothing here is presented as an LLM benchmark.

## 3. Router results

| Metric | Value |
|---|---|
| Accuracy (overall) | **90.15 %** |
| Accuracy — easy / ambiguous / adversarial | **100 % / 100 % / 50.75 %** |
| Precision / recall — legal | 0.933 / 0.935 |
| Precision / recall — chemistry | 1.000 / 0.801 |
| Precision / recall — general | 0.774 / 1.000 |
| Decision latency | **31.5 µs p50**, 93.1 µs p95, 185.8 µs max |

![Confusion matrix](figures/fig10_router_confusion.png)

**Figure 10.** Confusion matrix. Chemistry loses 293 queries to *general* and 152 to *legal*: the first is
under-matching (short queries such as “pH 7”), the second is the substring trap — “สัญญา” is a prefix of
“สัญญาณ” (signal).

![Accuracy by tier](figures/fig11_accuracy_by_tier.png)

**Figure 11.** Accuracy collapses on adversarial inputs while staying perfect on the other tiers. A single
number (90 %) hides this; the per-tier breakdown is the result that matters.

![Router latency](figures/fig12_router_latency.png)

**Figure 12.** Routing costs tens of microseconds — four orders of magnitude below the 174 ms service floor.
Routing is free relative to inference; **accuracy**, not speed, is the constraint.

## 4. Capacity results

Model inputs: 150 output steps per answer, gateway floor 98 ms, 1.5 GB container cap (≈1.1 GB usable after the
runtime), 50 machines.

| Shape | Active params | Copy size | Machines | Parallel copies | Latency | Fleet capacity |
|---|---|---|---|---|---|---|
| Dense 8B | 8 B | 16 GB | 15 | 3 | 50.1 s | 0.060 req/s |
| MoE 8×7B (top-2) | 13 B | 94 GB | 86 | 0 | 81.2 s | **infeasible** |
| **Domain experts (routed)** | **2 B** | **4 GB** | **32** | **8** | **12.6 s** | **0.64 req/s** |

![Latency vs capacity](figures/fig13_latency_vs_capacity.png)

**Figure 13.** Each shape at its operating point. Domain routing is both faster per request (12.6 s vs 50.1 s)
and able to run eight pools in parallel; the MoE catalogue cannot be hosted at 1.5 GB per machine.

![Nodes required](figures/fig14_nodes_required.png)

**Figure 14.** Machine footprint against the 50-machine budget. Routing fits with 18 machines to spare;
dense 8B fits but leaves almost no room for replicas; MoE does not fit.

## 5. Confidence gating

The router exposes a confidence margin. Gating on it trades coverage for accuracy, which is the right knob when
a misroute is expensive (a contract question answered by a chemistry expert is worse than a slow general
answer).

![Confidence trade-off](figures/fig15_confidence_tradeoff.png)

**Figure 15.** Accuracy on the routed subset versus coverage. The router's confidence margin is bimodal: with
**no** gate it routes 100 % of traffic at 90.2 % accuracy, but gating at **0.1** routes **65.2 %** of traffic at
**100 %** accuracy. In other words, the queries where the router is unsure are precisely the ones that need a
fallback — the remaining 34.8 % should go to the general pool rather than to a guessed expert.

## 6. Discussion

1. **The win is capacity, not per-query speed.** Routing lets each pool host a small expert, so the 1.5 GB cap
   stops being the binding constraint and eight domains run in parallel. The 10.7× figure is a *capacity*
   result.
2. **Substring matching is not good enough.** 50.75 % on adversarial queries means half of the hard cases go to
   the wrong expert. Before this ships, replace term lists with a small embedding classifier trained on the
   organisation's own tickets, and keep the rules as a fallback.
3. **Misroutes must be visible.** Every decision should be logged with its confidence and the matched signals;
   shadow-evaluate a sample against the general pool so quality regressions are caught.
4. **Pool sizing matters more than model choice.** With 32 of 50 machines used, the remaining 18 are the only
   headroom for replicas; a 9th domain would need 36 and leave 14. Plan pools from measured demand.
5. **The MoE result is a warning.** Parametric efficiency does not help if the catalogue does not fit the
   machines you own; expert *routing* beats expert *mixing* at this scale.

## 7. Threats to validity

- The benchmark is synthetic; real tickets contain typos, code-switching and long context. Expect lower
  accuracy, especially on adversarial cases.
- Compute rates (3 / 1.85 / 12 steps/s) are assumptions for 8 vCPU-class machines, not measurements of these
  models. Replacing them changes the absolute numbers, not the ordering.
- The capacity model ignores cache reuse, batching and KV-cache sharing between requests in the same pool; all
  three favour routing, so the 10.7× should be treated as a lower bound on the design's potential.
- No quality evaluation was performed. The claim is that a 1B domain expert matches an 8B general model *within
  its domain*; that is an assumption and must be tested before publication.

## 8. Recommendation

| Step | Action | Acceptance |
|---|---|---|
| 1 | Replace the rule router with a 3-way classifier on real tickets | adversarial accuracy ≥ 90 %, p95 < 1 ms |
| 2 | Add confidence gating + fallback to the general pool | routed subset ≥ 65 % at ~100 % precision, remainder answered by general |
| 3 | Size pools from measured demand, keep 20 % replica headroom | pool utilisation 60–75 % |
| 4 | Run a domain quality evaluation (expert vs general, same prompts) | specialist ≥ general on its domain |
| 5 | Only then enable routing in production, with per-domain dashboards | rollback in one config flag |

**Bottom line.** Domain routing is the most promising optimisation we have measured: it turns an infeasible
catalogue into a feasible one and multiplies capacity by an order of magnitude on paper — but its weakest link
is a 90 %-accurate router whose hard-case accuracy is 51 %. Fix the router first; the capacity follows.
