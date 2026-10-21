"""Prefix-cache benefit benchmark against the running fleet.

Workload: a document Q&A pattern. `repeat_ratio` of requests reuse one of three popular documents (the common
enterprise case: the same policy PDF, the same contract), the rest are unique.

Policies:
  round_robin  — every request does a full prefill, no cache lookup (the baseline we measured earlier)
  cache_aware  — route to the machine holding the longest prefix; only the uncached suffix is prefilled

Timing comes from the measured prefill/decode rates (72.25 / 11.74 tok/s); routing and hit accounting are real
state in the node plane.

    python sim/kv/bench.py --base http://127.0.0.1:8081 --out report/kv
"""
import argparse
import json
import statistics
from pathlib import Path

import httpx


def percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))]


def run_workload(client, base, policy, size_tokens, repeat_ratio, requests):
    client.post(base.rstrip('/') + '/api/cache_reset').raise_for_status()
    samples = []
    for index in range(requests):
        popular = (index * 7919) % 100 < int(repeat_ratio * 100)
        doc_id = f'popular-{index % 3}' if popular else f'unique-{index}'
        response = client.post(base.rstrip('/') + '/api/serve', json={
            'doc_id': doc_id, 'shared_tokens': size_tokens, 'question_tokens': 50,
            'output_tokens': 150, 'policy': policy})
        response.raise_for_status()
        samples.append(response.json())
    stats = client.get(base.rstrip('/') + '/api/cache_stats').json()
    ttfts = [item['ttft_s'] for item in samples]
    totals = [item['total_s'] for item in samples]
    return {
        'policy': policy, 'size_tokens': size_tokens, 'repeat_ratio': repeat_ratio, 'requests': requests,
        'ttft_p50_s': round(percentile(ttfts, 0.5), 2), 'ttft_p95_s': round(percentile(ttfts, 0.95), 2),
        'total_p50_s': round(percentile(totals, 0.5), 2),
        'throughput_rpm': round(60 * requests / sum(totals), 1) if sum(totals) else 0,
        'hit_rate': stats['hit_rate'],
        'prefill_tokens': stats['prefill_tokens'],
        'cached_tokens': stats['cached_tokens'],
        'block_reuse_pct': round(100 * stats['cached_tokens'] /
                                 max(1, stats['cached_tokens'] + stats['prefill_tokens']), 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:8081')
    parser.add_argument('--sizes', default='2000,8000')
    parser.add_argument('--repeats', default='0,25,50,75,90')
    parser.add_argument('--requests', type=int, default=240)
    parser.add_argument('--out', default='report/kv')
    args = parser.parse_args()

    rows = []
    with httpx.Client(timeout=60) as client:
        for size in [int(part) for part in args.sizes.split(',')]:
            for ratio in [int(part) / 100 for part in args.repeats.split(',')]:
                for policy in ('round_robin', 'cache_aware'):
                    row = run_workload(client, args.base, policy, size, ratio, args.requests)
                    rows.append(row)
                    print(json.dumps(row), flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'bench.json').write_text(json.dumps({'rows': rows}, indent=2), encoding='utf-8')
    print('written', out / 'bench.json')


if __name__ == '__main__':
    main()
