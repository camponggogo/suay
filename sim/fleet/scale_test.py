"""Scale test: how many machines can one heartbeat sink carry?

Virtual machines post a heartbeat every `--interval` seconds and we measure what the sink actually delivers.
Use it against the old hub path (per-request SQLite) and the new node plane (in-memory + batched flush).

    python sim/fleet/scale_test.py --target http://127.0.0.1:8081/hb --sizes 100,250,500,1000 --interval 10
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


async def machine(client, target, index, interval, deadline, samples, errors):
    payload = {'node_id': f'scale-{index:05d}', 'zone': f'zone-{index % 3}', 'hostname': f'scale-{index:05d}',
               'ip': '127.0.0.1'}
    while time.monotonic() < deadline:
        started = time.perf_counter()
        try:
            response = await client.post(target, json=payload,
                                         headers={HEADER: KEY, 'X-SUAY-Request': '1'})
            if response.status_code == 200:
                samples.append((time.perf_counter() - started) * 1000)
            else:
                errors.append(str(response.status_code))
        except httpx.HTTPError as exc:
            errors.append(type(exc).__name__)
        await asyncio.sleep(interval)


async def run(target, machines, interval, seconds):
    samples, errors = [], []
    deadline = time.monotonic() + seconds
    async with httpx.AsyncClient(timeout=30, limits=httpx.Limits(max_connections=min(4096, machines + 64))) as client:
        started = time.monotonic()
        await asyncio.gather(*[machine(client, target, index, interval, deadline, samples, errors)
                               for index in range(machines)])
        elapsed = time.monotonic() - started
    ideal = machines * (elapsed / interval)
    return {
        'machines': machines,
        'interval_s': interval,
        'seconds': round(elapsed, 1),
        'delivered': len(samples),
        'errors': len(errors),
        'error_kinds': sorted({str(kind) for kind in errors})[:4],
        'offered_rps': round(machines / interval, 1),
        'achieved_rps': round(len(samples) / elapsed, 1),
        'delivered_pct': round(100 * len(samples) / max(1, ideal), 1),
        'p50_ms': round(percentile(samples, 0.5), 1),
        'p95_ms': round(percentile(samples, 0.95), 1),
        'p99_ms': round(percentile(samples, 0.99), 1),
        'mean_ms': round(statistics.fmean(samples), 1) if samples else 0.0,
    }


async def main_async(args):
    results = []
    for machines in [int(part) for part in args.sizes.split(',') if part.strip()]:
        result = await run(args.target, machines, args.interval, args.seconds)
        results.append(result)
        print(json.dumps(result), flush=True)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'runs': []}
    existing['runs'].append({'label': args.label, 'target': args.target, 'results': results})
    path.write_text(json.dumps(existing, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    parser.add_argument('--sizes', default='100,250,500,1000')
    parser.add_argument('--interval', type=float, default=10)
    parser.add_argument('--seconds', type=float, default=20)
    parser.add_argument('--label', default='node-plane')
    parser.add_argument('--out', default='report/fleet/scale_test.json')
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
