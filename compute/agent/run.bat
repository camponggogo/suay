@echo off
setlocal
cd /d "%~dp0"
if not defined MODEL_NAME set MODEL_NAME=bigscience/bloom-560m
if not defined NUM_BLOCKS set NUM_BLOCKS=2
if not defined NODE_MEMORY set NODE_MEMORY=4g
docker build -t office-ai-swarm .
if errorlevel 1 exit /b 1
docker run -d --name ai-swarm-node --network host --restart unless-stopped --cpus 1.5 --memory %NODE_MEMORY% -e MODEL_NAME=%MODEL_NAME% -e NUM_BLOCKS=%NUM_BLOCKS% -v petals-node-cache:/cache office-ai-swarm
