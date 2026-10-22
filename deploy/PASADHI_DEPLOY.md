# PASADHI landing — deployment

## What is live now

| URL | Status |
|---|---|
| https://campong.online/projects/pasadhi/ | **live** (release `20261022T123618851133Z`) |
| https://campong.online/projects/pasadhi/th/ | live |
| https://pasadhi.tech/ | **still the Hostinger parked page** (A record points to 2.57.91.91) |

The Nginx vhost for `pasadhi.tech` is already installed and answers correctly when asked directly:

```bash
curl -H 'Host: pasadhi.tech' http://187.52.120.204/ | grep PASADHI
```

## The one step only you can do: DNS

In Hostinger → **Domains → pasadhi.tech → DNS / Nameservers**:

| Type | Name | Value | TTL |
|---|---|---|---|
| A | `@` | `187.52.120.204` | 300 |
| A | `www` | `187.52.120.204` | 300 |

Remove the existing parking records (A/CNAME to `2.57.91.91` and the `parking` CNAME) or the old entry may win.
Wait 5–30 minutes, then:

```bash
nslookup pasadhi.tech      # must show 187.52.120.204
```

## Then enable HTTPS (one command)

```bash
ssh -i ~/.ssh/ssh_hostinger_deploy root@187.52.120.204 \
  "certbot --nginx -d pasadhi.tech -d www.pasadhi.tech --redirect -m hello@pasadhi.tech --agree-tos -n"
```

The vhost already serves HTTP; certbot will add the 443 block and the redirect.

## Re-deploying after a content change

```bash
python deploy/deploy_pasadhi.py            # dry-run: prints the plan
python deploy/deploy_pasadhi.py --apply    # uploads, reloads Nginx, verifies, rolls back on failure
```

The script only transfers the four files in `PUBLIC_FILES` (index, th/index, style.css, sitemap.xml), keeps every
release under `/opt/pasadhi/releases/<id>`, writes a backup under `/opt/pasadhi/backups/<id>` and restores the
previous Nginx configuration if any check fails.

## Why the earlier attempt failed

Password authentication for `root@187.52.120.204` is now rejected (the SUAY deployer failed the same way), so the
script prefers the key `~/.ssh/ssh_hostinger_deploy`, which works (`srv1913303`). Keep that key: it is the only
working credential for this host.

## Files

```
landing-pasadhi/
  index.html      English
  th/index.html   Thai
  style.css       shared
  sitemap.xml
  preview-en.png  rendered preview (1280 wide)
  preview-th.png
deploy/deploy_pasadhi.py
```
