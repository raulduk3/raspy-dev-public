#!/bin/sh
set -eu
umask 077
# Each container receives only its own control token and persistent home.
export OPENRIG_AUTH_BEARER_TOKEN="$(cat /run/secrets/control_token)"
export OPENRIG_BIND_HOST=0.0.0.0
export OPENRIG_PORT=7433
if [ "$#" -gt 0 ]; then
    exec "$@"
fi
# Foreground process: Docker owns lifecycle, not a second background supervisor.
exec node /opt/openrig/node_modules/@openrig/cli/daemon/dist/index.js
