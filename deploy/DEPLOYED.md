# Public landing deployment

- URL: https://campong.online/projects/suay/
- Deployed: 2026-10-19, 18:46 Asia/Bangkok (11:46 UTC)
- Release ID: `20261019T114629127447Z`
- Files: only the six static assets listed in `deploy_landing.py`, including the user-selected suay-device-landing.jpg
- Nginx preflight and post-change syntax checks: passed
- Public landing HTTPS content check: passed
- Existing company-root HTTPS check: passed
- Organization dashboard/API/database: not deployed by this operation

The host retains the release and prior configuration backup under `/opt/suay/`. Follow the rollback guidance in README.md and compare host configuration before restoring it. The public page includes the Star request and honest pending state for GitHub Sponsors. Repository publication is separate from website deployment; the release ID above identifies the static website deployment.
