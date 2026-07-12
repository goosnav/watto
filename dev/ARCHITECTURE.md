# Watto Architecture

## The one idea that matters

Watto is **not** a chatbot wrapper. It is a deterministic state machine where
LLMs are swappable components. Code decides what happens next; models only
fill well-defined slots and must return strict JSON (validated, one retry,
graceful degradation). This is what makes results *consistent* — the same
ring photographed twice goes through the same stages, gets the same category
of questions, and is anchored to the same kind of market data.

## Pipeline

```
INTAKE  photos/PDFs + free-text description
   │
TRIAGE  light vision model → {identification, category, confidence,
   │                          needs_research, questions[≤4]}
   │        • questions are the *only* facts that materially move value
   │        • empty list ⇒ skip GATHER entirely (e.g. common Pokémon card)
   ▼
GATHER  user answers / attaches detail photos; every question skippable
   │        • skipped fact ⇒ recorded as "(user does not know / skipped)"
   │        • re-triage after answers; hard cap 2 rounds (no infinite loops)
   ▼
RESEARCH  research model + OpenRouter ':online' web plugin
   │        → {comps[] (sold listings preferred), spot_prices, market_notes}
   │        • failure is non-fatal: pipeline continues, confidence capped
   ▼
APPRAISE  strongest model, sees EVERYTHING (photos + facts + research)
   │        → {low, high, most_likely, currency, confidence, summary,
   │           reasoning, red_flags, what_would_narrow_range, resale_channels}
   ▼
REPORT  rendered by web UI / CLI / (future) hosted API — same JSON everywhere
```

Guard rails encoded in `engine.py`:
- `MAX_ROUNDS = 2`, ≤4 questions per round — the "asks follow-ups" behavior
  is bounded, so a session always terminates.
- Malformed model output → one "JSON only" retry → clean `EngineError`. No
  stack traces reach users.
- Research errors are swallowed into the report ("research failed, confidence
  capped") rather than aborting.
- Result JSON is schema-defaulted (`setdefault`) so clients never see missing keys.

## Components & tech stack

| Layer | Choice | Why |
|---|---|---|
| Engine | `engine.py`, pure Python stdlib | one file holds prompts + state machine; imported by every front end, including the future hosted API route (port to TS or run as-is on a Python host) |
| Reports | `report.py`, hand-rolled minimal PDF writer | professional PDF (header band, value box, embedded photos, comps, reasoning, terms) with zero dependencies; every field optional so bad model output can't break it |
| Persistence | `~/Watto Appraisals/<date>-<item>-<id>/` | photos + `appraisal.json` + `report.pdf` per finished appraisal; saving failures never kill an appraisal (`save_error` surfaces in UI) |
| Model gateway | OpenRouter (OpenAI-compatible API) | one key/bill, every lab's models, `:free` variants for a free tier, `:online` suffix = built-in web search (no separate search API to integrate) |
| Local server | stdlib `ThreadingHTTPServer`, `127.0.0.1` only | zero pip installs ⇒ the paid download can't break on customer machines |
| UI | one `static/index.html`, vanilla JS | Google-simple was the requirement; no build step, works from a file server |
| CLI | `cli.py` | automation outlet; `--auto --json` for pipelines |
| Storage (local) | `~/.watto/settings.json` chmod 600; sessions in memory | single-user tool |

## Model roles (the "specialist AI" design)

- **Triage** (cheap, fast, vision): identification + question selection. Runs
  1–3× per appraisal. Wrong-but-cheap here is fine — appraise re-sees raw photos.
- **Research** (cheap + `:online`): market data gathering. Text-only input.
- **Appraise** (expensive, smart): the only stage where quality is paramount;
  it gets full context and is prompted to be blunt about fakes.

Cost shape: ~80% of tokens flow through cheap models; the expensive model
runs exactly once per appraisal.

## Startup robustness

- Port 8177 busy? The server walks 8177–8196 and takes the first free port.
- Already-running Watto detected via `/api/health` → second launch just opens
  the browser to the existing instance (double-clicking twice is safe).
- All startup failures print a human sentence (no tracebacks) and pause the
  terminal window so double-click users can read it.
- Launchers: `Watto.app` (macOS bundle w/ icon, background, Settings→Quit),
  `Watto.bat` (Windows), `run.command`/`run.sh` (terminal). Each checks for
  Python and shows a plain-language dialog/message if missing.

## Security posture (local app)

- Server binds `127.0.0.1` — unreachable from the network.
- API key: never rendered back to the browser (only `has_key` + last-4 hint),
  file is `0600`, key goes only to `openrouter.ai` over HTTPS.
- Uploads capped at 40 MB; all model output HTML-escaped before rendering
  (comps URLs/titles come from the open web — injection surface).
- No telemetry, no third-party calls other than OpenRouter.

## Assumptions made autonomously (flag if wrong)

1. OpenRouter-only for phase 1 (vs. direct per-lab keys) — simplest thing that
   supports "multiple models + free models + web search".
2. Default slugs `google/gemini-2.5-flash` / `anthropic/claude-sonnet-4.5`;
   slugs rot, so they're settings, not constants.
3. PDFs are passed through to OpenRouter's file input (works on models with
   file parsing; not all free models support it).
4. Video is out of scope for phase 1 (see ROADMAP — frame sampling design).
5. No login/accounts locally — that's a hosted-version concern.

## Where phase 2 plugs in

The hosted version (see `HOSTED_WEB_APP.md`) reuses this pipeline behind an
API route that adds: auth (Supabase), quota check (Postgres counter), *your*
OpenRouter key from server env, and per-tier model selection. `engine.py`'s
prompts and stage logic are the product; everything around them is plumbing.
