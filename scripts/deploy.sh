#!/usr/bin/env bash
# Build the static export and publish it to the Hetzner VPS.
# Usage: ./scripts/deploy.sh
set -euo pipefail

HOST="vps-hetzner"
REMOTE_DIR="/var/www/iliaskalalou.com"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT"

echo "==> Building static export"
npx next build

if [ ! -f out/index.html ]; then
  echo "!! out/index.html missing — aborting" >&2
  exit 1
fi

echo "==> Publishing to $HOST:$REMOTE_DIR"
rsync -az --delete --human-readable out/ "$HOST:$REMOTE_DIR/"

echo "==> Checking the live site"
code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 https://iliaskalalou.com/ || echo "000")
if [ "$code" = "200" ]; then
  echo "OK — https://iliaskalalou.com/ responded 200"
else
  echo "https://iliaskalalou.com/ responded $code (expected while DNS is not pointing here yet)"
  echo "Fallback URL: https://ilias.46-224-152-225.sslip.io/"
fi
