"""L4 dispatcher: receive on one port, round-robin to N gateway ports, stream the reply back.

    python sim/gateway/multiport.py --listen 8090 --backends 127.0.0.1:8082,127.0.0.1:8083
"""
import argparse
import asyncio
import itertools
import time


class Pool:
    def __init__(self, backends):
        self.backends = backends
        self.cycle = itertools.cycle(range(len(backends)))

    def pick(self):
        return self.backends[next(self.cycle)]


async def pipe(reader, writer):
    try:
        while True:
            chunk = await reader.read(65536)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
    except (ConnectionResetError, asyncio.IncompleteReadError, BrokenPipeError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def handle(client_reader, client_writer, pool, stats):
    host, port = pool.pick()
    started = time.perf_counter()
    try:
        upstream_reader, upstream_writer = await asyncio.open_connection(host, port)
    except OSError:
        client_writer.close()
        return
    stats['active'] += 1
    try:
        await asyncio.gather(
            pipe(client_reader, upstream_writer),
            pipe(upstream_reader, client_writer),
        )
    finally:
        stats['active'] -= 1
        stats['done'] += 1
        stats['last_ms'] = (time.perf_counter() - started) * 1000
        for writer in (client_writer, upstream_writer):
            try:
                writer.close()
            except Exception:
                pass


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--listen', type=int, default=8090)
    parser.add_argument('--backends', default='127.0.0.1:8082,127.0.0.1:8083')
    args = parser.parse_args()

    backends = []
    for item in args.backends.split(','):
        host, port = item.strip().rsplit(':', 1)
        backends.append((host, int(port)))
    pool = Pool(backends)
    stats = {'active': 0, 'done': 0, 'last_ms': 0.0}

    server = await asyncio.start_server(
        lambda r, w: handle(r, w, pool, stats), '0.0.0.0', args.listen, backlog=2048)
    print(f'listening on {args.listen} -> {backends}', flush=True)
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())
