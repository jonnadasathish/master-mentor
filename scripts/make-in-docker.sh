#!/usr/bin/env sh
# Run a Makefile target on a host without GNU make (only Docker required).
# The repo is mounted at the SAME absolute path so compose bind mounts resolve on the host daemon.
# A tiny image (docker:cli + make) is built once and cached, so later runs need no network.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
IMAGE=master-mentor-make:1
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  printf 'FROM docker:cli\nRUN apk add --no-cache make\n' | docker build -q -t "$IMAGE" - >/dev/null
fi
exec docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$ROOT":"$ROOT" -w "$ROOT" \
  -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
  "$IMAGE" make "$@"
