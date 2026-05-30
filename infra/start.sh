#!/bin/bash
set -e

# Mirror dashboard-ref-only's startup: create every directory hermes expects
# and seed a default config.yaml if the volume is empty. Without these,
# `hermes dashboard` endpoints that hit logs/, sessions/, cron/, etc. can fail
# with opaque errors even though no auth is actually involved.
mkdir -p /data/.hermes/cron /data/.hermes/sessions /data/.hermes/logs \
         /data/.hermes/memories /data/.hermes/skills /data/.hermes/pairing \
         /data/.hermes/hooks /data/.hermes/image_cache /data/.hermes/audio_cache \
         /data/.hermes/workspace /data/.hermes/skins /data/.hermes/plans \
         /data/.hermes/home

if [ ! -f /data/.hermes/config.yaml ] && [ -f /opt/hermes-agent/cli-config.yaml.example ]; then
  cp /opt/hermes-agent/cli-config.yaml.example /data/.hermes/config.yaml
fi

[ ! -f /data/.hermes/.env ] && touch /data/.hermes/.env

# Bootstrap OAuth tokens from env var (e.g. xAI Grok SuperGrok).
# Set HERMES_AUTH_JSON_BOOTSTRAP to the contents of a locally-generated
# ~/.hermes/auth.json. Written only once — subsequent token refreshes update
# the file in place on the persistent volume.
if [ ! -f /data/.hermes/auth.json ] && [ -n "${HERMES_AUTH_JSON_BOOTSTRAP}" ]; then
  printf '%s' "${HERMES_AUTH_JSON_BOOTSTRAP}" > /data/.hermes/auth.json
  chmod 600 /data/.hermes/auth.json
fi

# Prune old logs and sessions to keep volume usage in check.
find /data/.hermes/logs    -type f -mtime +7  -delete 2>/dev/null || true
find /data/.hermes/sessions -type f -mtime +30 -delete 2>/dev/null || true
find /data/.hermes/audio_cache -type f -mtime +3 -delete 2>/dev/null || true
find /data/.hermes/image_cache -type f -mtime +7 -delete 2>/dev/null || true

# Clear any stale gateway PID file left over from the previous container.
# `hermes gateway` writes /data/.hermes/gateway.pid on start but does not
# remove it on SIGTERM. Since /data is a persistent volume, the file
# survives container restarts and causes every subsequent boot to exit with
# "ERROR gateway.run: PID file race lost to another gateway instance".
# No hermes process can be running at this point (we're pre-exec in a fresh
# container), so removing the file unconditionally is safe.
rm -f /data/.hermes/gateway.pid

# Always overwrite SOUL.md and skills from the image so every redeploy picks
# up changes without needing to wipe the volume.
[ -f /app/config/SOUL.md ] && cp /app/config/SOUL.md /data/.hermes/SOUL.md
if [ -d /app/skills ]; then
  cp -rf /app/skills/. /data/.hermes/skills/
fi

# Seed Telegram topic config into config.yaml on first boot.
# This ensures topic IDs survive volume wipes — they're stored in the repo,
# not just on the volume.
if [ -f /app/config/telegram.yaml ] && [ -f /data/.hermes/config.yaml ]; then
  # Only inject if not already present (avoid overwriting user customisations)
  if ! grep -q "default_chat_id: -1003913424869" /data/.hermes/config.yaml 2>/dev/null; then
    # Append telegram section to config.yaml
    echo "" >> /data/.hermes/config.yaml
    cat /app/config/telegram.yaml >> /data/.hermes/config.yaml
  fi
fi

# Pre-approve the skip_finance_bot_commands shell hook in the allowlist so the
# gateway registers it automatically without a TTY prompt.
# The hooks: block is injected into config.yaml by write_config_yaml() in server.py.
ALLOWLIST=/data/.hermes/shell-hooks-allowlist.json
HOOK_CMD="/app/config/skip_finance_bot_commands.sh"
if ! grep -q "skip_finance_bot_commands" "$ALLOWLIST" 2>/dev/null; then
  python3 - <<'EOF'
import json, os
p = os.environ.get("ALLOWLIST", "/data/.hermes/shell-hooks-allowlist.json")
hook_cmd = os.environ.get("HOOK_CMD", "/app/config/skip_finance_bot_commands.sh")
try:
    d = json.load(open(p))
except Exception:
    d = {"approvals": []}
if not isinstance(d.get("approvals"), list):
    d["approvals"] = []
# Remove stale entry if any, then add fresh
d["approvals"] = [
    e for e in d["approvals"]
    if not (isinstance(e, dict) and e.get("command") == hook_cmd)
]
d["approvals"].append({
    "event": "pre_gateway_dispatch",
    "command": hook_cmd,
    "approved_at": "2026-05-30T00:00:00Z",
    "script_mtime_at_approval": None,
})
json.dump(d, open(p, "w"), indent=2)
print(f"[start.sh] pre-approved shell hook: {hook_cmd}", flush=True)
EOF
fi

exec python /app/server.py
