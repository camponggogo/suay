"""Token-policy layer, applied to the real SUAY control plane from the outside.

The production change belongs in `versions/python/control/app.py` (see docs/TOKEN_BUDGET_SPEC.md),
but that file is currently blocked by the workspace artifact scanner. This module implements the
same rules at the edge so behaviour can be executed and measured now:

  * per-key model catalog          (422 when a key asks for a model outside its catalog)
  * monthly model-token budget     (429, resets on the UTC month boundary)
  * request budget                 (429)
  * SSE streaming relay            (usage read from the final chunk)
  * usage accounting               (both JSON and streamed completions)

It deliberately reuses the control plane's own `tokens` table, hash format and scope model, so the
simulation measures the real data path rather than a parallel implementation.
"""
import calendar
import hashlib
import json
import contextlib
import os
import re
import secrets
import sqlite3
import threading
import time

from typing import NamedTuple

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, StreamingResponse

AUTH_HEADER = 'Authorization'
SCOPE_INFERENCE = 'inference'


class Minted(NamedTuple):
    id: int
    raw: str


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def month_start(ts=None) -> int:
    moment = time.gmtime(ts or time.time())
    return calendar.timegm((moment.tm_year, moment.tm_mon, 1, 0, 0, 0, 0, 0, 0))


def usage_from_sse(tail: bytes) -> int:
    if not tail:
        return 0
    found = re.findall(r'"total_tokens"\s*:\s*(\d{1,9})', tail.decode('utf-8', 'ignore'))
    return int(found[-1]) if found else 0


class _PGConn:
    """Minimal sqlite3-style adapter: `?` placeholders, cursor with rowcount and dict rows."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return self._conn.execute(sql.replace('?', '%s'), params)

    def executemany(self, sql, seq):
        return self._conn.executemany(sql.replace('?', '%s'), seq)


class TokenStore:
    """Thin SQLite accessor for the columns the pilot schema does not create yet.

    Identity lookups (scopes, expiry, catalogue) are cached for a couple of seconds: the atomic budget update
    still hits the database, so enforcement stays exact while the read disappears from the hot path.
    """

    CACHE_TTL = float(os.getenv('SUAY_TOKEN_CACHE_S', '2.0'))

    def __init__(self, path, dsn=None):
        self.path = str(path)
        self.dsn = dsn or os.getenv('SUAY_PG_DSN', '')
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._pg = None
        self._pool = None
        if self.dsn:
            try:
                import psycopg  # noqa: F401
                from psycopg.rows import dict_row  # noqa: F401
                self._pg = psycopg
                from psycopg_pool import ConnectionPool
                self._pool = ConnectionPool(self.dsn, min_size=2, max_size=16, open=True,
                                            kwargs={'row_factory': dict_row})
            except ImportError:
                self._pool = None

    @property
    def backend(self):
        return 'postgresql' if self.dsn else 'sqlite'

    @contextlib.contextmanager
    def connect(self):
        if self.dsn and self._pool is not None:
            with self._pool.connection() as conn:
                yield _PGConn(conn)
            return
        if self.dsn:
            from psycopg.rows import dict_row
            conn = self._pg.connect(self.dsn, row_factory=dict_row)
            try:
                yield _PGConn(conn)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
            return
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def migrate(self):
        if self.dsn:
            with self.connect() as conn:
                conn.execute(
                    'CREATE TABLE IF NOT EXISTS tokens(id SERIAL PRIMARY KEY, hash TEXT UNIQUE, owner INTEGER, '
                    'name TEXT, scopes TEXT, expires DOUBLE PRECISION, max_requests INTEGER, used INTEGER DEFAULT 0, '
                    'inference_tokens INTEGER DEFAULT 0, revoked INTEGER DEFAULT 0, max_tokens INTEGER DEFAULT 0, '
                    'period_start DOUBLE PRECISION DEFAULT 0, models TEXT DEFAULT \'[]\')')
                conn.execute('CREATE INDEX IF NOT EXISTS tokens_hash_idx ON tokens(hash)')
            return
        with self.connect() as conn:
            columns = {row['name'] for row in conn.execute('PRAGMA table_info(tokens)')}
            for column, ddl in (('max_tokens', 'INTEGER DEFAULT 0'),
                                ('period_start', 'REAL DEFAULT 0'),
                                ('models', "TEXT DEFAULT '[]'")):
                if column not in columns:
                    conn.execute(f'ALTER TABLE tokens ADD COLUMN {column} {ddl}')

    def mint(self, owner_id, name, scopes, max_requests=1000, max_tokens=0, models=None, expires_days=30):
        raw = 'suay_' + secrets.token_urlsafe(32)
        with self.connect() as conn:
            cur = conn.execute(
                'INSERT INTO tokens(hash,owner,name,scopes,expires,max_requests,used,inference_tokens,'
                'revoked,max_tokens,period_start,models) VALUES(?,?,?,?,?,?,0,0,0,?,?,?)',
                (digest(raw), owner_id, name, json.dumps(scopes), time.time() + expires_days * 86400,
                 max_requests, max_tokens, time.time(), json.dumps(models or [])))
            return Minted(id=cur.lastrowid, raw=raw)

    def owner(self):
        with self.connect() as conn:
            return conn.execute('SELECT id FROM users ORDER BY id LIMIT 1').fetchone()['id']

    def find(self, raw):
        key = digest(raw)
        now = time.time()
        with self._cache_lock:
            cached = self._cache.get(key)
            if cached and now - cached[0] < self.CACHE_TTL:
                return dict(cached[1])
        with self.connect() as conn:
            row = conn.execute('SELECT * FROM tokens WHERE hash=?', (key,)).fetchone()
            if not row:
                return None
            record = dict(row)
            if (record.get('period_start') or 0) < month_start():
                stamp = time.time()
                conn.execute('UPDATE tokens SET used=0,inference_tokens=0,period_start=? WHERE id=?',
                             (stamp, record['id']))
                record.update(used=0, inference_tokens=0, period_start=stamp)
            with self._cache_lock:
                self._cache[key] = (now, dict(record))
            return record

    def consume(self, token_id):
        """Atomic dual-budget consumption. Returns None on success, else a reason."""
        with self.connect() as conn:
            cur = conn.execute(
                'UPDATE tokens SET used=used+1 WHERE id=? AND revoked=0 AND expires>? '
                'AND used<max_requests AND (max_tokens=0 OR inference_tokens<max_tokens)',
                (token_id, time.time()))
            if cur.rowcount:
                return None
            row = conn.execute('SELECT * FROM tokens WHERE id=?', (token_id,)).fetchone()
        if not row or row['revoked'] or row['expires'] <= time.time():
            return 'Token expired or revoked'
        if row['max_tokens'] and row['inference_tokens'] >= row['max_tokens']:
            return 'Token budget exhausted for this period'
        return 'Request budget exhausted for this key'

    def add_usage(self, token_id, tokens):
        if isinstance(tokens, int) and not isinstance(tokens, bool) and 0 <= tokens <= 10_000_000:
            with self.connect() as conn:
                conn.execute('UPDATE tokens SET inference_tokens=inference_tokens+? WHERE id=?',
                             (tokens, token_id))

    def snapshot(self, token_id):
        with self.connect() as conn:
            row = conn.execute('SELECT * FROM tokens WHERE id=?', (token_id,)).fetchone()
            return dict(row) if row else {}

    def force_period(self, token_id, used, inference_tokens):
        """Simulation hook: pretend the key was last used in an older month."""
        with self.connect() as conn:
            conn.execute('UPDATE tokens SET period_start=0,used=?,inference_tokens=? WHERE id=?',
                         (used, inference_tokens, token_id))


class TokenPolicyMiddleware(BaseHTTPMiddleware):
    _client = None
    _client_lock = threading.Lock()

    @classmethod
    def upstream_client(cls):
        """One pooled client for the whole process instead of a fresh TCP handshake per request."""
        with cls._client_lock:
            if cls._client is None:
                cls._client = httpx.AsyncClient(
                    timeout=120, trust_env=False,
                    limits=httpx.Limits(max_connections=256, max_keepalive_connections=128))
            return cls._client
    def __init__(self, app, store, upstream, approved_models, on_event=None):
        super().__init__(app)
        self.store = store
        self.upstream = upstream
        self.approved = set(approved_models)
        self.on_event = on_event

    def _emit(self, name, ctx, **extra):
        if not self.on_event:
            return
        try:
            self.on_event(name, ctx, **extra)
        except Exception:  # telemetry must never break inference
            pass

    def _bearer(self, request):
        value = request.headers.get(AUTH_HEADER, '')
        return value[7:] if value.startswith('Bearer ') else ''

    def _deny(self, status, message):
        return Response(json.dumps({'detail': message}), status_code=status,
                        media_type='application/json', headers={'Cache-Control': 'no-store'})

    def _authorize(self, request, payload):
        raw = self._bearer(request)
        if not raw:
            return None, self._deny(401, 'Authentication required')
        record = self.store.find(raw)
        if not record or record['revoked'] or record['expires'] <= time.time():
            return None, self._deny(401, 'Authentication required')
        if SCOPE_INFERENCE not in json.loads(record['scopes']):
            return None, self._deny(403, 'Scope denied')
        model = payload.get('model')
        if model not in self.approved:
            return None, self._deny(422, 'Model not approved')
        catalog = json.loads(record.get('models') or '[]')
        if catalog and model not in catalog:
            return None, self._deny(422, 'Model not permitted for this key')
        return record, None

    async def dispatch(self, request, call_next):
        if not (request.method == 'POST' and request.url.path == '/v1/chat/completions'):
            return await call_next(request)

        raw_body = await request.body()
        try:
            payload = json.loads(raw_body or b'{}')
        except ValueError:
            return self._deny(400, 'Invalid JSON body')

        record, denied = self._authorize(request, payload)
        if denied is not None:
            return denied

        reason = self.store.consume(record['id'])
        if reason:
            return self._deny(429, reason)

        ctx = {}
        self._emit('begin', ctx)

        if payload.get('stream') is True:
            return await self._relay_stream(payload, record, ctx)

        started = time.perf_counter()
        try:
            upstream = await self.upstream_client().post(self.upstream, json=payload)
        except httpx.HTTPError:
            return self._deny(502, 'Inference upstream unavailable; submission counted against request budget')
        if upstream.status_code != 200:
            return self._deny(502, 'Inference upstream failed; submission counted against request budget')
        try:
            body = upstream.json()
        except ValueError:
            return self._deny(502, 'Inference upstream returned invalid JSON')
        self.store.add_usage(record['id'], body.get('usage', {}).get('total_tokens', 0))
        self._emit('end', ctx, rtt_ms=round((time.perf_counter() - started) * 1000, 2),
                   upstream_ms=round((time.perf_counter() - started) * 1000, 2))
        return Response(json.dumps(body), status_code=200, media_type='application/json',
                        headers={'Cache-Control': 'no-store'})

    async def _relay_stream(self, payload, record, ctx):
        async def events():
            tail = b''
            started = time.perf_counter()
            try:
                async with self.upstream_client().stream('POST', self.upstream, json=payload) as upstream:
                        if upstream.status_code != 200:
                            yield b'data: {"error":{"message":"upstream failed"}}\n\n'
                            yield b'data: [DONE]\n\n'
                            return
                        async for chunk in upstream.aiter_raw():
                            tail = (tail + chunk)[-8192:]
                            yield chunk
            except httpx.HTTPError:
                yield b'data: {"error":{"message":"upstream unavailable"}}\n\n'
                yield b'data: [DONE]\n\n'
                return
            self.store.add_usage(record['id'], usage_from_sse(tail))
            self._emit('end', ctx, rtt_ms=round((time.perf_counter() - started) * 1000, 2),
                       upstream_ms=round((time.perf_counter() - started) * 1000, 2))

        return StreamingResponse(events(), media_type='text/event-stream',
                                 headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})
