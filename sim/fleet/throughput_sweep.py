"""Throughput sweep for a heartbeat sink: how many requests per second can it actually absorb?

Unlike scale_test.py (which simulates N independent machines from one event loop and hits client-side limits
around 100 concurrent sockets), this measures the server: C continuous workers per level.

    python sim/fleet/throughput_sweep.py --targets http://127.0.0.1:8081/hb,http://127.0.0.1:8080/api/node/heartbeat
"""
import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

import httpx

KEY_HEADER = 'X-Swarm-Key'
KEY = 'sim-swarm-key'


async def worker(client, target, worker_id, deadline, counter, latencies):
    payload = {'node_id': f'sweep-{worker_id:03d}', 'zone': 'sweep', 'hostname': f'sweep-{worker_id}',
               'ip': '127.0.0.1'}
    while time.monotonic() < deadline:
        started = time.perf_counter()
        try:
            response = await client.post(target, json=payload,
                                         headers={KEY_HEADER: KEY, 'X-SUAY-Request': '1'})
            if response.status_code == 200:
                counter[0] += 1
                latencies.append((time.perf_counter() - started) * 1000)
        except httpx.HTTPError:
            pass


async def level(target, concurrency, seconds):
    counter = [0]
    latencies = []
    deadline = time.monotonic() + seconds
    limits = httpx.Limits(max_connections=concurrency * 2 + 8, max_keepalive_connections=concurrency * 2)
    async with httpx.AsyncClient(timeout=20, limits=limits) as client:
        started = time.monotonic()
        await asyncio.gather(*[worker(client, target, index, deadline, counter, latencies)
                               for index in range(concurrency)])
        elapsed = time.monotonic() - started
    ordered = sorted(latencies)
    return {'concurrency': concurrency, 'seconds': round(elapsed, 1), 'ok': counter[0],
            'rps': round(counter[0] / elapsed, 1),
            'p50_ms': round(statistics.median(ordered), 2) if ordered else 0,
            'p95_ms': round(ordered[int(0.95 * (len(ordered) - 1))], 2) if ordered else 0}


async def main_async(args):
    output = {'targets': []}
    for target in [part.strip() for part in args.targets.split(',') if part.strip()]:
        rows = []
        for concurrency in [int(part) for part in args.concurrency.split(',')]:
            row = await level(target, concurrency, args.seconds)
            rows.append(row)
            print(target, json.dumps(row), flush=True)
        output['targets'].append({'target': target, 'levels': rows})
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--targets', required=True)
    parser.add_argument('--concurrency', default='1,4,16,64')
    parser.add_argument('--seconds', type=float, default=8)
    parser.add_argument('--out', default='report/fleet/throughput_sweep.json')
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
