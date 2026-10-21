"""Hub for the 50-machine Docker simulation.

Composes the real SUAY control plane (`versions/python/control`) with the token-policy middleware from
`sim/token_policy.py`, and adds the two endpoints a fleet simulation needs:

  POST /api/node/heartbeat   node plane, authenticated by a pre-shared swarm key
  GET  /api/sim/stats        live/total nodes and heartbeat count, for the load generator

A deterministic load-generator key is seeded on first boot so the benchmark never depends on the
browser login flow. That key is a simulation fixture, not a production pattern.
"""
import asyncio
import hashlib
import hmac
import itertools
import json
import os
import secrets
import sys
import threading
import time
from pathlib import Path

import httpx
from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'versions' / 'python'))
sys.path.insert(0, str(ROOT / 'sim'))

from control.app import create_app  # noqa: E402
import token_policy as policy  # noqa: E402

DB = Path(os.getenv('SUAY_SIM_DB', '/data/sim.sqlite3'))
APPROVED = [m.strip() for m in os.getenv('SUAY_SIM_MODELS', 'sim-model').split(',') if m.strip()]
UPSTREAM = os.getenv('SUAY_UPSTREAM', 'http://upstream:9000/v1/chat/completions')
SWARM_KEY = os.getenv('SUAY_SWARM_KEY', 'sim-swarm-key')
NODE_PLANE = os.getenv('SUAY_NODE_PLANE', '').rstrip('/')
LOAD_KEY = os.getenv('SUAY_SIM_KEY', 'suay_sim_loadgen_key')

DB.parent.mkdir(parents=True, exist_ok=True)
STATIC = ROOT / 'versions' / 'python' / 'control' / 'static'

# Every observed traffic event becomes a travelling pulse in the 3D view.
EVENTS = []
EVENTS_LOCK = threading.Lock()
EVENT_IDS = itertools.count(1)
MAX_EVENTS = 800
DISPATCH = {'index': 0}


class Metrics:
    """Server-side counters used by the paper experiments."""

    def __init__(self):
        self.lock = threading.Lock()
        self.dispatches = []
        self.upstreams = []
        self.requests = 0
        self.failures = 0

    def record(self, node, dispatch_ms, upstream_ms):
        with self.lock:
            self.requests += 1
            if dispatch_ms is None:
                self.failures += 1
            else:
                self.dispatches.append((node, float(dispatch_ms)))
            if upstream_ms is not None:
                self.upstreams.append(float(upstream_ms))
            if len(self.dispatches) > 6000:
                del self.dispatches[:2000]
            if len(self.upstreams) > 6000:
                del self.upstreams[:2000]

    def snapshot(self):
        with self.lock:
            dispatches = list(self.dispatches)
            upstreams = list(self.upstreams)
            requests = self.requests
            failures = self.failures
        dispatch_ms = sorted(value for _, value in dispatches)
        per_node = {}
        for node, _ in dispatches:
            per_node[node] = per_node.get(node, 0) + 1

        def pct(values, fraction):
            if not values:
                return 0.0
            index = min(len(values) - 1, max(0, int(round(fraction * (len(values) - 1)))))
            return round(values[index], 2)

        return {
            'requests': requests,
            'failures': failures,
            'dispatch_samples': len(dispatch_ms),
            'dispatch_p50_ms': pct(dispatch_ms, 0.5),
            'dispatch_p95_ms': pct(dispatch_ms, 0.95),
            'dispatch_mean_ms': round(sum(dispatch_ms) / len(dispatch_ms), 2) if dispatch_ms else 0,
            'upstream_samples': len(upstreams),
            'upstream_p50_ms': pct(sorted(upstreams), 0.5),
            'upstream_p95_ms': pct(sorted(upstreams), 0.95),
            'upstream_mean_ms': round(sum(upstreams) / len(upstreams), 2) if upstreams else 0,
            'nodes_dispatched': len(per_node),
            'per_node_counts': per_node,
            'fairness_min': min(per_node.values()) if per_node else 0,
            'fairness_max': max(per_node.values()) if per_node else 0,
        }


METRICS = Metrics()


def push(kind, source, target, rtt_ms=None):
    with EVENTS_LOCK:
        EVENTS.append({'id': next(EVENT_IDS), 'at': time.time(), 'kind': kind,
                       'source': source, 'target': target, 'rtt_ms': rtt_ms})
        if len(EVENTS) > MAX_EVENTS:
            del EVENTS[:len(EVENTS) - MAX_EVENTS]


app = create_app(DB, upstream='', models=APPROVED)
store = policy.TokenStore(DB, dsn=os.getenv('SUAY_PG_DSN', ''))
store.migrate()


def dispatch_work(job_id):
    """Send a real unit of work to one live machine and measure the round trip."""
    rows = live_nodes()
    if not rows:
        return None, None
    DISPATCH['index'] = (DISPATCH['index'] + 1) % len(rows)
    target = rows[DISPATCH['index']]
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=0.8, trust_env=False) as client:
            client.post('http://' + str(target['ip']) + ':9100/work', json={'job': job_id})
        return target['node_id'], round((time.perf_counter() - started) * 1000, 2)
    except httpx.HTTPError:
        return target['node_id'], None


def handle_event(name, ctx, **extra):
    """Wraps a real inference request so the visualisation shows the actual flow."""
    if name == 'begin':
        push('request', 'client', 'hub')
        node, rtt = dispatch_work(int(time.time() * 1000))
        ctx['node'] = node
        ctx['dispatch_ms'] = rtt
        if node:
            push('dispatch', 'hub', node, rtt)
    elif name == 'end':
        node = ctx.get('node')
        upstream = extra.get('upstream_ms')
        dispatch = ctx.get('dispatch_ms')
        if node:
            push('result', node, 'hub', dispatch)
        push('response', 'hub', 'client', upstream)
        METRICS.record(node, dispatch, upstream)


app.add_middleware(policy.TokenPolicyMiddleware, store=store,
                   upstream=UPSTREAM, approved_models=APPROVED, on_event=handle_event)

with store.connect() as conn:
    conn.execute('CREATE TABLE IF NOT EXISTS sim_heartbeats(node_id TEXT PRIMARY KEY, zone TEXT, '
                 'hostname TEXT, ip TEXT, last_seen REAL, beats INTEGER DEFAULT 0)')
    beat_columns = ({row['name'] for row in conn.execute('PRAGMA table_info(sim_heartbeats)')}
                     if store.backend == 'sqlite' else {'node_id', 'zone', 'hostname', 'ip', 'last_seen', 'beats'})
    if store.backend == 'sqlite' and 'ip' not in beat_columns:
        conn.execute('ALTER TABLE sim_heartbeats ADD COLUMN ip TEXT')
    # The benchmark key belongs to a dedicated non-admin account, so an admin password change or grant
    # edit during the run cannot revoke it. It is re-armed on every boot: a simulation fixture, not a pattern.
    # Only the SQLite store also holds the control-plane users; on the PostgreSQL hot-path store the benchmark
    # key simply has no owner row (the token schema allows owner = 0).
    loader = None
    if store.backend == 'sqlite':
        loader = conn.execute("SELECT id FROM users WHERE username='sim-loader'").fetchone()
        if loader is None:
            conn.execute(
                'INSERT INTO users(username,password,role,zones,nodes,must_change) VALUES(?,?,?,?,?,0)',
                ('sim-loader', policy.digest(secrets.token_urlsafe(32)), 'command_line', '["*"]', '[]'))
            loader = conn.execute("SELECT id FROM users WHERE username='sim-loader'").fetchone()
    owner_id = loader['id'] if loader else 0
    existing = conn.execute('SELECT id FROM tokens WHERE hash=?', (policy.digest(LOAD_KEY),)).fetchone()
    if existing is None:
        conn.execute(
            'INSERT INTO tokens(hash,owner,name,scopes,expires,max_requests,used,inference_tokens,'
            'revoked,max_tokens,period_start,models) VALUES(?,?,?,?,?,?,0,0,0,0,?,?)',
            (policy.digest(LOAD_KEY), owner_id, 'sim-loadgen', json.dumps(['inference']),
             time.time() + 365 * 86400, 10_000_000, time.time(), '[]'))
    else:
        conn.execute('UPDATE tokens SET owner=?,revoked=0,expires=? WHERE id=?',
                     (owner_id, time.time() + 365 * 86400, existing['id']))


@app.post('/api/node/heartbeat')
async def heartbeat(request: Request):
    if not hmac.compare_digest(request.headers.get('X-Swarm-Key', ''), SWARM_KEY):
        return JSONResponse({'detail': 'Unauthorized swarm key'}, status_code=401)
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({'detail': 'Invalid JSON'}, status_code=400)
    node_id = str(body.get('node_id', ''))[:64]
    zone = str(body.get('zone', 'default'))[:64]
    hostname = str(body.get('hostname', ''))[:64]
    ip = str(body.get('ip', ''))[:64]
    if not node_id:
        return JSONResponse({'detail': 'node_id required'}, status_code=422)
    now = time.time()
    with store.connect() as conn:
        conn.execute(
            'INSERT INTO sim_heartbeats(node_id,zone,hostname,ip,last_seen,beats) VALUES(?,?,?,?,?,1) '
            'ON CONFLICT(node_id) DO UPDATE SET last_seen=excluded.last_seen, ip=excluded.ip, '
            'hostname=excluded.hostname, beats=beats+1',
            (node_id, zone, hostname, ip, now))
        conn.execute('INSERT OR IGNORE INTO nodes(id,zone) VALUES(?,?)', (node_id, zone))
    push('heartbeat', node_id, 'hub')
    push('ack', 'hub', node_id, 1.0)
    return {'ok': True, 'heartbeat_at': now}


@app.get('/neural')
def neural_page():
    return FileResponse(STATIC / 'neural3d.html')


@app.get('/neural-flat')
def neural_flat_page():
    return FileResponse(STATIC / 'neural.html')


@app.get('/neural3d.js')
def neural3d_script():
    return FileResponse(STATIC / 'neural3d.js', media_type='text/javascript')


@app.get('/vendor/three.module.js')
def three_module():
    return FileResponse(STATIC / 'vendor' / 'three.module.js', media_type='text/javascript')


@app.get('/vendor/three.core.js')
def three_core():
    return FileResponse(STATIC / 'vendor' / 'three.core.js', media_type='text/javascript')


@app.get('/vendor/three-LICENSE.txt')
def three_license():
    return FileResponse(STATIC / 'vendor' / 'three-LICENSE.txt', media_type='text/plain')


@app.get('/neural.js')
def neural_script():
    return FileResponse(STATIC / 'neural.js', media_type='text/javascript')


@app.get('/neural.css')
def neural_style():
    return FileResponse(STATIC / 'neural.css', media_type='text/css')


@app.get('/api/topology')
def topology():
    if NODE_PLANE:
        try:
            with httpx.Client(timeout=3, trust_env=False) as client:
                return client.get(NODE_PLANE + '/topology').json()
        except (httpx.HTTPError, ValueError):
            pass
    now = time.time()
    with store.connect() as conn:
        conn.execute('DELETE FROM sim_heartbeats WHERE last_seen < ?', (now - 300,))
        rows = [dict(row) for row in conn.execute(
            'SELECT node_id, zone, hostname, last_seen, beats FROM sim_heartbeats ORDER BY zone, node_id')]
    nodes = []
    zone_counts = {}
    for row in rows:
        age = max(0.0, now - row['last_seen'])
        status = 'live' if age <= 10 else ('stale' if age <= 30 else 'offline')
        nodes.append({'id': row['node_id'], 'zone': row['zone'], 'status': status,
                      'age_s': round(age, 1), 'beats': row['beats']})
        zone_counts[row['zone']] = zone_counts.get(row['zone'], 0) + 1

    links = [{'source': node['id'], 'target': 'hub', 'kind': 'uplink'} for node in nodes]
    grouped = {}
    for node in nodes:
        grouped.setdefault(node['zone'], []).append(node['id'])
    for identifiers in grouped.values():
        for index, identifier in enumerate(identifiers):
            links.append({'source': identifier, 'target': identifiers[(index + 1) % len(identifiers)],
                          'kind': 'mesh'})
    return {
        'hub': {'name': 'suay-hub'},
        'nodes': nodes,
        'links': links,
        'zones': [{'name': name, 'count': count} for name, count in sorted(zone_counts.items())],
        'stats': stats(),
        'generated_at': now,
    }


@app.get('/api/metrics')
def metrics():
    return METRICS.snapshot()


@app.get('/api/events')
def events(since: int = 0, limit: int = 240):
    with EVENTS_LOCK:
        newest = EVENTS[-1]['id'] if EVENTS else since
        picked = [event for event in EVENTS if event['id'] > since][:limit]
    return {'events': picked, 'now': time.time(), 'latest': newest}


@app.post('/api/shard')
async def shard(request: Request):
    """Map-reduce over the fleet: split text, process on many machines, assemble the result."""
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

    nodes = live_nodes()
    if not nodes:
        return JSONResponse({'detail': 'no live machines'}, status_code=503)

    started = time.perf_counter()
    if mode == 'sequential' or chunks == 1:
        payload = {'text': text, 'rounds': rounds, 'job': 0}
        async with httpx.AsyncClient(timeout=120, trust_env=False) as client:
            response = await client.post('http://' + nodes[0]['ip'] + ':9100/work', json=payload)
        result = response.json()
        total_ms = round((time.perf_counter() - started) * 1000, 2)
        return {'mode': mode, 'chunks': 1, 'nodes_used': 1, 'ms_total': total_ms, 'ms_assembly': 0.0,
                'words': result.get('words', 0), 'chars': result.get('chars', 0),
                'sum_len': result.get('sum_len', 0), 'digest': combined_digest([result]),
                'worker': result.get('node')}

    boundaries = chunk_text(text, chunks)
    assignments = [(index, piece) for index, piece in enumerate(boundaries)]
    assignment_nodes = [nodes[index % len(nodes)] for index in range(len(assignments))]
    dispatch_started = time.perf_counter()
    async with httpx.AsyncClient(timeout=120, trust_env=False) as client:
        responses = await asyncio.gather(*[
            client.post('http://' + assignment_nodes[index]['ip'] + ':9100/work',
                        json={'text': piece, 'rounds': rounds, 'job': index})
            for index, piece in assignments])
    dispatch_ms = round((time.perf_counter() - dispatch_started) * 1000, 2)
    results = [response.json() for response in responses]
    assembly_started = time.perf_counter()
    words = sum(item.get('words', 0) for item in results)
    chars = sum(item.get('chars', 0) for item in results)
    sum_len = sum(item.get('sum_len', 0) for item in results)
    digest = combined_digest(results)
    assembly_ms = round((time.perf_counter() - assembly_started) * 1000, 3)
    return {'mode': mode, 'chunks': len(assignments), 'nodes_used': len({node['id'] for node in assignment_nodes}),
            'ms_total': round((time.perf_counter() - started) * 1000, 2), 'ms_dispatch': dispatch_ms,
            'ms_assembly': assembly_ms, 'words': words, 'chars': chars, 'sum_len': sum_len, 'digest': digest}


NODE_CACHE = {'at': 0.0, 'rows': []}


def live_nodes():
    now = time.time()
    if NODE_CACHE['rows'] and now - NODE_CACHE['at'] < 5:
        return NODE_CACHE['rows']
    if NODE_PLANE:
        try:
            with httpx.Client(timeout=3, trust_env=False) as client:
                data = client.get(NODE_PLANE + '/topology').json()
            from_plane = [{'id': node['id'], 'ip': node['ip']} for node in data.get('nodes', [])
                          if node.get('status') == 'live' and node.get('ip')]
            if from_plane:
                NODE_CACHE.update(at=now, rows=from_plane)
                return from_plane
        except (httpx.HTTPError, ValueError):
            pass
    with store.connect() as conn:
        return [{'id': row['node_id'], 'ip': row['ip']} for row in conn.execute(
            'SELECT node_id, ip FROM sim_heartbeats WHERE last_seen>? AND ip IS NOT NULL', (time.time() - 30,))]


def chunk_text(text, chunks):
    """Split on whitespace boundaries so every piece is a valid text fragment."""
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
        pieces.append(text[start:boundary])
        start = boundary + 1
    pieces.append(text[start:])
    return [piece for piece in pieces if piece]


def combined_digest(results):
    digest = hashlib.sha256()
    for item in results:
        digest.update(str(item.get('digest', '')).encode())
    return digest.hexdigest()


@app.get('/api/sim/stats')
def stats():
    if NODE_PLANE:
        try:
            with httpx.Client(timeout=3, trust_env=False) as client:
                plane = client.get(NODE_PLANE + '/stats').json()
            try:
                with store.connect() as conn:
                    served = conn.execute(
                        "SELECT COUNT(*) AS c FROM audit WHERE action='inference_submission'").fetchone()['c']
            except Exception:
                served = 0
            return {**plane, 'inference_served': served, 'events': len(EVENTS)}
        except (httpx.HTTPError, ValueError):
            pass
    now = time.time()
    with store.connect() as conn:
        conn.execute('DELETE FROM sim_heartbeats WHERE last_seen < ?', (now - 300,))
        total = conn.execute('SELECT COUNT(*) AS c FROM sim_heartbeats').fetchone()['c']
        live = conn.execute('SELECT COUNT(*) AS c FROM sim_heartbeats WHERE last_seen>?',
                            (now - 10,)).fetchone()['c']
        beats = conn.execute('SELECT COALESCE(SUM(beats),0) AS b FROM sim_heartbeats').fetchone()['b']
        served = conn.execute("SELECT COUNT(*) AS c FROM audit WHERE action='inference_submission'").fetchone()['c']
    return {'nodes_total': total, 'nodes_live': live, 'heartbeats': beats,
            'inference_served': served, 'events': len(EVENTS)}
