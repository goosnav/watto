# Claude Run Summary — 2026-07-11

## What was built (phase 1 of the Watto plan)

A working local AI appraiser: deterministic state-machine pipeline
(triage → gather → research → appraise) with LLMs as swappable components,
a Google-simple web UI, a developer CLI, and the full documentation set for
the later phases (hosted SaaS, selling the download, iPhone).

## Files

- `engine.py` — state machine, prompts, OpenRouter client (stdlib only)
- `server.py` — local web server, 127.0.0.1:8177
- `static/index.html` — entire UI (settings modal, question rounds, report)
- `cli.py` — interactive / `--auto` / `--json` appraisals
- `test_watto.py` — offline pipeline tests (fake LLM)
- `run.command` / `run.sh` / `run.ps1` — double-click launchers (unix ones executable)
- `README.md`, `TUTORIAL.md`
- `dev/ARCHITECTURE.md`, `dev/HOSTED_WEB_APP.md` (Vercel+Supabase+Stripe
  playbook incl. command center, tiers, security checklist),
  `dev/SELLING_LOCAL_APP.md`, `dev/ROADMAP.md`
- `docs/superpowers/specs/2026-07-11-watto-design.md` — design spec

## Verification (fresh output this run)

- `python3 test_watto.py` → **all 5 tests passed** (full flow, question
  skipping, research-failure degradation, JSON extraction, JSON retry)
- `python3 server.py` → `GET /` 200, `GET /api/settings` correct, `POST
  /api/appraise` without key returns the friendly settings prompt (502)
- Browser inspection: home page and settings modal render correctly
  (fixed one bug found visually: dialog centering)
- `python3 cli.py --help` ok; no-key path exits 1 with readable error

## Known limitations

- End-to-end appraisal with a real OpenRouter key not exercised (no key
  available in this session) — first real run may surface model-slug rot;
  slugs are user-editable in Settings by design.
- Default model slugs current as of 2026-07; verify on openrouter.ai/models.
- Sessions in memory; PDF support depends on model file-parsing.

## Next task

Run one real appraisal with a live key, then the accuracy benchmark
(20 known-value items) flagged in `dev/ROADMAP.md` before any marketing
claims. Then phase 1.5: zip + storefront per `dev/SELLING_LOCAL_APP.md`.
