#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
docker build -t petals-client .
docker run --rm -it --network host -v petals-client-cache:/cache petals-client "$@"
