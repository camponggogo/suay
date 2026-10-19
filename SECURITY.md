# Security policy

This project is an early pilot, not a hardened enterprise control plane. Supported maintenance targets the current source tree; there are no production support or response-time guarantees.

Do not open an exploit report containing credentials, employee data or operational infrastructure in a public issue. Use GitHub's private vulnerability reporting on the SUAY repository **if the maintainer has enabled it**. If that channel is unavailable, request a private contact through an issue without publishing exploit details or secrets. No monitored security email is currently declared.

## Local bootstrap

The first database creates `admin / suay1234` unless `SUAY_BOOTSTRAP_PASSWORD` is set. Every newly created account must change its password before accessing data or issuing tokens. Password changes invalidate all of that account's sessions and API tokens. Admin resets, account disablement and grant changes also revoke access. Default credentials must never be exposed to a public listener, even with forced rotation.

The default launch command binds only 127.0.0.1. Before organizational access, use HTTPS at a trusted reverse proxy, `SUAY_COOKIE_SECURE=1`, restrictive firewall rules and correct proxy/header configuration. Do not trust forwarded headers from arbitrary sources. The application uses a custom header and same-origin checks for mutations, strict HttpOnly session cookies, password hashing, hashed API keys and login throttling. These controls are not a substitute for SSO/MFA, external rate limiting, a security assessment or encrypted backups.

Keep SQLite/state files readable only by the service account. Local database audit rows are not tamper-proof; send audit events to a protected external system before production use. Session lifetime is eight hours. Expired sessions are cleared on login; token metadata remains for audit and must be managed according to organizational retention policy.

The developer inference endpoint uses a fixed operator-configured upstream and an approved model list, not arbitrary URLs or shell arguments. Do not configure an upstream that calls SUAY itself. Authenticate and isolate the upstream separately. API keys never grant admin user-management rights. Lifetime request budgets count accepted inference submissions, including upstream failures; they are not hard model-token or currency budgets. Token revocation affects new requests, not already running inference.

The original UDP discovery / Petals dashboard is a separate unauthenticated experiment. Adding the control application does not secure that network or retrofit authorization into the original Client. Do not expose the old agent API or connect it directly to an untrusted network. Native worker identity, acknowledged command execution, mutual TLS enrollment, SSO/MFA and signed updates remain future work.
