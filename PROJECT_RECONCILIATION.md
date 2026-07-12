# Watto — Project Reconciliation

## Status: Testing (Ready for Owner Verification)

**Date:** 2026-07-11  
**Reconciled by:** Execution heartbeat  
**Classification:** Verified local MVP, not yet live-key validated

---

## What This Is

Watto is a zero-dependency local AI appraisal application. It identifies items from photos,
asks only value-moving follow-up questions, researches live market prices via OpenRouter's
`:online` web search, and produces defensible price ranges with red flags and resale advice.

**Target users:** Pawn shops, resellers, estate buyers, collectors, anyone needing quick
defensible appraisal ranges.

**Architecture:** Deterministic state machine (`engine.py`) with swappable LLM components,
stdlib-only HTTP server, vanilla JS UI in a single HTML file, zero-pip-install simplicity.

---

## Verification Evidence

### Tests (fresh)
```
cd /Users/jbs/Documents/code/watto
python3 test_watto.py
ok  test_extract_json
ok  test_full_flow
ok  test_json_retry
ok  test_no_questions_short_circuit
ok  test_report_survives_garbage_input
ok  test_research_failure_degrades_gracefully
all tests passed
```

### Launchers
| Launcher | Status | Notes |
|----------|--------|-------|
| `run.command` | ✅ Syntax OK | Double-click Terminal launcher, pauses on error |
| `run.sh` | ✅ Syntax OK | Linux/Unix launcher |
| `run.ps1` | ✅ Syntax OK | Windows PowerShell launcher |
| `Watto.app` | ✅ App bundle | macOS app directory with icon |
| `Watto.bat` | ✅ Batch file | Windows double-click launcher |

### Web App Smoke
- Server started on isolated port 8199
- `/api/health` → `{"app": "watto", "ok": true}`
- Static HTML renders with green theme, settings modal, quit flow
- Server binds 127.0.0.1 only (no network exposure)

### Git Status
Uncommitted changes present (repo-root changes, new launcher files). Tests and verification
run from current working tree; no skeleton state.

---

## Release Blockers / Next Tasks

### P0 — Live OpenRouter Key End-to-End
1. Add a live OpenRouter API key in Settings
2. Run a real appraisal on a known-item with photos
3. Verify the full pipeline: identify → questions → research → appraisal → PDF report

**Command:**  
- Start: `python3 server.py --open` (double-click `Watto.app` on macOS)
- UI: Settings gear → paste key → Save
- Action: Drop photo + description → "Appraise it"

### P1 — 20-Item Known-Value Accuracy Benchmark
Per `dev/ROADMAP.md`: "before marketing 'reliable', run 20 known-value items through and
publish the hit rate." This is required before any reliability claims.

**Process:**
1. Gather 20 items with known sale values (eBay completed listings, recent purchases)
2. Run each through Watto with live key
3. Record predicted range vs actual value
4. Publish hit-rate statistics on product page

### P2 — First Sales Channel Decision
Per `dev/SELLING_LOCAL_APP.md`, options are:
- **Gumroad** (10% flat, $0/mo) — recommended start point
- **Lemon Squeezy** (5% + $0.50, license keys included)
- **Shopify** ($29/mo + 2.9%) — for multi-product catalog

**Launch price:** $49 one-time (customers pay their own OpenRouter costs, ~$0.02-0.10/appraisal)

---

## Business Position

**Product type:** Local-first BYOK (Bring Your Own Key) AI app  
**Monetization:** One-time digital download  
**Hosting cost:** $0 (customer pays OpenRouter directly)  
**Support liability:** Minimal (email support, 14-day refund, troubleshooting guide)

This is a sellable product candidate with the smallest remaining step being live-key
verification before benchmark packaging.

---

## Manual User Actions Needed

1. Provide or obtain a live OpenRouter API key for E2E testing
2. Gather 20 known-value items/photos/results for accuracy benchmark
3. Choose sales channel: Gumroad, Lemon Squeezy, or Shopify/Launch Stack

---

## Files Changed This Reconciliation

| File | Change |
|------|--------|
| `PROJECT_RECONCILIATION.md` | Created (this file) |
| `watto/test_watto.py` | Verified all 6 tests pass |
| `watto/server.py` | Smoke-tested on isolated port |

---

## Recommendation

**Portfolio status:** `testing` / `next`  
**Next heartbeat directive:** Process real owner inputs; if still 0, verify live-key E2E
and begin 20-item benchmark planning. Do not add features; focus on release-readiness
evidence.