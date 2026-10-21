"""Drive N gateway ports concurrently and report per-port and aggregate throughput.

    python sim/gateway/parallel_probe.py --bases http://127.0.0.1:8082,http://127.0.0.1:8083 --c 16
"""
import argparse
import asyncio
import statistics
import time

import httpx


async def drive(client, base, headers, concurrency, seconds, body):
    latencies, errors = [], 0
    stop = time.perf_counter() + seconds

    async def worker():
        nonlocal errors
        while time.perf_counter() < stop:
            started = time.perf_counter()
            try:
                response = await client.post(base + '/v1/chat/completions', json=body, headers=headers)
                if response.status_code >= 400:
                    errors += 1
            except httpx.HTTPError:
                errors += 1
            latencies.append((time.perf_counter() - started) * 1000)

    await asyncio.gather(*[worker() for _ in range(concurrency)])
    return latencies, errors


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bases', required=True)
    parser.add_argument('--key', default='suay_sim_loadgen_key')
    parser.add_argument('--c', type=int, default=16)
    parser.add_argument('--seconds', type=float, default=6)
    args = parser.parse_args()

    bases = [b.strip() for b in args.bases.split(',') if b.strip()]
    headers = {'Authorization': f'Bearer {args.key}', 'X-SUAY-Request': '1'}
    body = {'model': 'sim-model', 'messages': [{'role': 'user', 'content': 'parallel probe'}]}
    per_port = max(1, args.c // len(bases))
    limits = httpx.Limits(max_connections=args.c * 2, max_keepalive_connections=args.c * 2)

    async with httpx.AsyncClient(timeout=60, limits=limits) as client:
        results = await asyncio.gather(
            *[drive(client, base, headers, per_port, args.seconds, body) for base in bases])
    total, errors = 0, 0
    for base, (latencies, err) in zip(bases, results):
        latencies.sort()
        rps = len(latencies) / args.seconds
        total += rps
        errors += err
        p50 = statistics.median(latencies)
        p95 = latencies[int(len(latencies) * 0.95) - 1]
        print(f'{base:<26} clients={per_port:>2}  rps={rps:6.2f}  p50={p50:7.1f} ms  p95={p95:7.1f} ms  err={err}')
    print(f'aggregate rps={total:6.2f}  errors={errors}  ({len(bases)} ports × {per_port} clients)')


if __name__ == '__main__':
    asyncio.run(main())
