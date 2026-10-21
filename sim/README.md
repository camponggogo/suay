# SUAY simulation — token policy on a virtual machine

Runs the **real control plane** (`versions/python/control/app.py`: SQLite schema, token hashing, scope
model) with the token-policy layer in front of a **mock OpenAI-compatible backend**. No GPU, no Petals,
no internet, no writes to the production files.

```sh
python sim/simulate.py
```

Expected tail:

```
14/14 checks passed
```

## What it proves

| Rule | Check |
|---|---|
| Approved model returns a completion | 1 |
| Reported `usage.total_tokens` is booked against the key | 2 |
| A key with a model catalog cannot use another (even approved) model | 3 |
| A globally unapproved model is rejected | 4 |
| The UTC month boundary resets request **and** token counters | 5 |
| The token budget stops a key once spent (`429 Token budget exhausted`) | 6 |
| The request budget is enforced independently (`429 Request budget exhausted`) | 7 |
| `stream: true` relays SSE end to end and ends with `[DONE]` | 8 |
| Usage is recovered from the streamed final chunk | 9 |
| Missing credentials → `401` | 10 |
| A read-only (`observe`) key cannot call inference → `403` | 11 |
| Expired key → `401` | 12 |
| Revoked key → `401` | 13 |
| The control plane still serves its own routes | 14 |

The ledger printed at the end shows the per-key state after the run (requests, tokens, budgets, catalog).

## Files

| File | Role |
|---|---|
| `mock_upstream.py` | OpenAI-compatible backend; JSON and SSE modes, deterministic `usage` |
| `token_policy.py` | The policy under test: per-key catalog, dual budget, monthly rollover, SSE relay, usage accounting |
| `simulate.py` | Boots both, mints keys, runs the 14 checks, prints the ledger |

## Honest limits

- This is an **edge simulation**, not the merged product. The same rules still need to move into
  `versions/python/control/app.py` (see `docs/TOKEN_BUDGET_SPEC.md`); that file is currently blocked by the
  workspace artifact scanner.
- The mock backend always reports 7 tokens per request (3 when streaming), so the numbers verify the
  accounting path, not a model's real tokenisation.
- Budgets are checked against already-reported usage: the request that crosses the limit is allowed and may
  overshoot by its own size. That matches the spec and is deliberate.
- No dashboard rendering is exercised here; the control plane's own test suite covers UI-adjacent APIs.
