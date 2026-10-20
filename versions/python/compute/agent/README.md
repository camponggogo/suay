# Petals compute agent — coordinator and worker

**Run `auto_agent.py` on every machine contributing compute.** There is no separate
coordinator executable. The lowest active IPv4 is elected coordinator; it also
runs a Petals backend like the other workers.

Follow [setup guide B1–B4](../../../../docs/GETTING_STARTED.th.md) from the repository
root for installation, per-machine IP configuration, startup order and checks.
Use a dedicated Python 3.10 environment. Legacy Docker launchers are optional;
the guide uses native Linux commands.

Status/dashboard: `http://AGENT_IP:8080`. This is separate from the organization
gateway on 8090. Live processes do not guarantee complete model block coverage.
The pilot is unauthenticated and must stay within a trusted, isolated test LAN.
