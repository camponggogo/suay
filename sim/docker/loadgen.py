"""Concurrency sweep with byte accounting and server-side metrics.

Records, per request: latency, status, request bytes, response bytes. Per step: throughput, percentiles and the
hub's own view (dispatch RTT to a real machine, upstream RTT), so the report can separate queueing from service
time instead of guessing.

    python sim/docker/loadgen.py --base http://127.0.0.1:8080 --key suay_sim_loadgen_key \
        --steps 1,2,4,8,12,16,24,32,40,50 --seconds 10 --out results/paper
"""
import argparse
import asyncio
import csv
import json
import statistics
import time
from pathlib import Path

import httpx

HEADER = 'Authorization'


def percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


async def worker(client, url, key, model, deadline, rows, step):
    headers = {HEADER: 'Bearer ' + key, 'X-SUAY-Request': '1'}
    payload = {'model': model, 'messages': [{'role': 'user', 'content': 'measure'}], 'max_tokens': 8}
    encoded = json.dumps(payload).encode()
    while time.monotonic() < deadline:
        started = time.perf_counter()
        status = 0
        response_bytes = 0
        try:
            response = await client.post(url, content=encoded, headers=headers)
            status = response.status_code
            response_bytes = len(response.content)
        except httpx.HTTPError:
            status = 0
        rows.append((step, round((time.perf_counter() - started) * 1000, 2), status,
                     len(encoded), response_bytes))


async def snapshot_metrics(client, base):
    try:
        response = await client.get(base.rstrip('/') + '/api/metrics')
        return response.json()
    except (httpx.HTTPError, ValueError):
        return {}


async def run(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    summary = []
    url = args.base.rstrip('/') + '/v1/chat/completions'

    async with httpx.AsyncClient(timeout=60, limits=httpx.Limits(max_connections=256)) as client:
        for _ in range(3):
            await client.post(url, json={'model': args.model, 'messages': [{'role': 'user', 'content': 'warm'}]},
                              headers={HEADER: 'Bearer ' + args.key, 'X-SUAY-Request': '1'})

        for concurrency in [int(part) for part in args.steps.split(',') if part.strip()]:
            before = await snapshot_metrics(client, args.base)
            try:
                stats_before = (await client.get(args.base.rstrip('/') + '/api/sim/stats')).json()
            except httpx.HTTPError:
                stats_before = {}

            step_rows = []
            started = time.monotonic()
            deadline = started + args.seconds
            await asyncio.gather(*[worker(client, url, args.key, args.model, deadline, step_rows, concurrency)
                                   for _ in range(concurrency)])
            elapsed = time.monotonic() - started

            after = await snapshot_metrics(client, args.base)
            try:
                stats_after = (await client.get(args.base.rstrip('/') + '/api/sim/stats')).json()
            except httpx.HTTPError:
                stats_after = {}

            latencies = [row[1] for row in step_rows if row[2] == 200]
            errors = sum(1 for row in step_rows if row[2] != 200)
            request_bytes = sum(row[3] for row in step_rows)
            response_bytes = sum(row[4] for row in step_rows)
            total_bytes = request_bytes + response_bytes

            entry = {
                'concurrency': concurrency,
                'requests': len(step_rows),
                'ok': len(latencies),
                'errors': errors,
                'elapsed_s': round(elapsed, 3),
                'rps': round(len(step_rows) / elapsed, 2) if elapsed else 0,
                'success_rps': round(len(latencies) / elapsed, 2) if elapsed else 0,
                'mean_ms': round(statistics.fmean(latencies), 2) if latencies else 0,
                'p50_ms': round(percentile(latencies, 0.50), 2),
                'p95_ms': round(percentile(latencies, 0.95), 2),
                'p99_ms': round(percentile(latencies, 0.99), 2),
                'max_ms': round(max(latencies), 2) if latencies else 0,
                'stdev_ms': round(statistics.pstdev(latencies), 2) if len(latencies) > 1 else 0,
                'bandwidth_mbps': round(total_bytes * 8 / elapsed / 1e6, 4) if elapsed else 0,
                'bytes_per_request': round(total_bytes / len(step_rows), 1) if step_rows else 0,
                'nodes_live': stats_after.get('nodes_live', stats_before.get('nodes_live', 0)),
                'server': {
                    'dispatch_mean_ms': after.get('dispatch_mean_ms', 0),
                    'dispatch_p95_ms': after.get('dispatch_p95_ms', 0),
                    'upstream_mean_ms': after.get('upstream_mean_ms', 0),
                    'upstream_p95_ms': after.get('upstream_p95_ms', 0),
                    'requests_delta': (after.get('requests', 0) - before.get('requests', 0)),
                    'nodes_dispatched': after.get('nodes_dispatched', 0),
                    'fairness_min': after.get('fairness_min', 0),
                    'fairness_max': after.get('fairness_max', 0),
                },
            }
            summary.append(entry)
            rows.extend(step_rows)
            print(f"c={concurrency:>3} rps={entry['rps']:>7} mean={entry['mean_ms']:>8} "
                  f"p95={entry['p95_ms']:>8} bw={entry['bandwidth_mbps']:>7} Mbps err={errors}", flush=True)

    with (out / 'latency.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['concurrency', 'latency_ms', 'status', 'req_bytes', 'resp_bytes'])
        writer.writerows(rows)
    (out / 'summary.json').write_text(json.dumps({'steps': summary}, indent=2), encoding='utf-8')
    print('wrote', out / 'summary.json')
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:8080')
    parser.add_argument('--key', required=True)
    parser.add_argument('--model', default='sim-model')
    parser.add_argument('--steps', default='1,2,4,8,12,16,24,32,40,50')
    parser.add_argument('--seconds', type=float, default=10)
    parser.add_argument('--out', default='sim/docker/results/paper')
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == '__main__':
    main()
