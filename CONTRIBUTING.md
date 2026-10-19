# Contributing to SUAY

SUAY helps organizations experiment with local AI and shared compute. Useful contributions include reproducible hardware results, native service packaging, scoped worker identity, accessibility, documentation and tests.

1. Open an issue explaining the business problem, OS/hardware and expected behavior. Never include employee documents, prompts containing private data, API keys or device certificates.
2. Make a focused change and add tests when changing authorization, budgets, process lifecycle or networking.
3. Run `python -m unittest discover -s tests -v` after installing `versions/python/control/requirements.txt`. Run `node --check landing/main.js` and `node --check versions/python/control/static/app.js` for the browser scripts.
4. In your pull request, explain what changed, what you verified and remaining platform limitations. Distinguish simulated telemetry from connected workers.

By submitting original contributions you agree to license them under the project's MIT license and confirm that you have the right to submit them. Preserve upstream notices for third-party material. Do not contribute model weights, copied proprietary code or employer-owned material without authorization.

The public landing page is separate from the private control plane. Do not add remote shell, arbitrary executable launch, client file browsing or desktop control to the AI command API. Report security issues privately as described in SECURITY.md.
