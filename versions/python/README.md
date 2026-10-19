# Python version

This version contains the existing organization control-plane pilot, separate experimental Petals agent/client, and the public landing-page visitor analytics service. The analytics service is independent of coordinator identities and resources.

- `control/`: organization dashboard, permissions and developer inference gateway.
- `compute/agent/`: trusted-LAN Petals process supervisor.
- `compute/client/`: Petals prompt client.
- `visitor_analytics/`: consent-based public website metrics and a separate admin account.

From the repository root:

```sh
python -m pip install -r versions/python/control/requirements.txt
python -m uvicorn control.app:create_app --factory --app-dir versions/python --host 127.0.0.1 --port 8090
```

The control dashboard remains private/local by default. Its login is not the visitor-analytics admin login. See the root README and SECURITY.md for bootstrap and deployment requirements. Petals should use its own Python 3.10 environment. The Rust resource agent is an alternative local supervisor, not a feature-equivalent replacement for all Python components.
