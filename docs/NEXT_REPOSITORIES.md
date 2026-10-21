# Next repositories — where a constrained budget actually hurts

Four candidates, ranked by (pain severity × willingness to pay × how much of SUAY can be reused).
Each one is a *separate repository*; SUAY stays the compute/control-plane project.

Scoring: 5 = severe, frequent, already budgeted somewhere.

| # | Repository | Enterprise pain | Reuse of SUAY | Build effort | Score |
|---|---|---|---|---|---|
| 1 | `suay-box` | Per-seat AI subscriptions vs. one existing GPU | Control plane, auth, token budgets, landing | 2–3 weeks | **23/25** |
| 2 | `ticket-to-kb` | L1 support headcount; knowledge trapped in closed tickets | Gateway + token policy | 3–4 weeks | 20/25 |
| 3 | `redact-ai` | Legal blocks cloud AI because of PII/PDPA | Gateway + audit | 3 weeks | 19/25 |
| 4 | `doc2quote` | Manual PO/invoice entry in SMEs | Gateway + token policy | 4 weeks | 16/25 |

## 1. `suay-box` — one GPU, one department, zero per-seat fees  ← recommended

**Pain.** A 40-person department is quoted per-seat pricing for an AI assistant; the same department already
owns a workstation with a 24 GB GPU that sits idle 80% of the day. Procurement cannot justify either the
subscription or new hardware.

**Product.** A single installable unit — "the box" — that turns one existing GPU machine into a private,
OpenAI-compatible AI endpoint for the department: RAG over the shared drive, per-team API keys with monthly
token budgets, audit log, and a readiness check that refuses to start if the model licence is not accepted.

**Why it wins.** It is the same control plane SUAY already implements (`versions/python/control`), pointed at
one local backend instead of a swarm. The demo is one command and one browser tab; the buyer is the department
head, not the CIO, so the sales cycle is a meeting rather than a quarter.

**MVP scope.** One model from an allowlist (7–8B, quantised), document folder ingestion with citations,
token budgets + audit (reuse), Windows/Linux installer, health page. **Out of scope:** multi-tenant SSO,
fine-tuning, agents.

**Licence.** MIT for code. Ship only Apache-2.0 weights by default; Llama models behind an explicit
acceptance gate.

**Risk.** Commodity competition from Ollama + Open WebUI. Differentiator is *governance* (budgets, audit,
zones), not raw inference — keep that front and centre.

## 2. `ticket-to-kb` — answer from your own closed tickets

**Pain.** L1 support re-answers the same 200 questions; the answers exist in a ticketing system nobody
searches. Hiring is frozen, so headcount is the constraint, not tooling.

**Product.** Ingests resolved tickets from one connector, builds a retrieval index, drafts replies with
citations to past tickets, and reports deflection rate. Human approves before send.

**Why now.** The value is measurable in a week (deflection %), which is what budget holders need to see.

**Risk.** Data access and PII. Ship redaction on ingest, not as an add-on.

## 3. `redact-ai` — the compliance gate before cloud AI

**Pain.** Legal will not approve sending documents to a cloud model because of PDPA/GDPR exposure.
The business uses it anyway, shadow-IT style.

**Product.** An on-prem proxy that detects and redacts PII/PHI, keeps a reversible mapping in the tenant's
own store, forwards the redacted text to any approved provider, and restores entities in the response.
Audit trail per document.

**Why it wins.** It converts a "no" into a "yes with controls" — the cheapest possible procurement outcome.

**Risk.** Detection quality is the product. Start with a narrow, high-precision entity set (Thai ID,
passport, phone, email, bank account) and publish precision/recall on a public test set.

## 4. `doc2quote` — purchase orders and invoices into structured rows

**Pain.** SMEs re-key supplier documents into accounting software. Errors cost real money and month-end
is a fire drill.

**Product.** Local OCR + extraction to a fixed schema, confidence per field, human review queue, CSV/API export.

**Risk.** Long tail of layouts; accuracy claims are easy to overstate. Only viable with a per-customer
template tune-up service.

## Recommendation

Build **`suay-box`** next. It reuses ~60% of the existing control plane, has the shortest path to a demo a
department head can approve on their own budget, and it makes the SUAY swarm an *upgrade path* rather than a
prerequisite: start with one box, add nodes when the pilot proves useful.

Suggested repository name and one-liner:

```
suay-box — One existing GPU. One private, audited, OpenAI-compatible AI endpoint for your department.
```

Keep `camponggogo/suay` as the umbrella project; link the two from both READMEs rather than merging them.
