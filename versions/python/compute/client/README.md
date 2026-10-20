# Petals prompt client — user machine

This is a **terminal client**, not a browser chat or a lightweight HTTP gateway
client. Install the client requirements in a separate Petals Python 3.10
environment on the user machine, after the compute agents have started.

From the repository root, after installation:

```sh
.venv-petals-client/bin/python versions/python/compute/client/app.py --coordinator http://192.168.1.10:8080 --max-new-tokens 32
```

Replace the example IP with a ready agent's LAN IP. The URL supplies bootstrap
status; generation uses Petals P2P. Do not use the A gateway's 8090 port. Wait for
`You (/quit to exit):`, type a prompt, and use `/quit` to exit.

Follow [setup guide B5–B6](../../../../docs/GETTING_STARTED.th.md) for full
installation and troubleshooting. Client dependencies and model components can
use substantial memory/storage; the illustration is not device certification.
