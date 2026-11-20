#!/usr/bin/env bash
# Run the installer end-to-end test locally in Docker (Docker Desktop must be running).
#
#   tests/installer/docker-test.sh                    # all images
#   tests/installer/docker-test.sh ubuntu:22.04       # one image
#
# Your working tree (including uncommitted changes) is mounted read-only; nothing on
# your machine is modified.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [ "$#" -gt 0 ]; then
  IMAGES=("$@")
else
  IMAGES=(ubuntu:22.04 ubuntu:24.04 debian:12 fedora:41)
fi

# Git Bash on Windows rewrites /src-style paths; this turns that off for docker.
export MSYS_NO_PATHCONV=1

failed=()
for image in "${IMAGES[@]}"; do
  echo "################ $image"
  if docker run --rm -v "$ROOT:/src:ro" "$image" sh /src/tests/installer/run-in-container.sh /src; then
    echo "################ $image: PASS"
  else
    echo "################ $image: FAIL"
    failed+=("$image")
  fi
done

if [ "${#failed[@]}" -gt 0 ]; then
  echo "Failed: ${failed[*]}" >&2
  exit 1
fi
echo "All installer tests passed: ${IMAGES[*]}"
