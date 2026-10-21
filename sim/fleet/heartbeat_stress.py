"""Heartbeat stress: can one hub process carry a 50-100 machine fleet?

Each virtual machine sends a heartbeat every 2 s (the deployed interval). We sweep fleet size and measure the
hub's response time and success rate, which is the part that decides whether 100 machines can even register.

    python sim/fleet/heartbeat_stress.py --base http://127.0.0.1:8080 --sizes 50,75,100 --seconds 12
"""
import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

import httpx

HEADER = 'X-Swarm-Key'
KEY = 'sim-swarm-key'


def percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))]


async def machine(client, base, index, deadline, samples, errors):
    payload = {'node_id': f'probe-{index:03d}', 'zone': 'stress', 'hostname': f'probe-{index:03d}',
               'ip': '127.0.0.1'}
    headers = {HEADER: KEY, 'X-SUAY-Request': '1'}
    while time.monotonic() < deadline:
        started = time.perf_counter()
        try:
            response = await client.post(base.rstrip('/') + '/api/node/heartbeat', json=payload, headers=headers)
            if response.status_code == 200:
                samples.append((time.perf_counter() - started) * 1000)
            else:
                errors.append(response.status_code)
        except httpx.HTTPError as exc:
            errors.append(type(exc).__name__)
        await asyncio.sleep(2.0)


async def run_size(base, machines, seconds):
    samples, errors = [], []
    deadline = time.monotonic() + seconds
    async with httpx.AsyncClient(timeout=10, limits=httpx.Limits(max_connections=256)) as client:
        started = time.monotonic()
        await asyncio.gather(*[machine(client, base, index, deadline, samples, errors) for index in range(machines)])
        elapsed = time.monotonic() - started
    expected = machines * (seconds / 2.0)
    return {
        'machines': machines,
        'seconds': round(elapsed, 2),
        'ok': len(samples),
        'errors': len(errors),
        'error_kinds': sorted({str(kind) for kind in errors}),
        'success_pct': round(100 * len(samples) / max(1, len(samples) + len(errors)), 2),
        'rps': round(len(samples) / elapsed, 2),
        'p50_ms': round(percentile(samples, 0.5), 1),
        'p95_ms': round(percentile(samples, 0.95), 1),
        'p99_ms': round(percentile(samples, 0.99), 1),
        'mean_ms': round(statistics.fmean(samples), 1) if samples else 0,
        'achieved_share_pct': round(100 * len(samples) / max(1, expected), 1),
    }


async def main_async(args):
    results = []
    for machines in [int(part) for part in args.sizes.split(',') if part.strip()]:
        result = await run_size(args.base, machines, args.seconds)
        results.append(result)
        print(json.dumps(result), flush=True)
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({'sizes': results, 'interval_s': 2.0}, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:8080')
    parser.add_argument('--sizes', default='50,75,100')
    parser.add_argument('--seconds', type=float, default=12)
    parser.add_argument('--out', default='report/fleet/heartbeat_stress.json')
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
