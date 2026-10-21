# Token policy — implementation specification

Target file: `versions/python/control/app.py` (control plane).
Status: **specified and proven in simulation, not merged.** `sim/simulate.py` runs these rules against the
real control plane with a mock backend and passes 14/14 checks. Merging into `app.py` is blocked by the
workspace artifact scanner (see the note at the end of this document). The write was blocked because the target
file already contains a Pydantic field whose name matches a credential keyword, and a curl example inside
`README.md` contains an auth header. Both are false positives; the change below adds no secrets.

## 1. Goal

Make a key usable by one team or one workload, within a hard monthly budget, without giving it the whole
model catalog. Today a key carries `max_requests` only: a caller can burn 1,000 requests of 4,096 tokens each
and stay "within budget". Dev teams need cost-shaped limits, not request-count limits.

## 2. Schema

New columns on `tokens` (defaults keep old keys valid):

| Column | Type | Default | Meaning |
|---|---|---|---|
| `max_tokens` | INTEGER | `0` | Model-token budget per UTC calendar month. `0` = unlimited. |
| `period_start` | REAL | `0` | Unix time of the last rollover; compared against the start of the current UTC month. |
| `models` | TEXT | `'[]'` | JSON array; empty = every globally approved model, otherwise a per-key catalog. |

```sql
CREATE TABLE IF NOT EXISTS tokens(
  id INTEGER PRIMARY KEY, hash TEXT UNIQUE, owner INTEGER REFERENCES users(id),
  name TEXT, scopes TEXT, expires REAL, max_requests INTEGER, used INTEGER DEFAULT 0,
  inference_tokens INTEGER DEFAULT 0, revoked INTEGER DEFAULT 0,
  max_tokens INTEGER DEFAULT 0, period_start REAL DEFAULT 0, models TEXT DEFAULT '[]');
```

Migration for pilot databases, after the `executescript` block:

```python
columns = {row['name'] for row in conn.execute('PRAGMA table_info(tokens)')}
for column, ddl in (('max_tokens', 'INTEGER DEFAULT 0'),
                    ('period_start', 'REAL DEFAULT 0'),
                    ('models', "TEXT DEFAULT '[]'")):
    if column not in columns:
        conn.execute(f'ALTER TABLE tokens ADD COLUMN {column} {ddl}')
```

## 3. Period rollover

```python
def month_start(ts=None):
    moment = time.gmtime(ts or time.time())
    return calendar.timegm((moment.tm_year, moment.tm_mon, 1, 0, 0, 0, 0, 0, 0))
```

Inside `create_app`, next to `audit()`:

```python
def roll_period(conn, row):
    token = dict(row)
    if (token.get('period_start') or 0) < month_start():
        now = time.time()
        conn.execute('UPDATE tokens SET used=0,inference_tokens=0,period_start=? WHERE id=?', (now, token['id']))
        token.update(used=0, inference_tokens=0, period_start=now)
    return token
```

Call it in `actor()` immediately after the bearer row is loaded, so every authenticated request sees a
rolled record:

```python
if row is not None:
    row = roll_period(conn, row)
```

Why UTC and not local midnight: the database stores Unix time, the deployment timezone is not recorded per
node, and a UTC boundary is what every OpenAI-compatible billing dashboard already uses. Document it.

## 4. Atomic budget consumption

Replace the current `UPDATE tokens SET used=used+1 ...` with one statement that enforces both budgets:

```sql
UPDATE tokens SET used=used+1
WHERE id=? AND revoked=0 AND expires>?
  AND used<max_requests
  AND (max_tokens=0 OR inference_tokens<max_tokens)
```

On `rowcount == 0`, read the row once and return a specific 429 message: `Token expired or revoked`,
`Request budget exhausted for this key`, or `Token budget exhausted for this period`. Callers need to know
which budget to raise; a single generic message generates support tickets.

**Overshoot is accepted and documented.** The budget is checked against *already reported* usage, so the
request that crosses the line is allowed and may exceed the budget by its own size. Exact enforcement would
require reserving tokens before generation, which no OpenAI-compatible upstream supports. Say this in the
README instead of implying hard caps.

## 5. Per-key model catalog

- `TokenInput.models: list[str] = Field(default_factory=list, max_length=20)`.
- On mint: reject any model not in the global approved list (`422 Requested model is not in the approved catalog`).
- On completion: `key_models = json.loads(token['models'] or '[]')`; if non-empty and `data.model` not in it,
  return `422 Model not permitted for this key`.

This is what lets a "specific workload" key be pinned to the cheap model while a research key gets the larger one.

## 6. Request surface

`Completion` gains `temperature` (0–2, default 0.7), `top_p` (0–1 exclusive, default 1.0) and `stop`
(max 4 strings). Without these, the current `extra='forbid'` model rejects the payloads the OpenAI SDK sends
by default, which is the most common first integration failure.

`stream: true` returns `text/event-stream` and relays upstream bytes unchanged, with
`Cache-Control: no-store` and `X-Accel-Buffering: no`. Usage is read from the last 8 KiB of the relayed
stream via `re.findall(r'"total_tokens"\s*:\s*(\d{1,9})', tail)` and added to `inference_tokens` after the
stream ends. Upstream failures emit one `data: {"error":...}` frame plus `data: [DONE]` so SDKs terminate
cleanly instead of hanging.

The streaming generator must open its own `db()` context; the request-scoped connection is closed before the
response body is consumed.

## 7. UI (`static/index.html`, `static/app.js`)

- Token form: add `max_tokens` (number, `0` = unlimited, label "Model token budget / month") and `models`
  (text, comma separated, label "Allowed models · blank = all approved").
- Token list line: `used/max_requests requests · inference_tokens/max_tokens tokens · models`.
- Send both fields in the create payload; both are optional so the existing form still works.

Keep all script in `app.js`: the CSP is `script-src 'self'` and forbids inline handlers.

## 8. Acceptance tests (`tests/test_control.py`)

| Test | Expected |
|---|---|
| Mint key with `max_tokens=5`, upstream reports `total_tokens=7` | first call `200`, second `429 Token budget exhausted` |
| Mint key with `models=['test-model']`, call with another approved model | `422 Model not permitted for this key` |
| Mint key with `models=['unapproved']` | `422` on mint |
| Age the key into an older month with counters already spent, then authenticate | counters reset to zero and a fresh period begins |
| `stream: true` against a fake SSE upstream | `200`, `content-type: text/event-stream`, body ends `[DONE]`, `inference_tokens` incremented by reported usage |
| Payload with `temperature`, `top_p`, `stop` | accepted (previously `422`) |

## 9. Documentation deltas

`README.md` — "Developer API keys" row: add token budgets with monthly reset and per-key model catalog.
"Inference gateway" row: add SSE streaming. Replace the sentence listing streaming/per-token budgets/per-key
catalogs as not implemented; keep the honest residuals (no currency billing, overshoot possible, no per-zone
inference routing, usage depends on upstream reporting).

`THIRD_PARTY_NOTICES.md` — unchanged; no new dependency.

## 10. Rollout

1. Restart the control plane; the `ALTER TABLE` migration runs on first connection.
2. Existing keys keep working: `max_tokens=0` and `models='[]'` mean "unchanged behaviour".
3. Mint one pilot key per team with a token budget; watch `inference_tokens` for a week before setting the
   budget to what teams actually use.

## 11. Simulation evidence

`python sim/simulate.py` executes rules 3–7 of this document against the real control plane:

```
PASS  reported usage is booked against the key (1 request, 7 model tokens)
PASS  per-key catalog blocks another approved model
PASS  month boundary resets both budgets
PASS  token budget stops the key after it is spent
PASS  streaming relays SSE end to end
PASS  usage is read from the streamed final chunk
14/14 checks passed
```

See `sim/README.md` for the full check table and the honest limits of the simulation.
