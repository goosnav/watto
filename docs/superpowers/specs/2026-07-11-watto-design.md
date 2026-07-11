# Watto — Design Spec (2026-07-11)

Generalist AI appraiser. A deterministic pipeline that uses LLMs as components —
not a chatbot wrapper. Asks only the follow-up questions that materially change
value, researches live market prices, and returns a defensible price range.

## Phased delivery

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Local web app (double-click launcher, bring-your-own OpenRouter key, settings UI, multi-model) | **built now** |
| 1b | CLI harness for developers/automation | **built now** |
| 1c | `dev/` docs: architecture, hosted-SaaS tutorial (Vercel+Supabase+Stripe), local-app sales guide, roadmap | **built now** |
| 2 | Hosted web app: Google/email login, Stripe tiers, free-run gating, admin "command center" | documented in `dev/HOSTED_WEB_APP.md`, not built |
| 3 | iPhone app (PWA → wrapper) | documented in `dev/ROADMAP.md` |

## Can it be pure client-side JS? (user asked)

No — not for the paid product. A browser-only app must embed the API key in
client code, where anyone can extract it and drain your account. Two viable
shapes instead:

1. **Local app (phase 1):** tiny Python server on `127.0.0.1`; the user's own
   key lives on their disk, never leaves their machine except to OpenRouter.
   Zero dependencies (stdlib only) so "double-click and it runs".
2. **Hosted app (phase 2):** *your* key lives only in server-side environment
   variables; browser talks to your API routes, which check auth + quota
   before proxying to the model. This is the only safe shape for a
   subscription product.

## The state machine (the differentiator)

Code owns the transitions; models only fill slots. Every model reply is strict
JSON, validated with one retry, and every stage degrades gracefully.

```
INTAKE ──► TRIAGE ──► (questions?) ──► GATHER ──► TRIAGE (re-check, max 2 rounds)
                │ no                      ▲  │
                ▼                         └──┘ (photos or typed answers, all skippable)
            RESEARCH (web search: comps, spot gold/silver, market notes)
                ▼
            APPRAISE (strong model, full context + images) ──► REPORT
```

- **TRIAGE** (light/cheap model, vision): identifies the item, picks a category,
  and returns *only* the questions whose answers materially change value.
  A Pokémon card gets set/number/condition questions, never weight. Jewelry
  gets weight/hallmark questions. Empty question list ⇒ skip GATHER entirely.
- **GATHER**: every question is skippable ("no scale? skip it") — a skipped
  fact widens the range instead of breaking the flow. Questions may request a
  detail photo (`type: "photo"`). Hard cap: 2 rounds, ≤4 questions per round.
- **RESEARCH**: model slug gets `:online` (OpenRouter web plugin) — pulls
  current comps (eBay/sold listings), spot metal prices when relevant. On
  failure the pipeline continues and the final confidence drops.
- **APPRAISE** (strong model): sees photos + facts + research, returns
  `{low, high, most_likely, confidence, reasoning, red_flags,
  what_would_narrow_range, resale_channels}`. Red flags cover authenticity
  (fake gold, counterfeit cards, glass "gems").

## Model allocation (user-configurable in Settings)

| Role | Default | Why |
|---|---|---|
| triage | `google/gemini-2.5-flash` | cheap, fast, good vision |
| research | `google/gemini-2.5-flash` + `:online` | web plugin does the searching |
| appraise | `anthropic/claude-sonnet-4.5` | the answer that matters |

One provider (OpenRouter) = one key, hundreds of models including `:free`
variants for the phase-2 free tier.

## Components

| File | Purpose |
|---|---|
| `engine.py` | state machine + OpenRouter client + prompts. No HTTP-server code. Reused verbatim by web, CLI, and (later) hosted API. |
| `server.py` | stdlib `ThreadingHTTPServer` on `127.0.0.1:8177`; static page + 4 JSON endpoints |
| `cli.py` | interactive or `--auto` non-interactive appraisals, `--json` output |
| `static/index.html` | the whole UI, single file, no frameworks |
| `test_watto.py` | offline smoke test with a fake LLM |

## Key decisions & assumptions (made autonomously)

1. **OpenRouter-only for phase 1.** One key covers vision, web search, free
   models, and every major lab. Direct Anthropic/OpenAI key support deferred.
2. **Python stdlib only.** No pip install ⇒ the double-click launcher can't
   break on a customer machine. `urllib` is enough for one API.
3. **Sessions in memory.** Local single-user tool; restart = fresh start.
4. **Images downscaled client-side** to ≤1600px JPEG before upload (token cost).
5. **PDFs pass through** to OpenRouter's file input (works on models with the
   file parser; noted in tutorial).
6. **Video deferred** to phase 3 (frame-sampling design in ROADMAP).
7. **Launcher** = `run.command` (macOS double-click) / `run.sh` / `run.ps1`.

## Error handling

- No key ⇒ friendly settings prompt, never a stack trace.
- Model returns non-JSON ⇒ one retry with a "JSON only" nudge, then clean error.
- Research fails ⇒ appraisal proceeds, confidence capped, error shown in report.
- Oversized uploads rejected at 40 MB with a readable message.

## Testing

`python3 test_watto.py` — runs the full state machine against a scripted fake
LLM (no network, no key): triage→questions→answers→research→appraise, plus
JSON-extraction edge cases. Server smoke: `curl localhost:8177` after launch.
