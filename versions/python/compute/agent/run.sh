#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
docker build -t office-ai-swarm .
docker run -d --name ai-swarm-node --network host --restart unless-stopped --cpus "${NODE_CPUS:-1.5}" --memory "${NODE_MEMORY:-4g}" -e MODEL_NAME="${MODEL_NAME:-bigscience/bloom-560m}" -e NUM_BLOCKS="${NUM_BLOCKS:-2}" -v petals-node-cache:/cache office-ai-swarm
