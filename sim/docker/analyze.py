"""Analyse the concurrency sweep: derived metrics + publication scatter plots.

    python sim/docker/analyze.py --results sim/docker/results/paper
"""
import argparse
import csv
import json
import math
import statistics
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

BG = '#0b1020'
PANEL = '#121a33'
INK = '#e8ecff'
MUTED = '#8b93b8'
COLORS = {'p50': '#7c5cff', 'p95': '#22d3ee', 'p99': '#34d399', 'accent': '#fbbf24', 'bad': '#fb7185'}


def style(ax, title, xlabel, ylabel):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=MUTED, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color('#243055')
    ax.grid(True, color='#1d2745', linewidth=0.7, alpha=0.85)
    ax.set_title(title, color=INK, fontsize=11, pad=12)
    ax.set_xlabel(xlabel, color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)


def scatter(ax, xs, ys, color, label, marker='o', size=42):
    ax.scatter(xs, ys, s=size, color=color, edgecolors=BG, linewidths=0.8, label=label, zorder=3, marker=marker)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', default='sim/docker/results/paper')
    args = parser.parse_args()
    root = Path(args.results)
    steps = json.loads((root / 'summary.json').read_text(encoding='utf-8'))['steps']
    figures = root / 'figures'
    figures.mkdir(parents=True, exist_ok=True)

    concurrency = [step['concurrency'] for step in steps]
    rps = [step['rps'] for step in steps]
    mean_ms = [step['mean_ms'] for step in steps]
    p50 = [step['p50_ms'] for step in steps]
    p95 = [step['p95_ms'] for step in steps]
    p99 = [step['p99_ms'] for step in steps]
    bandwidth = [step['bandwidth_mbps'] for step in steps]
    dispatch = [step['server']['dispatch_mean_ms'] for step in steps]
    upstream = [step['server']['upstream_mean_ms'] for step in steps]
    residual = [max(0.0, step['mean_ms'] - step['server']['dispatch_mean_ms'] - step['server']['upstream_mean_ms'])
                for step in steps]

    # ---------------------------------------------------------------- model fit: saturating throughput
    # T(c) = Tmax * c / (c + k)  — Michaelis–Menten form, the standard congestion-law shape.
    # Fitted without SciPy: for each candidate k the optimal Tmax has a closed form, so a log grid suffices.
    def fit_saturation(xs, ys):
        best = (max(ys) * 1.4, 20.0, float('inf'))
        for candidate in np.logspace(-0.3, 3.2, 400):
            weights = np.array(xs, dtype=float) / (np.array(xs, dtype=float) + candidate)
            tmax_try = float(np.dot(ys, weights) / max(1e-12, np.dot(weights, weights)))
            residual = float(np.sum((np.array(ys) - tmax_try * weights) ** 2))
            if residual < best[2]:
                best = (tmax_try, float(candidate), residual)
        return best

    try:
        tmax, kmax, _ = fit_saturation(concurrency, rps)
        fit_ok = True
    except Exception:
        tmax, kmax = max(rps), statistics.mean(concurrency)
        fit_ok = False

    # knee: first point where the marginal throughput gain drops below 5% of the previous step
    knee = concurrency[-1]
    for index in range(1, len(rps)):
        gain = rps[index] - rps[index - 1]
        if gain / max(1e-9, rps[index - 1]) < 0.05:
            knee = concurrency[index - 1]
            break

    baseline_service = steps[0]['server']['dispatch_mean_ms'] + steps[0]['server']['upstream_mean_ms']
    amplification = [m / baseline_service if baseline_service else 0 for m in mean_ms]
    queue_delay = [max(0.0, m - baseline_service) for m in mean_ms]
    little = [rate * (latency / 1000) for rate, latency in zip(rps, mean_ms)]
    little_error = [abs(pred - c) / c * 100 for pred, c in zip(little, concurrency)]

    server_metrics = {}
    metrics_path = root / 'metrics_server.json'
    if metrics_path.exists():
        server_metrics = json.loads(metrics_path.read_text(encoding='utf-8'))
    counts = list(server_metrics.get('per_node_counts', {}).values())
    layers = steps[-1]['nodes_live']

    fig, ax = plt.subplots(figsize=(7.2, 4.6), facecolor=BG)
    style(ax, 'Throughput vs. concurrent clients', 'concurrent clients (C)', 'throughput (requests/s)')
    scatter(ax, concurrency, rps, COLORS['p50'], 'measured')
    grid = np.linspace(1, max(concurrency) * 1.05, 200)
    if fit_ok:
        ax.plot(grid, tmax * grid / (grid + kmax), color=COLORS['accent'], linewidth=1.6,
                label=f'fit T=C·{tmax:.1f}/(C+{kmax:.1f})')
    ax.axhline(tmax, color=MUTED, linestyle=':', linewidth=1, label=f'asymptote ≈ {tmax:.1f} req/s')
    ax.axvline(knee, color=COLORS['bad'], linestyle='--', linewidth=1, alpha=0.7, label=f'knee ≈ C={knee}')
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)
    fig.tight_layout()
    fig.savefig(figures / 'fig1_throughput_vs_concurrency.png', facecolor=BG, dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.6), facecolor=BG)
    style(ax, 'Response time vs. achieved throughput', 'throughput (requests/s)', 'mean response time (ms, log)')
    scatter(ax, rps, mean_ms, COLORS['p95'], 'operating points')
    for x, y, c in zip(rps, mean_ms, concurrency):
        ax.annotate(f'C={c}', (x, y), textcoords='offset points', xytext=(6, 4), fontsize=7, color=MUTED)
    ax.set_yscale('log')
    fig.tight_layout()
    fig.savefig(figures / 'fig2_latency_vs_throughput.png', facecolor=BG, dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.6), facecolor=BG)
    style(ax, 'Response-time percentiles vs. concurrency', 'concurrent clients (C)', 'latency (ms, log)')
    for series, key, label in ((p50, 'p50', 'p50'), (p95, 'p95', 'p95'), (p99, 'p99', 'p99')):
        scatter(ax, concurrency, series, COLORS[key], label, marker='o' if key == 'p50' else ('s' if key == 'p95' else '^'))
        ax.plot(concurrency, series, color=COLORS[key], linewidth=1, alpha=0.5)
    ax.set_yscale('log')
    ax.set_xscale('log')
    ax.set_xticks(concurrency)
    ax.set_xticklabels([str(c) for c in concurrency], fontsize=8)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)
    fig.tight_layout()
    fig.savefig(figures / 'fig3_percentiles_vs_concurrency.png', facecolor=BG, dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.6), facecolor=BG)
    style(ax, 'Gateway bandwidth vs. concurrency', 'concurrent clients (C)', 'payload bandwidth (Mbit/s)')
    scatter(ax, concurrency, bandwidth, COLORS['p99'], 'measured')
    for x, y, b in zip(concurrency, bandwidth, steps):
        ax.annotate(f"{b['bytes_per_request']/1024:.1f} KiB/req", (x, y), textcoords='offset points',
                    xytext=(5, 6), fontsize=7, color=MUTED)
    fig.tight_layout()
    fig.savefig(figures / 'fig4_bandwidth_vs_concurrency.png', facecolor=BG, dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.6, 4.8), facecolor=BG)
    style(ax, 'Where the response time goes: service floor vs. queueing', 'concurrent clients (C)', 'mean time (ms, log)')
    ax.fill_between(concurrency, [baseline_service] * len(concurrency), mean_ms,
                    color=COLORS['accent'], alpha=0.22, label='queueing + scheduling delay')
    ax.plot(concurrency, mean_ms, color=COLORS['accent'], linewidth=1.4, marker='o', markersize=4,
            label='measured mean response time')
    ax.axhline(baseline_service, color=COLORS['p50'], linestyle='--', linewidth=1.2,
               label=f'uncontended service ≈ {baseline_service:.0f} ms (C=1)')
    ax.annotate(f'{100 * queue_delay[-1] / mean_ms[-1]:.0f}% queueing',
                (concurrency[-1], mean_ms[-1]), textcoords='offset points', xytext=(-72, -18),
                fontsize=8, color=COLORS['accent'])
    ax.set_yscale('log')
    ax.set_xscale('log')
    ax.set_xticks(concurrency)
    ax.set_xticklabels([str(c) for c in concurrency], fontsize=8)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc='upper left')
    fig.tight_layout()
    fig.savefig(figures / 'fig5_time_decomposition.png', facecolor=BG, dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 5.0), facecolor=BG)
    style(ax, "Little's law check: C vs. λ·W", 'predicted concurrency λ·W', 'configured concurrency C')
    limit = max(max(concurrency), max(little)) * 1.08
    ax.plot([0, limit], [0, limit], color=MUTED, linestyle=':', linewidth=1, label='y = x')
    scatter(ax, little, concurrency, COLORS['p95'], 'measured')
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)
    fig.tight_layout()
    fig.savefig(figures / 'fig6_little_law.png', facecolor=BG, dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.6), facecolor=BG)
    style(ax, f'Dispatch fairness across {layers} live machines', 'machine index (sorted)', 'work units received')
    ordered = sorted(counts) if counts else [0]
    ax.bar(range(len(ordered)), ordered, color=COLORS['p50'], width=0.85)
    if ordered:
        cv = statistics.pstdev(ordered) / statistics.fmean(ordered) if len(ordered) > 1 and statistics.fmean(ordered) else 0
        ax.axhline(statistics.fmean(ordered), color=MUTED, linestyle=':', linewidth=1,
                   label=f'mean {statistics.fmean(ordered):.1f}, CV {cv:.2f}')
        ax.legend(frameon=False, fontsize=8, labelcolor=INK)
    fig.tight_layout()
    fig.savefig(figures / 'fig7_dispatch_fairness.png', facecolor=BG, dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.6), facecolor=BG)
    style(ax, 'Queue amplification: mean latency / measured service time', 'concurrent clients (C)', 'amplification (×)')
    scatter(ax, concurrency, amplification, COLORS['bad'], 'mean / (dispatch + upstream)')
    ax.axhline(1.0, color=MUTED, linestyle=':', linewidth=1, label='no queueing')
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)
    fig.tight_layout()
    fig.savefig(figures / 'fig8_queue_amplification.png', facecolor=BG, dpi=200)
    plt.close(fig)

    metrics = {
        'steps': len(steps),
        'clients_max': max(concurrency),
        'throughput_peak_rps': round(max(rps), 2),
        'throughput_asymptote_rps': round(float(tmax), 2),
        'saturation_k': round(float(kmax), 2),
        'fit_ok': bool(fit_ok),
        'knee_concurrency': int(knee),
        'latency_p50_ms_at_max': p50[-1],
        'latency_p95_ms_at_max': p95[-1],
        'latency_p99_ms_at_max': p99[-1],
        'latency_mean_ms_at_max': mean_ms[-1],
        'bandwidth_peak_mbps': round(max(bandwidth), 4),
        'bytes_per_request_mean': round(statistics.fmean([step['bytes_per_request'] for step in steps]), 1),
        'service_dispatch_mean_ms': round(statistics.fmean(dispatch), 2),
        'service_upstream_mean_ms': round(statistics.fmean(upstream), 2),
        'baseline_service_ms_c1': round(baseline_service, 2),
        'queue_delay_max_ms': round(max(queue_delay), 1),
        'queue_delay_at_max_pct': round(100 * queue_delay[-1] / mean_ms[-1], 1) if mean_ms[-1] else 0,
        'queue_amplification_max': round(max(amplification), 2),
        'little_law_max_error_pct': round(max(little_error), 2),
        'little_law_mean_error_pct': round(statistics.fmean(little_error), 2),
        'errors_total': sum(step['errors'] for step in steps),
        'success_rate_pct': round(100 * sum(step['ok'] for step in steps) / max(1, sum(step['requests'] for step in steps)), 3),
        'nodes_live': layers,
        'fairness_min': server_metrics.get('fairness_min', 0),
        'fairness_max': server_metrics.get('fairness_max', 0),
        'fairness_samples': server_metrics.get('nodes_dispatched', 0),
        'fairness_cv': round(statistics.pstdev(ordered) / statistics.fmean(ordered), 4) if len(ordered) > 1 and statistics.fmean(ordered) else 0,
    }
    (root / 'metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')

    table = ['| C | req | rps | mean | p50 | p95 | p99 | Mbit/s | dispatch | upstream |',
             '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for step in steps:
        table.append(f"| {step['concurrency']} | {step['requests']} | {step['rps']:.1f} | {step['mean_ms']:.0f} | "
                     f"{step['p50_ms']:.0f} | {step['p95_ms']:.0f} | {step['p99_ms']:.0f} | "
                     f"{step['bandwidth_mbps']:.2f} | {step['server']['dispatch_mean_ms']:.1f} | "
                     f"{step['server']['upstream_mean_ms']:.1f} |")
    (root / 'table.md').write_text('\n'.join(table), encoding='utf-8')

    print(json.dumps(metrics, indent=2))
    print('figures ->', figures)


if __name__ == '__main__':
    main()
