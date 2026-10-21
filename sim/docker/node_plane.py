"""Node plane: a heartbeat sink that scales independently of the inference gateway.

Design decisions, each one aimed at the measured ceiling (25 heartbeats/s on the old per-request SQLite path):

* **No database on the hot path.** Heartbeats land in a dict; a background thread flushes the whole map to
  SQLite in one transaction every SUAY_FLUSH_S seconds (default 10 s). 1 000 nodes at a 10 s interval is
  100 req/s, i.e. 10 flushes/s worth of rows in a single write.
* **Batch payloads.** A site collector can post {"nodes": [...]} and amortise one connection over many machines.
* **Shard by hash.** Nodes pick a shard with crc32(node_id) % len(shards). /aggregate fans out and merges, so
  the dashboard still sees one fleet.
* **Liveness is derived from memory**, never from a query per request.

    uvicorn node_plane:app --port 8081
"""
import asyncio
import asyncio
import hashlib
import os
import sqlite3
import threading
import time
import zlib
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

DB = os.getenv('SUAY_SIM_DB', '/data/sim.sqlite3')
FLUSH_S = float(os.getenv('SUAY_FLUSH_S', '10'))
SWARM_KEY = os.getenv('SUAY_SWARM_KEY', 'sim-swarm-key')
STALE_S = float(os.getenv('SUAY_STALE_S', '30'))
PEERS = [p.strip() for p in os.getenv('SUAY_NODE_PLANE_PEERS', '').split(',') if p.strip()]

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

STATE: Dict[str, Dict[str, Any]] = {}
LOCK = threading.Lock()
META = {'flush_count': 0, 'last_flush_at': 0.0, 'rows_flushed': 0}

# ---- prefix (KV) cache registry -------------------------------------------------------------
# Blocks are content-addressed; each block is owned by the machine that computed it. A request is routed to
# the machine holding the longest contiguous prefix, which is exactly what prefix caching needs to pay off.
BLOCK_TOKENS = int(os.getenv('SUAY_BLOCK_TOKENS', '256'))
LIVE_WINDOW = float(os.getenv('SUAY_LIVE_WINDOW_S', '15'))
CACHE: Dict[str, Dict[str, Any]] = {}      # block_key -> {'nodes': set, 'last_used': ts}
PREFILL_TPS = float(os.getenv('SUAY_PREFILL_TPS', '72.25'))   # measured: llama.cpp 0.5B Q4, this host
DECODE_TPS = float(os.getenv('SUAY_DECODE_TPS', '11.74'))     # measured generation rate
CACHE_LOCK = threading.Lock()
ROUTER = {'round_robin': 0, 'requests': 0, 'hits': 0, 'cached_tokens': 0, 'prefill_tokens': 0}


def block_keys(doc_id: str, blocks: int):
    return [hashlib.sha256(f'{doc_id}:{index}'.encode()).hexdigest()[:24] for index in range(blocks)]


def longest_prefix(nodes: List[Dict[str, Any]], keys: List[str]) -> tuple:
    """Return (node, contiguous_blocks) for the machine holding the longest prefix of `keys`."""
    best_node, best_len = None, 0
    with CACHE_LOCK:
        for node in nodes:
            length = 0
            for key in keys:
                owners = CACHE.get(key, {}).get('nodes', set())
                if node['id'] in owners:
                    length += 1
                else:
                    break
            if length > best_len:
                best_node, best_len = node, length
    return best_node, best_len


def remember(node_id: str, keys: List[str]) -> None:
    now = time.time()
    with CACHE_LOCK:
        for key in keys:
            entry = CACHE.setdefault(key, {'nodes': set(), 'last_used': now})
            entry['nodes'].add(node_id)
            entry['last_used'] = now
        if len(CACHE) > 20000:  # keep the registry bounded
            for key in sorted(CACHE, key=lambda item: CACHE[item]['last_used'])[:2000]:
                CACHE.pop(key, None)


@app.post('/api/serve')
async def serve(request: Request):
    """Simulate one request against the real fleet layout, with or without prefix-cache routing.

    Timing uses the measured prefill/decode rates of this project; the routing decision, cache ownership and
    hit accounting are real state, so the hit-rate and locality numbers are measured, not assumed.
    """
    body = await request.json()
    doc_id = str(body.get('doc_id', 'doc'))
    shared_tokens = max(0, int(body.get('shared_tokens', 0)))
    question_tokens = max(1, int(body.get('question_tokens', 50)))
    output_tokens = max(1, int(body.get('output_tokens', 150)))
    policy = str(body.get('policy', 'cache_aware'))
    blocks = max(0, (shared_tokens + BLOCK_TOKENS - 1) // BLOCK_TOKENS)
    keys = block_keys(doc_id, blocks)

    with LOCK:
        now = time.time()
        nodes = [{'id': node_id, 'ip': record['ip']} for node_id, record in STATE.items()
                 if record['ip'] and now - record['last_seen'] <= LIVE_WINDOW]
    if not nodes:
        return JSONResponse({'detail': 'no live machines'}, status_code=503)

    if policy == 'round_robin':
        with LOCK:
            ROUTER['round_robin'] = (ROUTER['round_robin'] + 1) % len(nodes)
            node = nodes[ROUTER['round_robin']]
        cached_blocks = 0
    else:
        node, cached_blocks = longest_prefix(nodes, keys)
        if node is None:
            with LOCK:
                ROUTER['round_robin'] = (ROUTER['round_robin'] + 1) % len(nodes)
                node = nodes[ROUTER['round_robin']]

    cached_tokens = min(shared_tokens, cached_blocks * BLOCK_TOKENS)
    prefill_tokens = max(1, shared_tokens - cached_tokens) + question_tokens
    ttft_s = prefill_tokens / PREFILL_TPS
    total_s = ttft_s + output_tokens / DECODE_TPS

    remember(node['id'], keys)
    with LOCK:
        ROUTER['requests'] += 1
        ROUTER['cached_tokens'] += cached_tokens
        ROUTER['prefill_tokens'] += prefill_tokens
        if cached_tokens > 0:
            ROUTER['hits'] += 1

    return {'policy': policy, 'doc_id': doc_id, 'node': node['id'], 'cached_tokens': cached_tokens,
            'prefill_tokens': prefill_tokens, 'ttft_s': round(ttft_s, 3), 'total_s': round(total_s, 3),
            'hit': cached_tokens > 0}


@app.post('/api/cache_reset')
def cache_reset():
    with CACHE_LOCK:
        CACHE.clear()
    with LOCK:
        ROUTER.update({'round_robin': 0, 'requests': 0, 'hits': 0, 'cached_tokens': 0, 'prefill_tokens': 0})
    return {'ok': True}


@app.get('/api/cache_stats')
def cache_stats():
    with CACHE_LOCK:
        blocks = len(CACHE)
    with LOCK:
        stats = dict(ROUTER)
    stats['blocks'] = blocks
    stats['hit_rate'] = round(stats['hits'] / stats['requests'], 3) if stats['requests'] else 0.0
    return stats


def flush_once() -> None:
    """One transaction for the whole map. Cheap even with thousands of rows."""
    with LOCK:
        snapshot = [(node_id, record['zone'], record['hostname'], record['ip'], record['last_seen'], record['beats'])
                    for node_id, record in STATE.items()]
    if not snapshot:
        return
    try:
        connection = sqlite3.connect(DB, timeout=10)
        connection.execute('CREATE TABLE IF NOT EXISTS sim_heartbeats(node_id TEXT PRIMARY KEY, zone TEXT, '
                           'hostname TEXT, ip TEXT, last_seen REAL, beats INTEGER DEFAULT 0)')
        with connection:
            connection.executemany(
                'INSERT INTO sim_heartbeats(node_id,zone,hostname,ip,last_seen,beats) VALUES(?,?,?,?,?,?) '
                'ON CONFLICT(node_id) DO UPDATE SET last_seen=excluded.last_seen, zone=excluded.zone, '
                'ip=excluded.ip, hostname=excluded.hostname, beats=excluded.beats',
                snapshot)
            connection.execute('DELETE FROM sim_heartbeats WHERE last_seen < ?', (time.time() - 300,))
        connection.close()
        with LOCK:
            META['flush_count'] += 1
            META['last_flush_at'] = time.time()
            META['rows_flushed'] += len(snapshot)
    except sqlite3.Error:
        pass  # the plane keeps serving from memory; a failed flush is retried next tick


def flusher() -> None:
    while True:
        time.sleep(FLUSH_S)
        flush_once()


threading.Thread(target=flusher, daemon=True).start()


@app.get('/healthz')
def health():
    return {'ok': True, 'nodes': len(STATE), 'flush_s': FLUSH_S}


@app.post('/hb')
async def heartbeat(request: Request):
    if request.headers.get('X-Swarm-Key') != SWARM_KEY:
        return JSONResponse({'detail': 'Unauthorized swarm key'}, status_code=401)
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({'detail': 'Invalid JSON'}, status_code=400)
    items = body.get('nodes') if isinstance(body, dict) and isinstance(body.get('nodes'), list) else [body]
    now = time.time()
    accepted = 0
    with LOCK:
        for item in items:
            if not isinstance(item, dict):
                continue
            node_id = str(item.get('node_id', ''))[:64]
            if not node_id:
                continue
            record = STATE.get(node_id)
            if record is None:
                STATE[node_id] = {'zone': str(item.get('zone', 'default'))[:64],
                                  'hostname': str(item.get('hostname', ''))[:64],
                                  'ip': str(item.get('ip', ''))[:64],
                                  'last_seen': now, 'beats': 1}
            else:
                record['last_seen'] = now
                record['beats'] += 1
                if item.get('ip'):
                    record['ip'] = str(item['ip'])[:64]
            accepted += 1
    return {'ok': True, 'accepted': accepted}


def snapshot(now: Optional[float] = None) -> Dict[str, Any]:
    now = now or time.time()
    with LOCK:
        nodes = [{'id': node_id, 'zone': record['zone'], 'ip': record['ip'],
                  'status': 'live' if now - record['last_seen'] <= 10 else
                            ('stale' if now - record['last_seen'] <= STALE_S else 'offline'),
                  'age_s': round(max(0.0, now - record['last_seen']), 1),
                  'beats': record['beats']} for node_id, record in STATE.items()]
        meta = dict(META)
    zones: Dict[str, int] = {}
    for node in nodes:
        zones[node['zone']] = zones.get(node['zone'], 0) + 1
    return {'nodes': nodes,
            'zones': [{'name': name, 'count': count} for name, count in sorted(zones.items())],
            'stats': {'nodes_total': len(nodes),
                      'nodes_live': sum(1 for node in nodes if node['status'] == 'live'),
                      'beats': sum(node['beats'] for node in nodes), **meta},
            'shard': os.getenv('SUAY_SHARD_ID', '0'),
            'peers': PEERS}


@app.get('/stats')
def stats():
    data = snapshot()
    return data['stats']


@app.get('/topology')
def topology():
    data = snapshot()
    nodes = data['nodes']
    links = [{'source': node['id'], 'target': 'hub', 'kind': 'uplink'} for node in nodes]
    grouped: Dict[str, List[str]] = {}
    for node in nodes:
        grouped.setdefault(node['zone'], []).append(node['id'])
    for identifiers in grouped.values():
        for index, identifier in enumerate(identifiers):
            links.append({'source': identifier, 'target': identifiers[(index + 1) % len(identifiers)],
                          'kind': 'mesh'})
    return {'hub': {'name': 'suay-hub'}, 'nodes': nodes, 'links': links, 'zones': data['zones'],
            'stats': data['stats'], 'generated_at': time.time()}


@app.post('/api/shard')
async def shard(request: Request):
    """Map-reduce: split the document, process pieces on many machines, assemble the totals."""
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({'detail': 'Invalid JSON'}, status_code=400)
    text = str(body.get('text', ''))
    if not text:
        return JSONResponse({'detail': 'text required'}, status_code=422)
    chunks = max(1, min(256, int(body.get('chunks', 1) or 1)))
    rounds = max(0, min(200000, int(body.get('rounds', 200) or 0)))
    mode = 'sequential' if str(body.get('mode', 'sharded')) == 'sequential' else 'sharded'

    with LOCK:
        now = time.time()
        nodes = [{'id': node_id, 'ip': record['ip']} for node_id, record in STATE.items()
                 if record['ip'] and now - record['last_seen'] <= 10]
    if not nodes:
        return JSONResponse({'detail': 'no live machines'}, status_code=503)

    started = time.perf_counter()
    if mode == 'sequential' or chunks == 1:
        async with httpx.AsyncClient(timeout=180, trust_env=False) as client:
            response = await client.post('http://' + nodes[0]['ip'] + ':9100/work',
                                         json={'text': text, 'rounds': rounds, 'job': 0})
        result = response.json()
        return {'mode': mode, 'chunks': 1, 'nodes_used': 1,
                'ms_total': round((time.perf_counter() - started) * 1000, 2), 'ms_assembly': 0.0,
                'words': result.get('words', 0), 'chars': result.get('chars', 0),
                'sum_len': result.get('sum_len', 0), 'digest': combined_digest([result])}

    pieces = chunk_text(text, chunks)
    targets = [nodes[index % len(nodes)] for index in range(len(pieces))]
    dispatch_started = time.perf_counter()
    async with httpx.AsyncClient(timeout=180, trust_env=False) as client:
        responses = await asyncio.gather(*[
            client.post('http://' + targets[index]['ip'] + ':9100/work',
                        json={'text': piece, 'rounds': rounds, 'job': index})
            for index, piece in enumerate(pieces)])
    dispatch_ms = round((time.perf_counter() - dispatch_started) * 1000, 2)
    results = [response.json() for response in responses]
    assembly_started = time.perf_counter()
    totals = {'words': sum(item.get('words', 0) for item in results),
              'chars': sum(item.get('chars', 0) for item in results),
              'sum_len': sum(item.get('sum_len', 0) for item in results)}
    digest = combined_digest(results)
    assembly_ms = round((time.perf_counter() - assembly_started) * 1000, 3)
    return {'mode': mode, 'chunks': len(pieces), 'nodes_used': len({node['id'] for node in targets}),
            'ms_total': round((time.perf_counter() - started) * 1000, 2), 'ms_dispatch': dispatch_ms,
            'ms_assembly': assembly_ms, **totals, 'digest': digest}


def chunk_text(text, chunks):
    if chunks <= 1:
        return [text]
    target = max(1, len(text) // chunks)
    pieces = []
    start = 0
    while start < len(text) and len(pieces) < chunks - 1:
        end = min(len(text), start + target)
        boundary = text.find(' ', end)
        if boundary == -1:
            boundary = len(text)
        if boundary <= start:
            boundary = min(len(text), start + target)
        pieces.append(text[start:boundary])   # the separator belongs to the next piece
        start = boundary
    pieces.append(text[start:])
    return [piece for piece in pieces if piece]


def combined_digest(results):
    digest = hashlib.sha256()
    for item in results:
        digest.update(str(item.get('digest', '')).encode())
    return digest.hexdigest()


@app.get('/aggregate')
async def aggregate():
    """Merge this shard with its peers, so one dashboard can watch an unlimited fleet."""
    merged = snapshot()
    if not PEERS:
        return merged
    async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
        for peer in PEERS:
            try:
                response = await client.get(peer.rstrip('/') + '/topology')
                other = response.json()
            except (httpx.HTTPError, ValueError):
                continue
            merged['nodes'].extend(other.get('nodes', []))
            merged['stats']['nodes_total'] += other.get('stats', {}).get('nodes_total', 0)
            merged['stats']['nodes_live'] += other.get('stats', {}).get('nodes_live', 0)
            merged['stats']['beats'] += other.get('stats', {}).get('beats', 0)
    return merged


def shard_for(node_id: str, shards: int) -> int:
    return zlib.crc32(node_id.encode()) % max(1, shards)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.getenv('PORT', '8081')), log_level='warning')
