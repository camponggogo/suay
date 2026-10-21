"""SQLite vs PostgreSQL for the hot path: the atomic dual-budget consume plus a usage write.

Both backends run the identical two statements per "request", each with its own connection (the pattern the
control plane uses today), under 1/4/8/16 concurrent threads. Measures throughput and p95 per operation.

    python sim/store/bench.py --pg "postgresql://suay@127.0.0.1:55432/suay" --out report/store
"""
import argparse
import json
import sqlite3
import statistics
import threading
import time
from pathlib import Path

SQL_CONSUME = ('UPDATE tokens SET used=used+1 WHERE id=1 AND used<max_requests '
               'AND (max_tokens=0 OR inference_tokens<max_tokens)')
SQL_USAGE = 'UPDATE tokens SET inference_tokens=inference_tokens+7 WHERE id=1'


def setup_sqlite(path):
    conn = sqlite3.connect(path)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('DROP TABLE IF EXISTS tokens')
    conn.execute('CREATE TABLE tokens(id INTEGER PRIMARY KEY, used INTEGER DEFAULT 0, inference_tokens INTEGER DEFAULT 0, '
                 'max_requests INTEGER, max_tokens INTEGER DEFAULT 0)')
    conn.execute('INSERT INTO tokens(id, used, inference_tokens, max_requests, max_tokens) VALUES(1,0,0,100000000,0)')
    conn.commit()
    conn.close()


def setup_pg(dsn):
    import psycopg
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute('DROP TABLE IF EXISTS tokens')
        conn.execute('CREATE TABLE tokens(id INTEGER PRIMARY KEY, used INTEGER DEFAULT 0, '
                     'inference_tokens INTEGER DEFAULT 0, max_requests INTEGER, max_tokens INTEGER DEFAULT 0)')
        conn.execute('INSERT INTO tokens(id, used, inference_tokens, max_requests, max_tokens) '
                     'VALUES(1,0,0,100000000,0)')


def worker(backend, target, count, latencies, barrier):
    if backend == 'sqlite':
        def run():
            conn = sqlite3.connect(target, timeout=10)
            try:
                conn.execute(SQL_CONSUME)
                conn.execute(SQL_USAGE)
                conn.commit()
            finally:
                conn.close()
    else:
        import psycopg

        def run():
            with psycopg.connect(target, autocommit=True) as conn:
                conn.execute(SQL_CONSUME)
                conn.execute(SQL_USAGE)

    barrier.wait()
    for _ in range(count):
        started = time.perf_counter()
        run()
        latencies.append((time.perf_counter() - started) * 1000)


def bench(backend, target, concurrency, per_thread=120):
    latencies = []
    barrier = threading.Barrier(concurrency)
    threads = [threading.Thread(target=worker, args=(backend, target, per_thread, latencies, barrier))
               for _ in range(concurrency)]
    started = time.perf_counter()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    elapsed = time.perf_counter() - started
    ordered = sorted(latencies)
    return {'backend': backend, 'concurrency': concurrency, 'ops': len(latencies),
            'ops_per_s': round(len(latencies) / elapsed, 1),
            'p50_ms': round(statistics.median(ordered), 2),
            'p95_ms': round(ordered[int(0.95 * (len(ordered) - 1))], 2),
            'max_ms': round(ordered[-1], 2)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sqlite', default='report/store/store.db')
    parser.add_argument('--pg', default='postgresql://suay@127.0.0.1:55432/suay')
    parser.add_argument('--concurrency', default='1,4,8,16')
    parser.add_argument('--out', default='report/store')
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    setup_sqlite(args.sqlite)
    pg_ready = True
    try:
        setup_pg(args.pg)
    except Exception as exc:  # noqa: BLE001
        pg_ready = False
        print('postgres unavailable:', exc)

    rows = []
    for concurrency in [int(part) for part in args.concurrency.split(',')]:
        rows.append(bench('sqlite', args.sqlite, concurrency))
        print(json.dumps(rows[-1]), flush=True)
        if pg_ready:
            rows.append(bench('postgresql', args.pg, concurrency))
            print(json.dumps(rows[-1]), flush=True)

    (out / 'bench.json').write_text(json.dumps({'rows': rows}, indent=2), encoding='utf-8')
    print('written', out / 'bench.json')


if __name__ == '__main__':
    main()
