# SUAY papers

Two documents, same measurements, different readers.

| File | For | Length |
|---|---|---|
| [`STORY.md`](STORY.md) | anyone who wants to know how the project got here, including the dead ends | ~8 chapters |
| [`WHITEPAPER.md`](WHITEPAPER.md) | reviewers, collaborators, people who will cite or reproduce a number | 9 sections + appendix |

## Where the numbers live

`WHITEPAPER.md` cites figures by relative path into `../report/`. Each study directory holds the script that
regenerated it and the JSON it produced:

| Topic | Report | Script |
|---|---|---|
| 50-machine load test | `report/REPORT.md` | `sim/docker/loadgen.py` |
| Fleet sizing and cost | `report/FLEET_100.md` | `sim/fleet/bench.py` |
| Heartbeat and node plane | `report/SCALING.md` | `sim/fleet/heartbeat_stress.py` |
| CPU quota sweep | `report/CPU_SWEEP.md`, `report/CPU_1PCT.md` | `sim/fleet/cpu_sweep.py` |
| Prefix / KV cache | `report/KV_CACHE.md` | `sim/kv/bench.py` |
| Expert routing | `report/EXPERTS_WHITEPAPER.md` | `sim/experts/run.py` |
| Sharding | `report/SHARDING.md` | `sim/shard/bench.py` |
| Store comparison | `report/STORE.md` | `sim/store/bench.py` |
| Gateway tuning | `report/GATEWAY_OPT.md` | `sim/gateway/opt.py` |
| Denoising | `report/DENOISE.md` | `sim/denoise/bench.py` |
| Growth laws | `report/GROWTH_MODEL.md` | `sim/scaling/growth_model.py` |
| Complexity classes O(1)…O(nⁿ) | `report/growth/complexity_classes.json` | `sim/scaling/complexity_classes.py` |
| Best configuration | `report/BEST_CONFIG.md` | — |
| Retired screenshots | `report/LEGACY_IMAGES.md` | — |

## Publishing

The same summary is live at **https://campong.online/projects/suay/research.html** (English, linked from all
eleven language pages). Re-deploy with `python deploy/deploy_landing.py --apply`.

The white paper is Markdown so it diffs cleanly and converts anywhere. For a PDF build:

```sh
pandoc paper/WHITEPAPER.md -o paper/SUAY-whitepaper.pdf \
  --pdf-engine=xelatex -V geometry:margin=2.5cm -V fontsize=10pt --toc
```

Figures are already 300 dpi on white, so no post-processing is needed. `STORY.md` is written to be readable on
its own — it is the version to hand to a new contributor on day one.

## Licence

MIT, same as the repository. Reuse the numbers, cite the repo, and please send back the measurements you make on
different hardware.
