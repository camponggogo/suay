# Python version

This version contains the existing organization control-plane pilot, separate experimental Petals agent/client, and the public landing-page visitor analytics service. The analytics service is independent of coordinator identities and resources.

**Begin with the [machine-by-machine Thai guide](../../docs/GETTING_STARTED.th.md). Choose A or B first; do not launch every component.**

| Role | Command / file | Where |
|---|---|---|
| A: management gateway | `python -m uvicorn control.app:create_app --factory --app-dir versions/python --host 127.0.0.1 --port 8090` | One management machine; needs a separate backend for AI output |
| B: coordinator + workers | `versions/python/compute/agent/auto_agent.py` | Same file on every compute machine; lowest active IPv4 becomes coordinator |
| B: prompt client | `versions/python/compute/client/app.py --coordinator http://AGENT_IP:8080` | User machine; terminal UI, separate Petals environment |

The A gateway is not automatically connected to B. Its dashboard does not start
Petals workers. The B client uses agent port 8080, not gateway port 8090.

- `control/`: organization dashboard, permissions and developer inference gateway.
- `compute/agent/`: trusted-LAN Petals process supervisor.
- `compute/client/`: Petals prompt client.
- `visitor_analytics/`: consent-based public website metrics and a separate admin account.

Path A only — Linux/macOS, from the repository root (Windows commands are in the guide):

```sh
python3 -m venv .venv-control
.venv-control/bin/python -m pip install -r versions/python/control/requirements.txt
.venv-control/bin/python -m uvicorn control.app:create_app --factory --app-dir versions/python --host 127.0.0.1 --port 8090
```

The control dashboard remains private/local by default. Its login is not the visitor-analytics admin login. See the root README and SECURITY.md for bootstrap and deployment requirements. Petals should use its own Python 3.10 environment. The Rust resource agent is an alternative local supervisor, not a feature-equivalent replacement for all Python components.
