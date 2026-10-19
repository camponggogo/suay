# Public landing deployment

- URL: https://campong.online/projects/suay/
- Deployed: 2026-10-19, 18:56 Asia/Bangkok (11:56 UTC)
- Release ID: `20261019T115659004220Z`
- Files: only the nine static files listed in `deploy_landing.py`, including English/Thai pages, the selected PNG, sitemap and public IndexNow verification file
- Nginx preflight and post-change syntax checks: passed
- Public landing HTTPS content check: passed
- Existing company-root HTTPS check: passed
- Organization dashboard/API/database: not deployed by this operation

The host retains the release and prior configuration backup under `/opt/suay/`. Follow the rollback guidance in README.md and compare host configuration before restoring it. The public page includes the Star request and honest pending state for GitHub Sponsors. Repository publication is separate from website deployment; the release ID above identifies the static website deployment.

Search discovery verification: English and Thai pages and the XML sitemap return HTTP 200. Visible FAQ content matches JSON-LD; canonical, hreflang and CSP hashes were checked. IndexNow accepted notification for both URLs with HTTP 202 on 2026-10-19; this does not establish indexing or ranking. Root robots/company sitemap were preserved.
