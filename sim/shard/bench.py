"""Map-reduce benchmark: split a document, process the pieces on many machines, assemble.

Sequential baseline = the whole document on one machine. Sharded = N pieces across N machines (round-robin over
the live fleet). Every run is verified against the sequential word/character totals, so a fast wrong answer
cannot win.

    python sim/shard/bench.py --base http://127.0.0.1:8080 --out report/shard
"""
import argparse
import json
import statistics
import time
from pathlib import Path

import httpx

SENTENCE = ('มาตรา ๔๒๐ ผู้ใดจงใจหรือประมาทเลินเล่อ ทำต่อบุคคลอื่นโดยผิดกฎหมายให้เขาเสียหายถึงแก่ชีวิตก็ดี '
            'แก่ร่างกายก็ดี อนามัยก็ดี เสรีภาพก็ดี ทรัพย์สินหรือสิทธิอย่างหนึ่งอย่างใดก็ดี ท่านว่าผู้นั้นทำละเมิด '
            'the quick brown fox jumps over the lazy dog and the titration curve reaches its equivalence point. ')


def corpus(target_bytes):
    block = SENTENCE * max(1, target_bytes // len(SENTENCE.encode()) + 1)
    return block.encode()[:target_bytes].decode('utf-8', 'ignore')


def call(client, base, payload):
    started = time.perf_counter()
    response = client.post(base.rstrip('/') + '/api/shard', json=payload,
                           headers={'X-SUAY-Request': '1'}, timeout=180)
    response.raise_for_status()
    body = response.json()
    body['ms_wall'] = round((time.perf_counter() - started) * 1000, 2)
    return body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:8080')
    parser.add_argument('--sizes', default='65536,262144,1048576')
    parser.add_argument('--chunks', default='2,4,8,16,32,50')
    parser.add_argument('--rounds', type=int, default=2000)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--out', default='report/shard')
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    with httpx.Client() as client:
        call(client, args.base, {'text': 'warm up', 'chunks': 1, 'rounds': 10})  # warm

        for size in [int(part) for part in args.sizes.split(',')]:
            text = corpus(size)
            baseline = None
            for _ in range(args.repeats):
                result = call(client, args.base, {'text': text, 'chunks': 1, 'mode': 'sequential',
                                                  'rounds': args.rounds})
                baseline = result if baseline is None else min(baseline, result, key=lambda item: item['ms_total'])
            rows.append({'size_bytes': size, 'chunks': 1, 'mode': 'sequential',
                         'ms_total': baseline['ms_total'], 'ms_dispatch': None, 'ms_assembly': 0,
                         'nodes_used': 1, 'words': baseline['words'], 'chars': baseline['chars'],
                         'sum_len': baseline['sum_len']})
            print(f"size {size:>8} sequential {baseline['ms_total']:>8.1f} ms  words {baseline['words']}", flush=True)

            for chunks in [int(part) for part in args.chunks.split(',')]:
                best = None
                for _ in range(args.repeats):
                    result = call(client, args.base, {'text': text, 'chunks': chunks, 'mode': 'sharded',
                                                      'rounds': args.rounds})
                    best = result if best is None else min(best, result, key=lambda item: item['ms_total'])
                assert best['words'] == baseline['words'] and best['chars'] == baseline['chars'], 'mismatch'
                rows.append({'size_bytes': size, 'chunks': best['chunks'], 'mode': 'sharded',
                             'ms_total': best['ms_total'], 'ms_dispatch': best.get('ms_dispatch'),
                             'ms_assembly': best.get('ms_assembly'), 'nodes_used': best['nodes_used'],
                             'words': best['words'], 'chars': best['chars'], 'sum_len': best['sum_len']})
                print(f"size {size:>8} chunks {best['chunks']:>3} {best['ms_total']:>8.1f} ms  "
                      f"nodes {best['nodes_used']:>2}  speedup {baseline['ms_total'] / best['ms_total']:>5.2f}x",
                      flush=True)

    for row in rows:
        base = next(item for item in rows if item['size_bytes'] == row['size_bytes'] and item['chunks'] == 1)
        row['speedup'] = round(base['ms_total'] / row['ms_total'], 2) if row['ms_total'] else 0
        row['efficiency'] = round(row['speedup'] / row['chunks'], 3)
        row['throughput_mb_s'] = round((row['size_bytes'] / 1e6) / (row['ms_total'] / 1000), 3) if row['ms_total'] else 0

    (out / 'bench.json').write_text(json.dumps({'rounds': args.rounds, 'rows': rows}, indent=2), encoding='utf-8')
    summary = {}
    for size in sorted({row['size_bytes'] for row in rows}):
        best = max((row for row in rows if row['size_bytes'] == size), key=lambda row: row['speedup'])
        summary[str(size)] = {'best_chunks': best['chunks'], 'speedup': best['speedup'],
                              'efficiency': best['efficiency'],
                              'sequential_ms': next(row['ms_total'] for row in rows
                                                    if row['size_bytes'] == size and row['chunks'] == 1)}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
