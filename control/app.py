"""SUAY organization control-plane pilot. No remote shell or worker execution."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from contextlib import contextmanager
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).parent
ROLES = {'admin', 'view_only', 'zone_display', 'agent_monitor', 'command_line'}
SCOPES = {'observe', 'command', 'inference'}


class Payload(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Login(Payload):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class Password(Payload):
    current_password: str = Field(max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class UserInput(Payload):
    username: str = Field(pattern=r'^[a-zA-Z0-9_.-]{1,64}$')
    password: str = Field(min_length=12, max_length=256)
    role: str
    zones: list[str] = Field(default_factory=list, max_length=100)
    nodes: list[str] = Field(default_factory=list, max_length=100)


class Grants(Payload):
    role: str
    zones: list[str] = Field(default_factory=list, max_length=100)
    nodes: list[str] = Field(default_factory=list, max_length=100)
    active: bool = True


class Reset(Payload):
    password: str = Field(min_length=12, max_length=256)


class TokenInput(Payload):
    name: str = Field(min_length=1, max_length=80)
    scopes: list[str] = Field(min_length=1, max_length=3)
    expires_days: int = Field(default=30, ge=1, le=365)
    max_requests: int = Field(default=1000, ge=1, le=1000000)


class NodeInput(Payload):
    id: str = Field(pattern=r'^[a-zA-Z0-9_.-]{1,64}$')
    zone: str = Field(pattern=r'^[a-zA-Z0-9_.-]{1,64}$')


class Command(Payload):
    action: str
    model: str | None = None


class Message(Payload):
    role: str = Field(pattern=r'^(system|user|assistant)$')
    content: str = Field(min_length=1, max_length=16000)


class Completion(Payload):
    model: str = Field(max_length=200)
    messages: list[Message] = Field(min_length=1, max_length=32)
    max_tokens: int = Field(default=128, ge=1, le=4096)
    stream: bool = False


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(value):
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', value.encode(), salt.encode(), 600000).hex()
    return salt + ':' + key


def password_matches(value, stored):
    salt, expected = stored.split(':')
    actual = hashlib.pbkdf2_hmac('sha256', value.encode(), salt.encode(), 600000).hex()
    return hmac.compare_digest(expected, actual)


def create_app(db_path=None, upstream=None, models=None):
    path = Path(db_path or os.getenv('SUAY_DB', str(ROOT / 'data' / 'suay.sqlite3')))
    path.parent.mkdir(parents=True, exist_ok=True)
    allowed_models = models or [m.strip() for m in os.getenv('SUAY_MODELS', 'bigscience/bloom-560m').split(',') if m.strip()]
    backend = upstream if upstream is not None else os.getenv('SUAY_INFERENCE_URL', '')
    if backend:
        url = urlparse(backend)
        if url.scheme not in {'https', 'http'} or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError('Invalid configured inference URL')
        if url.scheme == 'http' and url.hostname not in {'localhost', '127.0.0.1', '::1'}:
            raise ValueError('Non-loopback inference upstream must use HTTPS')
    secure_cookie = os.getenv('SUAY_COOKIE_SECURE', '0') == '1'

    @contextmanager
    def db():
        conn = sqlite3.connect(path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    with db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
          password TEXT NOT NULL, role TEXT NOT NULL, zones TEXT NOT NULL, nodes TEXT NOT NULL,
          must_change INTEGER NOT NULL DEFAULT 1, active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(id), expires REAL);
        CREATE TABLE IF NOT EXISTS tokens(id INTEGER PRIMARY KEY, hash TEXT UNIQUE, owner INTEGER REFERENCES users(id),
          name TEXT, scopes TEXT, expires REAL, max_requests INTEGER, used INTEGER DEFAULT 0,
          inference_tokens INTEGER DEFAULT 0, revoked INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS nodes(id TEXT PRIMARY KEY, zone TEXT, desired TEXT DEFAULT '{}', revision INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, at REAL, actor TEXT, action TEXT, target TEXT);
        CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY, failures INTEGER, until REAL);
        ''')
        if not conn.execute('SELECT 1 FROM users LIMIT 1').fetchone():
            conn.execute('INSERT INTO users(username,password,role,zones,nodes) VALUES(?,?,?,?,?)',
                         ('admin', password_hash(os.getenv('SUAY_BOOTSTRAP_PASSWORD', 'suay1234')), 'admin', '[]', '[]'))

    app = FastAPI(title='SUAY organization API', docs_url=None, redoc_url=None, openapi_url=None)

    def audit(conn, user, action, target=''):
        conn.execute('INSERT INTO audit(at,actor,action,target) VALUES(?,?,?,?)',
                     (time.time(), user['username'], action, str(target)))

    def allowed_scopes(user):
        if user['role'] == 'admin':
            return SCOPES
        return {'observe', 'inference', 'command'} if user['role'] == 'command_line' else {'observe'}

    def actor(request, scope=None, admin=False, changing=False):
        bearer = request.headers.get('authorization', '')
        token = None
        with db() as conn:
            if bearer.startswith('Bearer '):
                token = conn.execute('SELECT * FROM tokens WHERE hash=? AND revoked=0 AND expires>?',
                                     (digest(bearer[7:]), time.time())).fetchone()
                user = conn.execute('SELECT * FROM users WHERE id=?', (token['owner'],)).fetchone() if token else None
            else:
                session = conn.execute('SELECT * FROM sessions WHERE hash=? AND expires>?',
                                       (digest(request.cookies.get('suay_session', '')), time.time())).fetchone()
                user = conn.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone() if session else None
        if not user or not user['active']:
            raise HTTPException(401, 'Authentication required')
        if user['must_change'] and not changing:
            raise HTTPException(403, 'Password change required')
        if admin and (user['role'] != 'admin' or token):
            raise HTTPException(403, 'Admin browser session required')
        if scope and (scope not in allowed_scopes(user) or (token and scope not in json.loads(token['scopes']))):
            raise HTTPException(403, 'Scope denied')
        return dict(user), dict(token) if token else None

    def visible(user, node):
        if user['role'] == 'admin':
            return True
        zones, nodes = json.loads(user['zones']), json.loads(user['nodes'])
        if user['role'] == 'agent_monitor':
            return node['id'] in nodes
        return '*' in zones or node['zone'] in zones or node['id'] in nodes

    @app.middleware('http')
    async def boundaries(request, call_next):
        # Custom header cannot be sent by a cross-origin HTML form; CORS is not enabled.
        if request.method not in {'GET', 'HEAD'}:
            if request.headers.get('x-suay-request') != '1':
                return JSONResponse({'detail': 'X-SUAY-Request: 1 required'}, status_code=403)
            origin = request.headers.get('origin')
            if origin and origin != str(request.base_url).rstrip('/'):
                return JSONResponse({'detail': 'Cross-origin request denied'}, status_code=403)
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 65536:
                    return JSONResponse({'detail': 'Request too large'}, status_code=413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    @app.get('/')
    def dashboard():
        return FileResponse(ROOT / 'static' / 'index.html')

    @app.get('/app.js')
    def js():
        return FileResponse(ROOT / 'static' / 'app.js', media_type='text/javascript')

    @app.get('/style.css')
    def css():
        return FileResponse(ROOT / 'static' / 'style.css', media_type='text/css')

    @app.get('/logo.svg')
    def logo():
        return FileResponse(ROOT / 'static' / 'suay-network.svg', media_type='image/svg+xml')

    @app.post('/api/login')
    def login(data: Login, request: Request, response: Response):
        # Client IP is the direct peer; do not trust arbitrary forwarded headers.
        key = digest((request.client.host if request.client else '') + ':' + data.username.lower())
        with db() as conn:
            attempt = conn.execute('SELECT * FROM attempts WHERE key=?', (key,)).fetchone()
            if attempt and attempt['failures'] >= 5 and attempt['until'] > time.time():
                raise HTTPException(429, 'Too many attempts; wait 15 minutes')
            user = conn.execute('SELECT * FROM users WHERE username=?', (data.username,)).fetchone()
            valid = password_matches(data.password, user['password'] if user else dummy_hash)
            if not user or not valid or not user['active']:
                failures = attempt['failures'] + 1 if attempt and attempt['until'] > time.time() else 1
                conn.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?)', (key, failures, time.time()+900))
                conn.commit()
                raise HTTPException(401, 'Invalid credentials')
            conn.execute('DELETE FROM attempts WHERE key=?', (key,))
            session = secrets.token_urlsafe(32)
            conn.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
            conn.execute('INSERT INTO sessions VALUES(?,?,?)', (digest(session), user['id'], time.time()+28800))
            audit(conn, user, 'login')
        response.set_cookie('suay_session', session, httponly=True, secure=secure_cookie, samesite='strict', max_age=28800)
        return {'must_change': bool(user['must_change'])}

    dummy_hash = password_hash(secrets.token_urlsafe(32))

    @app.post('/api/logout')
    def logout(request: Request, response: Response):
        with db() as conn:
            conn.execute('DELETE FROM sessions WHERE hash=?', (digest(request.cookies.get('suay_session', '')),))
        response.delete_cookie('suay_session')
        return {'ok': True}

    @app.post('/api/password')
    def password(data: Password, request: Request, response: Response):
        user, token = actor(request, changing=True)
        if token or not password_matches(data.current_password, user['password']):
            raise HTTPException(403, 'Current password required')
        if data.new_password == data.current_password or data.new_password == 'suay1234':
            raise HTTPException(422, 'Choose a different password')
        with db() as conn:
            conn.execute('UPDATE users SET password=?,must_change=0 WHERE id=?', (password_hash(data.new_password), user['id']))
            conn.execute('DELETE FROM sessions WHERE user_id=?', (user['id'],))
            conn.execute('UPDATE tokens SET revoked=1 WHERE owner=?', (user['id'],))
            audit(conn, user, 'password_changed')
        response.delete_cookie('suay_session')
        return {'ok': True, 'login_required': True}

    @app.get('/api/me')
    def me(request: Request):
        user, _ = actor(request, changing=True)
        return {k: user[k] for k in ('id', 'username', 'role', 'zones', 'nodes', 'must_change')}

    @app.get('/api/users')
    def users(request: Request):
        actor(request, admin=True)
        with db() as conn:
            return [dict(r) for r in conn.execute('SELECT id,username,role,zones,nodes,active,must_change FROM users')]

    @app.post('/api/users')
    def add_user(data: UserInput, request: Request):
        user, _ = actor(request, admin=True)
        if data.role not in ROLES:
            raise HTTPException(422, 'Unknown role')
        try:
            with db() as conn:
                conn.execute('INSERT INTO users(username,password,role,zones,nodes) VALUES(?,?,?,?,?)',
                             (data.username, password_hash(data.password), data.role, json.dumps(data.zones), json.dumps(data.nodes)))
                audit(conn, user, 'user_created', data.username)
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'Username already exists')
        return {'ok': True}

    @app.put('/api/users/{uid}')
    def set_grants(uid: int, data: Grants, request: Request):
        user, _ = actor(request, admin=True)
        if uid == user['id']:
            raise HTTPException(409, 'Cannot disable or change your own grants')
        if data.role not in ROLES:
            raise HTTPException(422, 'Unknown role')
        with db() as conn:
            if not conn.execute('SELECT 1 FROM users WHERE id=?', (uid,)).fetchone():
                raise HTTPException(404, 'User not found')
            conn.execute('UPDATE users SET role=?,zones=?,nodes=?,active=? WHERE id=?',
                         (data.role, json.dumps(data.zones), json.dumps(data.nodes), data.active, uid))
            conn.execute('DELETE FROM sessions WHERE user_id=?', (uid,))
            conn.execute('UPDATE tokens SET revoked=1 WHERE owner=?', (uid,))
            audit(conn, user, 'grants_changed', uid)
        return {'ok': True}

    @app.post('/api/users/{uid}/reset-password')
    def reset_password(uid: int, data: Reset, request: Request):
        user, _ = actor(request, admin=True)
        if uid == user['id']:
            raise HTTPException(409, 'Use change password for your own account')
        with db() as conn:
            if not conn.execute('SELECT 1 FROM users WHERE id=?', (uid,)).fetchone():
                raise HTTPException(404, 'User not found')
            conn.execute('UPDATE users SET password=?,must_change=1 WHERE id=?', (password_hash(data.password), uid))
            conn.execute('DELETE FROM sessions WHERE user_id=?', (uid,))
            conn.execute('UPDATE tokens SET revoked=1 WHERE owner=?', (uid,))
            audit(conn, user, 'password_reset', uid)
        return {'ok': True}

    @app.post('/api/tokens')
    def mint_token(data: TokenInput, request: Request):
        user, token = actor(request)
        if token or user['role'] not in {'admin', 'command_line'}:
            raise HTTPException(403, 'Developer or admin browser session required')
        if not set(data.scopes) <= allowed_scopes(user):
            raise HTTPException(422, 'Invalid scopes')
        raw = 'suay_' + secrets.token_urlsafe(32)
        with db() as conn:
            cur = conn.execute('INSERT INTO tokens(hash,owner,name,scopes,expires,max_requests) VALUES(?,?,?,?,?,?)',
                               (digest(raw), user['id'], data.name, json.dumps(data.scopes), time.time()+data.expires_days*86400, data.max_requests))
            audit(conn, user, 'token_created', cur.lastrowid)
        return {'token': raw, 'id': cur.lastrowid, 'notice': 'Shown once. Quota counts accepted inference submissions, not model tokens.'}

    @app.get('/api/tokens')
    def tokens(request: Request):
        user, token = actor(request)
        if token:
            raise HTTPException(403, 'Browser session required')
        with db() as conn:
            fields = 'id,owner,name,scopes,expires,max_requests,used,inference_tokens,revoked'
            rows = conn.execute(f'SELECT {fields} FROM tokens' + ('' if user['role'] == 'admin' else ' WHERE owner=?'),
                                () if user['role'] == 'admin' else (user['id'],))
            return [dict(r) for r in rows]

    @app.delete('/api/tokens/{tid}')
    def revoke(tid: int, request: Request):
        user, token = actor(request)
        if token:
            raise HTTPException(403, 'Browser session required')
        with db() as conn:
            row = conn.execute('SELECT owner FROM tokens WHERE id=?', (tid,)).fetchone()
            if not row or (user['role'] != 'admin' and row['owner'] != user['id']):
                raise HTTPException(404, 'Token not found')
            conn.execute('UPDATE tokens SET revoked=1 WHERE id=?', (tid,))
            audit(conn, user, 'token_revoked', tid)
        return {'ok': True}

    @app.get('/api/nodes')
    def nodes(request: Request):
        user, _ = actor(request, 'observe')
        with db() as conn:
            return [dict(r, observed='not_connected', applied=False) for r in conn.execute('SELECT * FROM nodes') if visible(user, r)]

    @app.post('/api/nodes')
    def add_node(data: NodeInput, request: Request):
        user, _ = actor(request, admin=True)
        try:
            with db() as conn:
                conn.execute('INSERT INTO nodes(id,zone) VALUES(?,?)', (data.id, data.zone))
                audit(conn, user, 'node_registered', data.id)
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'Node already registered')
        return {'ok': True, 'observed': 'not_connected'}

    @app.post('/api/nodes/{nid}/command')
    def command(nid: str, data: Command, request: Request):
        user, _ = actor(request, 'command')
        if data.action not in {'run', 'stop', 'drain'} or (data.action == 'run' and data.model not in allowed_models) or (data.action != 'run' and data.model is not None):
            raise HTTPException(422, 'Only run with an approved model, stop, or drain is permitted')
        with db() as conn:
            row = conn.execute('SELECT * FROM nodes WHERE id=?', (nid,)).fetchone()
            if not row or not visible(user, row):
                raise HTTPException(404, 'Node not found')
            conn.execute('UPDATE nodes SET desired=?,revision=revision+1 WHERE id=?', (data.model_dump_json(), nid))
            audit(conn, user, 'desired_' + data.action, nid)
        return {'status': 'pending', 'applied': False, 'detail': 'Desired state stored. Worker transport is not implemented.'}

    @app.get('/api/models')
    def models_api(request: Request):
        actor(request)
        return allowed_models

    @app.get('/api/audit')
    def audit_api(request: Request):
        actor(request, admin=True)
        with db() as conn:
            return [dict(r) for r in conn.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100')]

    @app.post('/v1/chat/completions')
    async def completions(data: Completion, request: Request):
        user, token = actor(request, 'inference')
        if not token:
            raise HTTPException(403, 'Use a scoped API token')
        if data.model not in allowed_models or data.stream:
            raise HTTPException(422, 'Model not approved or streaming requested; only non-streaming supported')
        if not backend:
            raise HTTPException(503, 'Configure an approved inference upstream first')
        # Atomic quota check prevents concurrent requests exceeding a key budget.
        with db() as conn:
            cur = conn.execute('UPDATE tokens SET used=used+1 WHERE id=? AND revoked=0 AND expires>? AND used<max_requests',
                               (token['id'], time.time()))
            if not cur.rowcount:
                raise HTTPException(429, 'Token expired, revoked or request budget exhausted')
            audit(conn, user, 'inference_submission', token['id'])
        headers = {}
        if os.getenv('SUAY_UPSTREAM_KEY'):
            headers['Authorization'] = 'Bearer ' + os.environ['SUAY_UPSTREAM_KEY']
        try:
            async with httpx.AsyncClient(timeout=120, follow_redirects=False, trust_env=False) as client:
                result = await client.post(backend, json=data.model_dump(), headers=headers)
            if result.status_code != 200:
                raise HTTPException(502, 'Inference upstream failed; submission counted against request budget')
            payload = result.json()
            usage = payload.get('usage', {}).get('total_tokens', 0)
            if isinstance(usage, int) and not isinstance(usage, bool) and usage >= 0:
                with db() as conn:
                    conn.execute('UPDATE tokens SET inference_tokens=inference_tokens+? WHERE id=?', (usage, token['id']))
            return payload
        except (httpx.HTTPError, ValueError, AttributeError):
            raise HTTPException(502, 'Inference upstream unavailable or invalid; submission counted against request budget')

    return app
