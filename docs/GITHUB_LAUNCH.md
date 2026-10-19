# GitHub repository setup

The repository **camponggogo/suay** already exists at https://github.com/camponggogo/suay. Preserve its existing `main` history and inspect the staged diff before committing and pushing. Never replace the existing history with a new root commit or force-push it.

## Suggested “Create a new repository” fields

- **Repository name:** `suay`
- **Description:** `Wake old machines. Run AI together. Open-source distributed AI compute, local resource sharing, scoped developer API keys, and an organization control-plane pilot.`
- **Visibility:** Public
- **Initialize README / license / .gitignore:** Leave unchecked when uploading this prepared source tree; these files already exist locally.
- **Website:** `https://campong.online/projects/suay/` after verifying the deployment.
- **Topics:** `distributed-ai`, `distributed-computing`, `local-ai`, `resource-sharing`, `llm-inference`, `edge-ai`, `self-hosted`, `on-premise`, `ai-infrastructure`, `petals`, `developer-tools`, `cost-optimization`

Avoid presenting unimplemented native services or cloud savings as shipping features. Search visibility depends on useful documentation, activity and adoption; topics cannot guarantee a top ranking.

## Business positioning

**Headline:** Wake old machines. Run AI together.

**Thai headline:** ปลุกเครื่องเก่า ให้ร่วมกันรัน AI — เปลี่ยนทรัพยากรที่มี ให้เป็นโอกาสใหม่ขององค์กร

**Pain point:** Teams need AI experimentation and internal APIs, while GPU purchase approval, recurring cloud charges and fragmented access controls slow delivery.

**Promise to validate:** Start from existing hardware, give developers controlled access, and measure whether local shared inference fits actual workloads before buying more capacity. Local power, administration, maintenance and performance costs still matter.

**Who to invite first:** SME IT teams, internal developer platforms, universities and engineering labs with underused workstations. Invite hardware results and reproducible pilots rather than promising all machines can run every model.

**First issues:** native Windows service packaging; Linux worker identity/lease; macOS runtime validation; token quotas based on measured inference usage; zone-scoped gateway routing; authenticated worker state acknowledgements; dependency lockfiles and SBOM.

## Before public upload

Only upload source. Exclude `.env`, database files, API keys, sessions, model caches, company configuration, logs, virtual environments and local test artifacts. Confirm rights to existing code, preserve THIRD_PARTY_NOTICES.md and keep model licenses separate. Enable private vulnerability reporting, branch protection and dependency alerts when repository settings are available.

Inspect `git diff --cached --stat` and `git diff --cached` before committing. The remote origin should be `https://github.com/camponggogo/suay.git`. Check `git status --ignored` to confirm credentials/state are excluded. Once reviewed, the maintainer can commit and run `git push -u origin main`.
