"""Consent-based first-party landing analytics. No coordinator integration."""
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .credentials import load, password_matches, save

TARGETS = {'github', 'star', 'issues', 'contribute', 'architecture', 'license', 'language', 'start', 'internal', 'clone', 'support'}
DEVICES = {'mobile', 'tablet', 'desktop'}
PAGES = {'en','th','hi','zh','ja','ko','ms','id','sw','es','fr','pt'}


class Payload(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Login(Payload):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class Password(Payload):
    current_password: str = Field(max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class Event(Payload):
    kind: str
    target: str = ''
    x: int = Field(default=0, ge=0, le=19)
    y: int = Field(default=0, ge=0, le=19)
    value: int = Field(default=0, ge=0, le=100)
    intent: str = ''


class Batch(Payload):
    consent: bool
    view: str = Field(pattern=r'^[a-zA-Z0-9-]{20,64}$')
    page: str
    device: str
    events: list[Event] = Field(min_length=1, max_length=30)


def create_app(state_dir=None, public_origin=None, secure=True):
    state = Path(state_dir or os.getenv('SUAY_VISITOR_STATE', '/var/lib/suay-visitor'))
    state.mkdir(parents=True, exist_ok=True)
    origin = public_origin or os.getenv('SUAY_VISITOR_ORIGIN', 'https://campong.online')
    private = state / 'private'
    load(private)  # Fail closed if credentials were not initialized.
    database = state / 'metrics.sqlite3'
    lock = threading.Lock()
    throttle = defaultdict(list)
    failures = {}
    memory_salt = secrets.token_bytes(32)

    @contextmanager
    def db():
        conn = sqlite3.connect(database, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    with db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS views(id TEXT PRIMARY KEY, day TEXT, page TEXT, device TEXT, depth INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS events(view_id TEXT REFERENCES views(id) ON DELETE CASCADE,
          kind TEXT,target TEXT,x INTEGER,y INTEGER,n INTEGER DEFAULT 1,
          PRIMARY KEY(view_id,kind,target,x,y));
        CREATE TABLE IF NOT EXISTS feedback(view_id TEXT PRIMARY KEY REFERENCES views(id) ON DELETE CASCADE,
          rating INTEGER,intent TEXT);
        CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY,expires REAL);
        CREATE INDEX IF NOT EXISTS view_filters ON views(day,page,device);
        ''')
    database.chmod(0o600)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    def peer_key(request):
        # The service is loopback-only; Nginx replaces this header and strips forwarded chains.
        peer = request.headers.get('x-real-ip') if request.client and request.client.host in {'127.0.0.1', '::1'} else None
        value = peer or (request.client.host if request.client else 'unknown')
        return hmac.new(memory_salt, value.encode(), hashlib.sha256).hexdigest()

    @app.middleware('http')
    async def boundaries(request, call_next):
        if request.method == 'POST':
            if request.headers.get('origin') != origin or request.headers.get('x-suay-metrics') != '1':
                return JSONResponse({'detail': 'Same-origin request required'}, status_code=403)
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 24576:
                    return JSONResponse({'detail': 'Payload too large'}, status_code=413)
            request._body = bytes(body)
            key = peer_key(request)
            now = time.monotonic()
            with lock:
                if len(throttle) > 10000:
                    for old in list(throttle):
                        if not throttle[old] or now - throttle[old][-1] > 60:
                            del throttle[old]
                throttle[key] = [t for t in throttle[key] if now-t < 60]
                if len(throttle[key]) >= 90:
                    return JSONResponse({'detail': 'Rate limit'}, status_code=429)
                throttle[key].append(now)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    def authorized(request, changing=False):
        secret = request.cookies.get('suay_visitor_session', '')
        with db() as conn:
            if not conn.execute('SELECT 1 FROM sessions WHERE hash=? AND expires>?',
                                (hashlib.sha256(secret.encode()).hexdigest(), time.time())).fetchone():
                raise HTTPException(401, 'Sign in required')
        if load(private)[2] and not changing:
            raise HTTPException(403, 'Change the initial password first')

    @app.get('/health')
    def health():
        return {'ok': True, 'service': 'landing-visitor-analytics'}

    @app.post('/login')
    def login(data: Login, request: Request, response: Response):
        key = peer_key(request)
        now = time.monotonic()
        with lock:
            count, until = failures.get(key, (0, 0))
        if count >= 5 and until > now:
            raise HTTPException(429, 'Wait 15 minutes before retrying')
        username, password, must_change = load(private)
        valid_password = password_matches(data.password, password)
        if not hmac.compare_digest(data.username.encode(), username.encode()) or not valid_password:
            with lock:
                failures[key] = ((count+1) if until > now else 1, now+900)
            raise HTTPException(401, 'Invalid credentials')
        with lock:
            failures.pop(key, None)
        raw = secrets.token_urlsafe(32)
        with db() as conn:
            conn.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
            conn.execute('INSERT INTO sessions VALUES(?,?)', (hashlib.sha256(raw.encode()).hexdigest(), time.time()+14400))
        response.set_cookie('suay_visitor_session', raw, httponly=True, secure=secure,
                            samesite='strict', path='/projects/suay/visitor-api/', max_age=14400)
        return {'must_change': must_change}

    @app.get('/me')
    def me(request: Request):
        authorized(request, changing=True)
        return {'must_change': load(private)[2]}

    @app.post('/password')
    def password(data: Password, request: Request, response: Response):
        authorized(request, changing=True)
        username, stored, _ = load(private)
        if not password_matches(data.current_password, stored):
            raise HTTPException(403, 'Current password required')
        if data.current_password == data.new_password:
            raise HTTPException(422, 'Choose a different password')
        with lock:
            save(private, username, data.new_password, must_change=False)
            with db() as conn:
                conn.execute('DELETE FROM sessions')
        response.delete_cookie('suay_visitor_session', path='/projects/suay/visitor-api/')
        return {'ok': True, 'login_required': True}

    @app.post('/logout')
    def logout(request: Request, response: Response):
        with db() as conn:
            conn.execute('DELETE FROM sessions WHERE hash=?', (hashlib.sha256(request.cookies.get('suay_visitor_session', '').encode()).hexdigest(),))
        response.delete_cookie('suay_visitor_session', path='/projects/suay/visitor-api/')
        return {'ok': True}

    @app.post('/events')
    def collect(data: Batch):
        if not data.consent or data.page not in PAGES or data.device not in DEVICES:
            raise HTTPException(422, 'Consent and valid landing dimensions required')
        for event in data.events:
            if event.kind not in {'view', 'link', 'scroll', 'click', 'move', 'feedback'}:
                raise HTTPException(422, 'Unknown event')
            if event.kind == 'link' and event.target not in TARGETS:
                raise HTTPException(422, 'Invalid link category')
            if event.kind == 'feedback' and (event.value not in range(1, 6) or event.intent not in {'try', 'contribute', 'read', 'unsure'}):
                raise HTTPException(422, 'Invalid assessment')
            if event.kind not in {'link', 'feedback'} and (event.target or event.intent):
                raise HTTPException(422, 'Unexpected event metadata')
        identifier = hashlib.sha256(data.view.encode()).hexdigest()
        day = datetime.now(timezone.utc).date().isoformat()
        cutoff = (datetime.now(timezone.utc).date()-timedelta(days=90)).isoformat()
        with db() as conn:
            conn.execute('DELETE FROM views WHERE day<?', (cutoff,))
            conn.execute('INSERT OR IGNORE INTO views(id,day,page,device) VALUES(?,?,?,?)', (identifier, day, data.page, data.device))
            view = conn.execute('SELECT page,device FROM views WHERE id=?', (identifier,)).fetchone()
            if view['page'] != data.page or view['device'] != data.device:
                raise HTTPException(409, 'Page-load identity mismatch')
            for event in data.events:
                if event.kind == 'view':
                    continue
                if event.kind == 'scroll':
                    conn.execute('UPDATE views SET depth=MAX(depth,?) WHERE id=?', (event.value//25*25, identifier))
                elif event.kind == 'feedback':
                    conn.execute('INSERT OR IGNORE INTO feedback VALUES(?,?,?)', (identifier, event.value, event.intent))
                else:
                    if event.kind in {'move', 'click'}:
                        total = conn.execute('SELECT COALESCE(SUM(n),0) FROM events WHERE view_id=? AND kind=?', (identifier, event.kind)).fetchone()[0]
                        if total >= (120 if event.kind == 'move' else 100):
                            continue
                    conn.execute('''INSERT INTO events(view_id,kind,target,x,y) VALUES(?,?,?,?,?)
                      ON CONFLICT(view_id,kind,target,x,y) DO UPDATE SET n=MIN(n+1,10000)''',
                                 (identifier, event.kind, event.target if event.kind == 'link' else '',
                                  event.x if event.kind in {'move','click'} else 0,
                                  event.y if event.kind in {'move','click'} else 0))
        return {'ok': True}

    @app.get('/report')
    def report(request: Request, days: int = 30, page: str = 'all', device: str = 'all'):
        authorized(request)
        if days not in {7, 30, 90} or page not in PAGES | {'all'} or device not in DEVICES | {'all'}:
            raise HTTPException(422, 'Invalid report filters')
        cutoff = (datetime.now(timezone.utc).date()-timedelta(days=days-1)).isoformat()
        query = 'v.day>=?'
        params = [cutoff]
        for field, value in [('page', page), ('device', device)]:
            if value != 'all':
                query += ' AND v.'+field+'=?'
                params.append(value)
        with db() as conn:
            views = conn.execute('SELECT COUNT(*) FROM views v WHERE '+query, params).fetchone()[0]
            daily = [dict(r) for r in conn.execute('SELECT v.day,COUNT(*) AS views FROM views v WHERE '+query+' GROUP BY v.day ORDER BY v.day', params)]
            links = [dict(r) for r in conn.execute('SELECT e.target,SUM(e.n) AS clicks,COUNT(DISTINCT e.view_id) AS engaged_views FROM events e JOIN views v ON v.id=e.view_id WHERE '+query+" AND e.kind='link' GROUP BY e.target ORDER BY clicks DESC", params)]
            for link in links:
                link['ctr'] = round(100*link['engaged_views']/views, 2) if views else 0
            scroll = {str(depth): conn.execute('SELECT COUNT(*) FROM views v WHERE '+query+' AND v.depth>=?', params+[depth]).fetchone()[0] for depth in [25,50,75,100]}
            heat = [dict(r) for r in conn.execute('SELECT e.kind,e.x,e.y,SUM(e.n) AS n FROM events e JOIN views v ON v.id=e.view_id WHERE '+query+" AND e.kind IN ('click','move') GROUP BY e.kind,e.x,e.y", params)]
            feedback = dict(conn.execute('SELECT COUNT(*) AS responses,AVG(f.rating) AS average FROM feedback f JOIN views v ON v.id=f.view_id WHERE '+query, params).fetchone())
            feedback['intents'] = [dict(r) for r in conn.execute('SELECT f.intent,COUNT(*) AS n FROM feedback f JOIN views v ON v.id=f.view_id WHERE '+query+' GROUP BY f.intent', params)]
        return dict(views=views, daily=daily, links=links, scroll=scroll, heat=heat, feedback=feedback,
                    scope='Opt-in page loads, not unique people. UTC day boundaries. Heatmap is a coarse relative document grid; filter page/device before comparing.')

    return app
