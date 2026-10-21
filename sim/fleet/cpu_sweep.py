"""Sweep the per-machine CPU limit from 10% to 80% and measure the effect.

For each level: apply `docker update --cpus`, let the fleet settle, sample liveness, then run two short load
levels (C=1 and C=8) and read the hub's dispatch statistics.

    python sim/fleet/cpu_sweep.py --levels 0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8 --out report/cpu_sweep
"""
import argparse
import asyncio
import json
import statistics
import subprocess
import time
from pathlib import Path

import httpx

KEY = 'sim-swarm-key'


def node_names():
    out = subprocess.run(['docker', 'ps', '--filter', 'name=suay-sim-node-', '--format', '{{.Names}}'],
                         capture_output=True, text=True, timeout=60)
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def set_cpu(names, value):
    if not names:
        return False
    result = subprocess.run(['docker', 'update', f'--cpus={value}', *names],
                            capture_output=True, text=True, timeout=180)
    return result.returncode == 0


def percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))]


async def load_level(base, key, model, concurrency, seconds):
    url = base.rstrip('/') + '/v1/chat/completions'
    headers = {'Authorization': 'Bearer ' + key, 'X-SUAY-Request': '1'}
    payload = {'model': model, 'messages': [{'role': 'user', 'content': 'sweep'}], 'max_tokens': 8}
    rows = []

    async def worker(client, deadline):
        while time.monotonic() < deadline:
            started = time.perf_counter()
            status = 0
            try:
                response = await client.post(url, json=payload, headers=headers)
                status = response.status_code
            except httpx.HTTPError:
                status = 0
            rows.append(((time.perf_counter() - started) * 1000, status))

    async with httpx.AsyncClient(timeout=60, limits=httpx.Limits(max_connections=64)) as client:
        started = time.monotonic()
        deadline = started + seconds
        await asyncio.gather(*[worker(client, deadline) for _ in range(concurrency)])
        elapsed = time.monotonic() - started
    latencies = [row[0] for row in rows if row[1] == 200]
    return {'concurrency': concurrency, 'requests': len(rows), 'ok': len(latencies),
            'rps': round(len(rows) / elapsed, 2) if elapsed else 0,
            'mean_ms': round(statistics.fmean(latencies), 1) if latencies else 0,
            'p95_ms': round(percentile(latencies, 0.95), 1)}


def sample_liveness(base, rounds=4, gap=5):
    values = []
    with httpx.Client(timeout=20) as client:
        for _ in range(rounds):
            try:
                values.append(client.get(base.rstrip('/') + '/api/sim/stats').json()['nodes_live'])
            except (httpx.HTTPError, ValueError):
                pass
            time.sleep(gap)
    return {'samples': values, 'min': min(values) if values else 0, 'max': max(values) if values else 0,
            'mean': round(statistics.fmean(values), 1) if values else 0}


def metrics(base):
    try:
        with httpx.Client(timeout=20) as client:
            return client.get(base.rstrip('/') + '/api/metrics').json()
    except (httpx.HTTPError, ValueError):
        return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:8080')
    parser.add_argument('--key', default='suay_sim_loadgen_key')
    parser.add_argument('--model', default='sim-model')
    parser.add_argument('--levels', default='0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8')
    parser.add_argument('--seconds', type=float, default=5)
    parser.add_argument('--settle', type=float, default=18)
    parser.add_argument('--out', default='report/cpu_sweep')
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    names = node_names()
    print('nodes:', len(names), flush=True)
    results = []

    for level in [float(part) for part in args.levels.split(',')]:
        ok = set_cpu(names, level)
        time.sleep(args.settle)
        liveness = sample_liveness(args.base)
        before = metrics(args.base)
        one = asyncio.run(load_level(args.base, args.key, args.model, 1, args.seconds))
        eight = asyncio.run(load_level(args.base, args.key, args.model, 8, args.seconds))
        after = metrics(args.base)
        n0, n1 = before.get('dispatch_samples', 0), after.get('dispatch_samples', 0)
        m0, m1 = before.get('dispatch_mean_ms', 0), after.get('dispatch_mean_ms', 0)
        delta = round((m1 * n1 - m0 * n0) / (n1 - n0), 2) if n1 > n0 else None
        row = {'cpu': level, 'updated': ok, 'liveness': liveness,
               'c1': one, 'c8': eight, 'dispatch_ms_delta': delta,
               'dispatch_p95_ms': after.get('dispatch_p95_ms')}
        results.append(row)
        print(json.dumps(row), flush=True)
        (out / 'sweep.json').write_text(json.dumps({'rows': results}, indent=2), encoding='utf-8')

    print('written', out / 'sweep.json')


if __name__ == '__main__':
    main()
