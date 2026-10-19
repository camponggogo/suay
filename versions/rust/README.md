# Rust version — resource agent (experimental)

This is a local hardware/memory supervisor, not a Rust rewrite of Petals, the organization controller or the public analytics service. It exposes no HTTP listener, remote shell or remotely supplied command channel. Model inference remains in an explicitly configured local backend.

```sh
cargo build --release --locked
cargo test --locked
cargo run --locked -- status
cargo run --locked -- check local.example.json
# Edit the example to an existing absolute executable path before running it:
cargo run --release --locked -- run local.example.json
```

Rust 1.88+ is required. `status` reports measured host memory and CPU information. On Linux cgroup v2, it also considers memory.max/current at the visible cgroup root. Nested/custom cgroup mounts and cgroup v1 require deployment-specific validation.

Before starting a backend, available memory must cover its configured budget plus resume headroom. Running backends are stopped when sampled available memory falls below the reserve or their process-tree RSS exceeds the budget. Repeated failures use bounded backoff and a maximum of five starts per ten minutes. The larger resume threshold avoids immediate low-memory restart loops.

On Windows, the owned process tree is attached to a Job Object with a job-memory limit and kill-on-close. Attachment occurs immediately after spawn; startup before attachment is not a zero-allocation race-free guarantee. If attaching limits fails, startup fails closed. Unix backends run in an owned process group, terminated on shutdown or memory protection. Use a dedicated service account; a backend must not daemonize or escape its process group. Sampling cannot enforce an instantaneous Unix memory ceiling: use systemd/cgroup limits on Linux for a kernel-enforced cap. CPU figures are telemetry, not a hard CPU limit.

No native Windows SCM installer, macOS launchd package, fleet transport, GPU-memory allocator or model migration is included. Use OS service management and validate cleanup on the target platform before unattended operation. Windows has been the local build target for this contribution; CI is configured to check other desktop OSes. No comparative Python/Rust performance benchmark is claimed.
