#!/bin/sh
# Install company-root proxy for campong.online → 127.0.0.1:9499
# Does not overwrite /projects/* snippets or replace the whole vhost.
set -e

APP_DIR="${DEPLOY_PATH:-/opt/campong-main}"
SNIPPET_SRC="$APP_DIR/deploy/nginx-campong-main-snippet.conf"
SNIPPET_DEST="/etc/nginx/snippets/campong-main.conf"
VHOST="/etc/nginx/sites-available/campong.online"

if [ ! -f "$SNIPPET_SRC" ]; then
	echo "ERROR: missing $SNIPPET_SRC"
	exit 1
fi

if ! command -v nginx >/dev/null 2>&1; then
	echo "ERROR: host nginx is required (TLS terminator). Do not bind this container to :80/:443."
	exit 1
fi

cp -f "$SNIPPET_SRC" "$SNIPPET_DEST"

python3 - "$VHOST" "$SNIPPET_DEST" <<'PY'
from pathlib import Path
import re
import sys

vhost = Path(sys.argv[1])
snippet = Path(sys.argv[2])
include_line = "    include /etc/nginx/snippets/campong-main.conf;"

if not vhost.exists():
    raise SystemExit(f"ERROR: missing vhost {vhost}")

text = vhost.read_text(encoding="utf-8")
if "snippets/campong-main.conf" in text:
    print("Host nginx already includes campong-main snippet")
    raise SystemExit(0)

# Drop a previous static location / inside the default HTTPS server only,
# so we can proxy / without duplicating the location.
pattern = re.compile(
    r"location\s+/\s*\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}",
    re.MULTILINE,
)

def replace_root_location(server_text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        body = match.group(0)
        if "projects/" in body or "proxy_pass http://127.0.0.1:9499" in body:
            return body
        return "    # replaced static location / with campong-main Docker proxy\n"

    return pattern.sub(repl, server_text, count=1)

servers = re.split(r"(?=^server\s*\{)", text, flags=re.MULTILINE)
changed = []
for block in servers:
    if "listen 443" in block and "server_name campong.online" in block and "projects/" in block or (
        "listen 443" in block and "campong.online" in block
    ):
        if "listen 443" in block and "www.campong.online" not in block.split("{", 1)[0]:
            block = replace_root_location(block)
            if include_line.strip() not in block:
                # Insert before the server block's last closing brace.
                # Literal } in an f-string must be written as }}.
                head, sep, tail = block.rpartition("\n}")
                if not sep:
                    raise SystemExit("ERROR: HTTPS server block has no closing brace")
                block = f"{head}\n{include_line}\n}}{tail}"
        changed.append(block)
    else:
        changed.append(block)

new_text = "".join(changed)
if new_text == text:
    # Fallback: append include before the last closing brace of the file's first 443 server.
    raise SystemExit("ERROR: could not locate HTTPS server block to include campong-main snippet")

vhost.write_text(new_text, encoding="utf-8")
print("Included", snippet, "into", vhost)
PY

ln -sfn "$VHOST" /etc/nginx/sites-enabled/campong.online
nginx -t
if command -v systemctl >/dev/null 2>&1; then
	systemctl reload nginx
else
	nginx -s reload
fi

echo "Host nginx: / → 127.0.0.1:9499 (projects/* unchanged)"
