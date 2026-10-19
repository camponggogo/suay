# Deploy the public landing page

The existing host provided for this project serves **campong.online** (with `a`), not `compong.online`. SUAY is published at **https://campong.online/projects/suay/** using host Nginx. No Docker or public coordinator is needed for this static site.

Only these files are allowed into a release: `landing/index.html`, `style.css`, `main.js`, `assets/suay-network.svg`, `assets/suay-logo.svg`, `assets/suay-device-landing.png`. The controller, API, SQLite database, environment files and SSH password are never uploaded. The architecture figure is a repository documentation asset and is not needed by the static website.

## Workflow

1. Install `python -m pip install -r deploy/requirements.txt` in a deployment environment.
2. Set the three `HOSTINGER_SSH_*` environment variables, or copy `.env.example` to the **ignored** `deploy/.env` and enter credentials locally. Do not pass passwords on command lines.
3. Verify the server's SSH host key with its administrator/provider and add it to your user's known-hosts file. The helper rejects unknown or changed host keys.
4. Run `python deploy/deploy_landing.py` for a dry-run and preflight Nginx validation.
5. Run `python deploy/deploy_landing.py --apply` to publish.

The helper targets the already inspected `/etc/nginx/sites-available/campong.online` server block. It deliberately refuses an unfamiliar vhost layout. It adds one include for `nginx-suay-snippet.conf` and keeps the existing root and other projects intact. For a different host/domain, review and adapt the helper/config rather than reusing credentials blindly.

Each deployment creates `/opt/suay/releases/<UTC-release-id>`, saves prior configuration in `/opt/suay/backups/<UTC-release-id>`, atomically switches `/opt/suay/current`, runs `nginx -t` and reloads Nginx. Public SUAY and main-site HTTPS checks must pass. On failure, the helper restores the previous configuration and release link. Backups and old releases are retained for review; no broad cleanup is performed.

For later rollback, read the selected backup's `previous.json`, restore its saved vhost/snippet and previous release symlink, then validate Nginx before reloading. A first deployment has no prior SUAY release. Do not restore an old whole-vhost backup over unrelated changes made since that deployment; compare it first.

## Legacy reference files

`install-host-nginx.sh`, `nginx-campong-main-snippet.conf` and `nginx-container.conf` were supplied for the company root website. They are reference material, **not the SUAY deployment entrypoint**. Running the root installer would target `/`, not `/projects/suay/`.
