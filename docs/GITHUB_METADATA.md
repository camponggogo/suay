# GitHub metadata — how SUAY is found

Verified against the live repository on 2026-10-21 (`GET https://api.github.com/repos/camponggogo/suay`):

| Field | Current value | Action |
|---|---|---|
| Description | Set (see below) | Keep, optional sharpen with variant B |
| Topics | **empty** | Add the 20 topics below — biggest single discoverability win |
| Homepage | **empty** | Set to `https://campong.online/projects/suay/` |
| License | MIT (detected) | OK |

Topics are what GitHub search and topic pages index. A repository with no topics is effectively invisible
for queries like "distributed inference", "local LLM" or "share GPU", no matter how good the README is.

## Description

The live description is already set and acceptable; `docs/GITHUB_LAUNCH.md` approved a shorter, punchier wording.

**Variant A — live now (keep if you prefer measured wording):**

> Distributed AI compute for local networks. Pool idle CPU/GPU resources, share LLM inference workloads, and centrally manage native AI services across devices.

**Variant B — approved in `docs/GITHUB_LAUNCH.md` (recommended, keyword-dense):**

> Wake old machines. Run AI together. Open-source distributed AI compute, local resource sharing, scoped developer API keys, and an organization control-plane pilot.

Both keep the searchable nouns (*distributed AI compute, local resource sharing, inference, developer API keys,
self-hosted, control plane*). Variant B leads with the hook instead of the category, which reads better in a
search result list.

## Topics (20, maximum allowed)

The 12 topics already approved in `docs/GITHUB_LAUNCH.md` are kept unchanged; eight technical search terms
are appended to fill the remaining slots.

```
distributed-ai
distributed-computing
distributed-inference
local-ai
resource-sharing
llm-inference
ai-cluster
model-parallelism
pipeline-parallelism
petals
p2p
cpu-inference
gpu-sharing
edge-ai
self-hosted
on-premise
openai-compatible
ai-infrastructure
developer-tools
cost-optimization
```

Rationale: the first group matches how engineers search for this class of project (`distributed-inference`,
`ai-cluster`, `model-parallelism`, `p2p`, `cpu-inference`); the rest covers the vocabulary used by IT/ops
buyers (`self-hosted`, `on-premise`, `ai-infrastructure`, `cost-optimization`) and the gateway angle
(`openai-compatible`, `developer-tools`).

## Apply with the GitHub CLI

```sh
gh repo edit camponggogo/suay \
  --description "Wake old machines. Run AI together. Open-source distributed AI compute, local resource sharing, scoped developer API keys, and an organization control-plane pilot." \
  --homepage "https://campong.online/projects/suay/" \
  --add-topic distributed-ai,distributed-computing,distributed-inference,local-ai,resource-sharing,llm-inference,ai-cluster,model-parallelism,pipeline-parallelism,petals,p2p,cpu-inference,gpu-sharing,edge-ai,self-hosted,on-premise,openai-compatible,ai-infrastructure,developer-tools,cost-optimization
```

Without `gh`: **Settings → General → Description / Website / Topics** (topics are comma-separated, 20 max,
lowercase, hyphens only).

## What actually moves a repository into "top" results

Topics and description control *matching*, not *ranking*. Ranking is driven by stars, forks, watchers,
recent activity and inbound links. In rough order of impact per hour spent:

1. **Ship a tagged release** (`git tag v0.1.0 && git push --tags`) — releases rank in "recently updated"
   and give people something concrete to star.
2. **Publish the launch post** where the audience already is: r/LocalLLaMA, Hacker News *Show HN*,
   `awesome-local-llm` / `awesome-selfhosted` pull requests, Thai developer communities, LinkedIn.
3. **Make the first 160 characters of the README carry the keywords** — GitHub search indexes README text,
   and the description is truncated in list views.
4. **Add a social preview image** (Settings → Social preview). The repository already ships
   `landing/assets/suay-neural-devices.png` as a usable 1280×640 candidate.
5. **Keep commit cadence visible** — a monthly dependency bump beats a silent year.
6. **Answer issues within a day** for the first month; response time feeds the "community" signal people use
   when deciding whether to adopt.

Honest expectation: topics will make the project *findable for its exact niche*. "Top list" for broad terms
like `llm` is not winnable against projects with tens of thousands of stars; the niche terms above are.
