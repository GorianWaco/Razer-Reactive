#!/bin/bash
# Re-exec the command with the keyd group when keyd is running and this
# login session was started before the user was added to that group.
set -euo pipefail

if [ "${RAZER_KEYD_READY:-0}" != 1 ]; then
  if [ -S /run/keyd.socket ] || [ -S /var/run/keyd.socket ]; then
    if ! python3 -c 'import os, sys; sys.exit(0 if os.access("/run/keyd.socket", os.R_OK) or os.access("/var/run/keyd.socket", os.R_OK) else 1)'; then
      if getent group keyd >/dev/null && id -nG "$(id -un)" | grep -qw keyd && [ -x /usr/bin/newgrp ]; then
        export RAZER_KEYD_READY=1
        quoted=$(printf '%q ' "$@")
        exec /usr/bin/newgrp keyd <<EOF
exec $quoted
EOF
      fi
    fi
  fi
fi

exec "$@"
