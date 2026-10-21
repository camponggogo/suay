"""End-to-end simulation of the token policy on a virtual machine (no GPU, no Petals, no network).

Runs the real SUAY control plane (SQLite schema, scope checks, hash format) with the token-policy
middleware in front of a mock OpenAI-compatible backend, then measures every rule in
docs/TOKEN_BUDGET_SPEC.md.

    python sim/simulate.py
"""
import json
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from fastapi.testclient import TestClient

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'versions' / 'python'))
sys.path.insert(0, str(HERE))

from control.app import create_app  # noqa: E402  (real control plane)
from mock_upstream import app as mock_app  # noqa: E402
import token_policy as policy  # noqa: E402

APPROVED = ['tiny-test', 'big-test']
RESULTS = []


def check(name, condition, detail=''):
    RESULTS.append((name, bool(condition), detail))
    print(('PASS  ' if condition else 'FAIL  ') + name + (('  · ' + detail) if detail else ''))


def free_port():
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def start_upstream(port):
    server = uvicorn.Server(uvicorn.Config(mock_app, host='127.0.0.1', port=port, log_level='error'))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            if httpx.get(f'http://127.0.0.1:{port}/healthz', timeout=1).status_code == 200:
                return server
        except httpx.HTTPError:
            time.sleep(0.15)
    raise RuntimeError('mock upstream did not start')


def bearer(raw):
    return {policy.AUTH_HEADER: 'Bearer ' + raw}


def main():
    port = free_port()
    server = start_upstream(port)
    workdir = Path(tempfile.mkdtemp(prefix='suay-sim-'))
    db = workdir / 'sim.sqlite3'

    app = create_app(db, upstream='', models=APPROVED)
    store = policy.TokenStore(db)
    store.migrate()
    app.add_middleware(policy.TokenPolicyMiddleware, store=store,
                       upstream=f'http://127.0.0.1:{port}/v1/chat/completions',
                       approved_models=APPROVED)
    client = TestClient(app, headers={'X-SUAY-Request': '1'})
    owner = store.owner()

    print('SUAY token-policy simulation')
    print(f'  database : {db}')
    print(f'  upstream : http://127.0.0.1:{port}/v1/chat/completions (mock)')
    print(f'  approved : {", ".join(APPROVED)}')
    print('')

    team_a = store.mint(owner, 'team-a', ['inference'], max_requests=10, max_tokens=20, models=['tiny-test'])
    body = {'model': 'tiny-test', 'messages': [{'role': 'user', 'content': 'hello sim'}]}

    response = client.post('/v1/chat/completions', json=body, headers=bearer(team_a.raw))
    check('1. approved model returns 200 and a completion',
          response.status_code == 200 and response.json()['choices'][0]['message']['content'].startswith('simulated'),
          f'status={response.status_code}')
    row = store.snapshot(team_a.id)
    check('2. reported usage is booked against the key', row['inference_tokens'] == 7 and row['used'] == 1,
          f"used={row['used']} inference_tokens={row['inference_tokens']}")

    response = client.post('/v1/chat/completions',
                           json={'model': 'big-test', 'messages': [{'role': 'user', 'content': 'x'}]},
                           headers=bearer(team_a.raw))
    check('3. per-key catalog blocks another approved model',
          response.status_code == 422 and 'not permitted' in response.json()['detail'],
          f"status={response.status_code} detail={response.json().get('detail')}")

    response = client.post('/v1/chat/completions',
                           json={'model': 'unlisted', 'messages': [{'role': 'user', 'content': 'x'}]},
                           headers=bearer(team_a.raw))
    check('4. globally unapproved model is rejected', response.status_code == 422,
          f"detail={response.json().get('detail')}")

    store.force_period(team_a.id, used=10, inference_tokens=99)
    response = client.post('/v1/chat/completions', json=body, headers=bearer(team_a.raw))
    row = store.snapshot(team_a.id)
    check('5. month boundary resets both budgets',
          response.status_code == 200 and row['used'] == 1 and row['inference_tokens'] == 7,
          f"used={row['used']} inference_tokens={row['inference_tokens']}")

    team_small = store.mint(owner, 'team-small', ['inference'], max_requests=100, max_tokens=5, models=[])
    first = client.post('/v1/chat/completions', json=body, headers=bearer(team_small.raw))
    second = client.post('/v1/chat/completions', json=body, headers=bearer(team_small.raw))
    check('6. token budget stops the key after it is spent',
          first.status_code == 200 and second.status_code == 429 and 'Token budget' in second.json()['detail'],
          f'first={first.status_code} second={second.status_code} detail={second.json().get("detail")}')

    team_req = store.mint(owner, 'team-request', ['inference'], max_requests=1, max_tokens=0, models=[])
    first = client.post('/v1/chat/completions', json=body, headers=bearer(team_req.raw))
    second = client.post('/v1/chat/completions', json=body, headers=bearer(team_req.raw))
    check('7. request budget is enforced separately',
          first.status_code == 200 and second.status_code == 429 and 'Request budget' in second.json()['detail'],
          f'first={first.status_code} second={second.status_code}')

    team_stream = store.mint(owner, 'team-stream', ['inference'], max_requests=10, max_tokens=0, models=[])
    with client.stream('POST', '/v1/chat/completions',
                       json={**body, 'stream': True}, headers=bearer(team_stream.raw)) as streamed:
        content_type = streamed.headers.get('content-type', '')
        payload = b''.join(streamed.iter_bytes())
        check('8. streaming relays SSE end to end',
              streamed.status_code == 200 and 'text/event-stream' in content_type and payload.rstrip().endswith(b'[DONE]'),
              f'status={streamed.status_code} bytes={len(payload)}')
    row = store.snapshot(team_stream.id)
    check('9. usage is read from the streamed final chunk', row['inference_tokens'] == 3,
          f"inference_tokens={row['inference_tokens']}")

    check('10. missing credentials are rejected',
          client.post('/v1/chat/completions', json=body).status_code == 401)
    watcher = store.mint(owner, 'watcher', ['observe'], max_requests=10, models=[])
    check('11. a read-only key cannot call inference',
          client.post('/v1/chat/completions', json=body, headers=bearer(watcher.raw)).status_code == 403)

    expiring = store.mint(owner, 'expiring', ['inference'], max_requests=10, models=[])
    store.force_period(expiring.id, used=0, inference_tokens=0)
    with store.connect() as conn:
        conn.execute('UPDATE tokens SET expires=0 WHERE id=?', (expiring.id,))
    check('12. expired key is rejected',
          client.post('/v1/chat/completions', json=body, headers=bearer(expiring.raw)).status_code == 401)

    revocable = store.mint(owner, 'revocable', ['inference'], max_requests=10, models=[])
    with store.connect() as conn:
        conn.execute('UPDATE tokens SET revoked=1 WHERE id=?', (revocable.id,))
    check('13. revoked key is rejected',
          client.post('/v1/chat/completions', json=body, headers=bearer(revocable.raw)).status_code == 401)

    check('14. control-plane routes still serve normally', client.get('/logo.svg').status_code == 200)

    print('')
    print('ledger')
    print(f"{'key':<14}{'requests':>10}{'tokens':>9}{'token budget':>15}{'models':>18}")
    for minted, name in ((team_a, 'team-a'), (team_small, 'team-small'), (team_req, 'team-request'),
                         (team_stream, 'team-stream'), (watcher, 'watcher')):
        row = store.snapshot(minted.id)
        budget = row['max_tokens'] or 'unlimited'
        catalog = ','.join(json.loads(row['models'])) or 'all approved'
        print(f"{name:<14}{str(row['used']) + '/' + str(row['max_requests']):>10}"
              f"{row['inference_tokens']:>9}{str(budget):>15}{catalog:>18}")

    server.should_exit = True
    failed = [name for name, ok, _ in RESULTS if not ok]
    print('')
    print(f'{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
