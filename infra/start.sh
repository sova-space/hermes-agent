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

# Always overwrite SOUL.md, skills, and plugins from the image so every
# redeploy picks up changes without needing to wipe the volume.
[ -f /app/config/SOUL.md ] && cp /app/config/SOUL.md /data/.hermes/SOUL.md
if [ -d /app/skills ]; then
  cp -rf /app/skills/. /data/.hermes/skills/
  # Substitute service discovery variables so skills stay portable across Railway accounts.
  # Any ${VAR} in a skill file is replaced with the runtime env value at startup.
  find /data/.hermes/skills -name "*.md" | while read -r f; do
    sed -i "s|\${FINANCE_API_URL}|${FINANCE_API_URL}|g" "$f"
    # Substitute all AGENT_*_URL variables so any skill can reference them portably.
    for _var in $(env | grep -oE '^AGENT_[A-Z_]+_URL' | sort -u); do
      _val=$(eval "echo \"\$$_var\"")
      sed -i "s|\${$_var}|${_val}|g" "$f"
    done
  done
fi
if [ -d /app/plugins ]; then
  rm -rf /data/.hermes/plugins
  cp -rf /app/plugins /data/.hermes/plugins
else
  rm -rf /data/.hermes/plugins
fi

# Inject Telegram config into config.yaml on every boot.
# Using a content hash so changes in telegram.yaml are always picked up —
# not just on first boot.
if [ -f /app/config/telegram.yaml ] && [ -f /data/.hermes/config.yaml ]; then
  TELEGRAM_HASH=$(md5sum /app/config/telegram.yaml | cut -d' ' -f1)
  if ! grep -q "# telegram-hash: ${TELEGRAM_HASH}" /data/.hermes/config.yaml 2>/dev/null; then
    # Remove old telegram section (from the 'telegram:' key to end of file)
    sed -i '/^telegram:/,$ d' /data/.hermes/config.yaml
    # Remove any stale hash comment
    sed -i '/^# telegram-hash:/d' /data/.hermes/config.yaml
    # Append updated telegram section with hash marker
    echo "" >> /data/.hermes/config.yaml
    echo "# telegram-hash: ${TELEGRAM_HASH}" >> /data/.hermes/config.yaml
    cat /app/config/telegram.yaml >> /data/.hermes/config.yaml
  fi
fi


exec python /app/server.py
