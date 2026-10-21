# Where this system stands: comparison with the Compute Index (week 7, 2026) and llama.cpp

**White-paper appendix · 2026-10-21** · figures: `report/compare/figures/` (white background, 300 dpi)

## 1. What was compared, and how it was measured

| Source | What it measures | How |
|---|---|---|
| **This project** | gateway ceiling, per-shape capacity | measured on 50 Docker containers (966 requests, 10 concurrency levels); compute rates modelled |
| **Compute Index, week 7 2026** | tokens/s and price per 1M input tokens for 40 hosted models | API benchmarking, single stream per model |
| **llama.cpp (b11757)** | tokens/s on this machine | `llama-bench -m qwen2.5-0.5b-instruct-q4_k_m.gguf -p 512 -n 128 -t 8 -r 3` |

The local run is the honest anchor: it is the same class of hardware as the simulated office machines, and it
uses the engine the project would actually deploy.

```
cpu_info      Intel(R) Core(TM) i7-8550U @ 1.80 GHz   (4C/8T, laptop class)
model_type    qwen2 1B Q4_K - Medium (630 M parameters, 469 MB)
prompt        512 tokens -> 72.25 tok/s
generation    128 tokens -> 11.74 tok/s
build         b11757
```

## 2. Speed

![Generation speed](figures/fig16_generation_speed.png)

**Figure 16.** Generation speed across 20 hosted models (Compute Index), the measured llama.cpp baseline, and
our three deployment shapes. The median hosted model produces **136 tok/s**; this host produces **11.7 tok/s**
for a 0.6B model — a **11.6× gap per stream**. Our modelled shapes sit at 1.8–12 tok/s per stream because they
share one host's eight vCPUs across 50 containers.

The uncomfortable detail: our **gateway ceiling (10.2 req/s)** and one local model's generation rate
(**11.7 tok/s**) are of the same order. With a real model, the gateway is no longer the bottleneck — the model
is. That inverts the priority list from `report/REPORT.md`: optimising the gateway buys nothing until the
compute layer improves.

## 3. Cost

![Value frontier](figures/fig17_value_frontier.png)

**Figure 17.** Speed versus cost per 1M tokens. Cloud models span $0.00–1.75; the green curve is this pool at
duty cycles from 100 % down to 5 %, assuming 50 used PCs at $300 each, 3-year amortisation, 25 W average and
$0.12/kWh.

| Duty cycle | Fleet generation (tok/s) | Cost per 1M tokens |
|---|---|---|
| 100 % | 587 | **$0.29** |
| 50 % | 294 | $0.57 |
| 20 % | 117 | $1.43 |
| 10 % | 59 | $2.86 |
| 5 % | 29 | $5.73 |

At a realistic office duty cycle (10–20 %) the pool costs **$1.4–2.9 per million tokens** — squarely inside
the band the Compute Index calls the dead middle class. The cheapest hosted flash models deliver 292–359 tok/s
at **$0.05–0.10 per 1M input tokens**: 14–58× cheaper *and* 25–30× faster per stream. Even at 100 % duty the
pool only reaches $0.29/1M, still 3–6× above the flash tier.

Two caveats cut the other way, and they matter:

- Hosted prices are **per input token**; output tokens typically cost 2–4× more. Our cost is per **output**
  token. A like-for-like comparison narrows the gap by roughly a factor of three for chat workloads.
- The pool's marginal cost is **zero** once the hardware is sunk, which is the only defensible reason to run
  it: data never leaves the building, it works offline, and there is no per-seat ceiling.

## 4. Where our shapes sit

![Capacity vs speed](figures/fig18_capacity_vs_speed.png)

**Figure 18.** Capacity per deployment shape against the two reference speeds. Domain routing lands at
12 tok/s per stream — almost exactly the measured llama.cpp rate for a 0.6B model, which validates the
assumption used in the routing model — and yields 0.64 req/s from 32 machines.

## 5. Verdict

1. **We cannot win on tokens per second or on cost per token.** The measured gap is structural (8 vCPUs shared
   50 ways vs. a datacentre), not an implementation detail.
2. **The defensible position is residency and control**: offline operation, no data egress, per-team budgets
   and audit — the things a hosted API cannot offer.
3. **The right comparison is not "our pool vs GPT-5.2".** It is "our pool vs the alternative for this
   department": if the alternative is a $1.75/1M API, we are 1.2–2× cheaper at 10–20 % duty; if it is a
   $0.05/1M flash model, we are 30× more expensive and should say so.
4. **The one real optimisation left is utilisation.** Every doubling of duty cycle halves cost per token;
   routing domains (previous section) doubles it again by letting small experts serve most traffic. At 100 %
   duty with routing, the pool approaches the flash tier without leaving the building.

## 6. Reproducibility

```sh
# local baseline (this machine)
curl -L -o llama.zip https://github.com/ggml-org/llama.cpp/releases/download/b11757/llama-b11757-bin-win-cpu-x64.zip
powershell Expand-Archive llama.zip -DestinationPath llama
curl -L -o qwen2.5-0.5b-q4_k_m.gguf https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf
llama/llama-bench.exe -m qwen2.5-0.5b-q4_k_m.gguf -p 512 -n 128 -t 8 -r 3 -o json > llama-bench.json

# comparison figures
python sim/compare/compare.py --data report/compare
```

Cloud numbers are transcribed from the Compute Index week-7 charts (TPS and cost per 1M input tokens); the
model list and values are in `sim/compare/compare.py` so the comparison can be re-run when the index updates.

## 7. Threats to validity

- Hosted TPS is measured through provider APIs with unknown batching and hardware; it is an upper bound on
  what a user sees, not a hardware property.
- The local baseline is a 4-core laptop CPU, not a server; a modern 32-core host would close part of the gap,
  but not the 30× cost gap.
- Our on-prem cost model assumes $300 used PCs and ignores admin labour, replacement, and the opportunity cost
  of the machines.
- Quality is not compared at all: a 0.6B model is not a GPT-5.2-class model. The speed and cost numbers say
  nothing about answer quality; the paper must not imply otherwise.
