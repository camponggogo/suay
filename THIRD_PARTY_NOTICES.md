# Third-party software and model terms

The root MIT license covers original SUAY code and documentation, not third-party packages, model weights, datasets, trademarks, or hosted services. Dependencies are installed separately; no model weights or dependency binaries are bundled in this source tree.

## Confirmed upstream terms

- **Petals**: MIT. Copyright (c) 2022 Petals authors and collaborators. If redistributing Petals code or binaries, retain its copyright and license notice. Source: https://github.com/bigscience-workshop/petals/blob/main/LICENSE
- **BLOOM / bigscience/bloom-560m**: BigScience RAIL License v1.0, not MIT. Use restrictions and redistribution/hosted-access obligations apply. Review the complete license, model card and downstream user obligations before offering inference, including to third parties. The default model name in the experimental agent is a configuration choice, not a license grant. Source: https://huggingface.co/bigscience/bloom-560m/blob/main/LICENSE

No claim is made that all model families are commercially interchangeable. Llama, Gemma and other models must be reviewed individually at their exact repository and revision before entering an organization's approved catalog. Model operators should record model ID, revision, artifact digest, license URL and approval owner. Do not publish gated weights or access tokens.

## Package and asset review still required for binary releases

SUAY control uses FastAPI, Uvicorn, HTTPX and their transitive dependencies. The experimental compute/client uses Petals, PyTorch, Transformers, Hivemind, bitsandbytes and other dependencies. Their terms remain separate. A complete transitive dependency/license audit and reproducible lockfile have **not** been produced in this environment. Docker images and native installers must include notices for the actual resolved packages; source-level review is not a binary redistribution clearance.

The landing page uses project HTML/CSS and SVG brand artwork with conceptual device-network and architecture images composed using ChatGPT ImageGen. The figures are explanatory visuals, not hardware compatibility certifications. No third-party photographs are bundled. The page requests DM Sans and Space Grotesk through Google Fonts; these are separate assets with their own font licenses and external network/privacy implications. Before self-hosting fonts, retain the license supplied with the exact font files. System-font fallbacks allow the page to function without the font service.

Review date: 2026-10-19. This is an engineering inventory of observed terms, not a legal opinion or a guarantee of compliance. Before public release, confirm ownership/provenance of pre-existing repository files and review the exact dependency versions that will ship.
