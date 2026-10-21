# Public landing deployment

- URL: https://campong.online/projects/suay/
- Deployed: 2026-10-21, 15:50 Asia/Bangkok (08:50 UTC)
- Release ID: `20261021T085027270119Z`
- Files: the static set listed in `deploy_landing.py` — eleven language pages, the research log, the
  anatomy and install illustrations, `style.css`, `main.js`, `language-menu.js`, `metrics.js`, `sitemap.xml`
  and the public IndexNow verification file
- Nginx preflight and post-change syntax checks: passed
- Public landing HTTPS content check: passed
- Existing company-root HTTPS check: passed
- Organization dashboard/API/database: not deployed by this operation

## What changed in this release

The research page (`/projects/suay/research.html`) became a **reverse-chronological log** with sixteen entries,
newest first: each entry carries the date, the decision, the number that decided it and a link to its report.
Status chips separate gains (green), failures and costs (amber) and model-derived numbers (grey). A header strip
shows `White paper v1.1 · updated 2026-10-21`, so visitors can see the paper is current.

Research is linked from the navigation of all eleven language pages (Thai label: งานวิจัย) and listed in
`sitemap.xml`.

## Rollback

The host keeps every release under `/opt/suay/releases/` and a configuration backup under `/opt/suay/backups/`.
To roll back, point the Nginx snippet at the previous release directory and reload Nginx; compare the vhost
before restoring it.

## Verification notes

- `research.html` returns HTTP 200 with the new title `SUAY Research Log | 50 office machines, measured`.
- The English and Thai landing pages and the XML sitemap return HTTP 200.
- The white paper on GitHub is byte-identical to the repository copy (24 398 characters).
- Search discovery is not claimed: deployment does not establish indexing.
