"""Isolate the gateway ceiling: raw server / with auth+policy / with upstream.

    python sim/gateway/ceiling_probe.py --base http://127.0.0.1:8080 --key suay_sim_loadgen_key --c 16
"""
import argparse
import asyncio
import statistics
import time

import httpx


async def drive(client, url, headers, concurrency, seconds, body=None):
    latencies = []
    errors = 0
    stop = time.perf_counter() + seconds

    async def worker():
        nonlocal errors
        while time.perf_counter() < stop:
            started = time.perf_counter()
            try:
                response = await (client.post(url, json=body, headers=headers) if body
                                  else client.get(url, headers=headers))
                if response.status_code >= 400:
                    errors += 1
            except httpx.HTTPError:
                errors += 1
            latencies.append((time.perf_counter() - started) * 1000)

    await asyncio.gather(*[worker() for _ in range(concurrency)])
    return latencies, errors


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:8080')
    parser.add_argument('--key', default='suay_sim_loadgen_key')
    parser.add_argument('--c', type=int, default=16)
    parser.add_argument('--seconds', type=float, default=6)
    args = parser.parse_args()

    auth = {'Authorization': f'Bearer {args.key}', 'X-SUAY-Request': '1'}
    chat = {'model': 'sim-model', 'messages': [{'role': 'user', 'content': 'ceiling probe'}]}
    probes = [
        ('raw /api/health', args.base + '/api/health', {}, None),
        ('auth /v1/models', args.base + '/v1/models', auth, None),
        ('completion', args.base + '/v1/chat/completions', auth, chat),
    ]
    limits = httpx.Limits(max_connections=args.c * 2, max_keepalive_connections=args.c * 2)
    async with httpx.AsyncClient(timeout=30, limits=limits) as client:
        for name, url, headers, body in probes:
            latencies, errors = await drive(client, url, headers, args.c, args.seconds, body)
            latencies.sort()
            rps = len(latencies) / args.seconds
            p50 = statistics.median(latencies)
            p95 = latencies[int(len(latencies) * 0.95) - 1]
            print(f'{name:<16} rps={rps:6.2f}  p50={p50:7.1f} ms  p95={p95:7.1f} ms  n={len(latencies):5d}  err={errors}')


if __name__ == '__main__':
    asyncio.run(main())
