# Watto Roadmap

## Phase status

| Phase | What | Status |
|---|---|---|
| 1 | Local web app + CLI + tests | ✅ shipped (this repo) |
| 1.5 | Sell local app as digital download | playbook in `SELLING_LOCAL_APP.md` |
| 2 | Hosted SaaS (auth, Stripe tiers, command center) | playbook in `HOSTED_WEB_APP.md` |
| 3 | iPhone | below |
| 4 | Video & heavyweight inputs | below |

## Phase 3 — iPhone

**Step 1 (nearly free): PWA.** The hosted web app + a manifest and icons =
installable from Safari ("Add to Home Screen"), camera capture already works
via `<input type="file" accept="image/*" capture>`. Phone-sized CSS is
already the design. This covers 90% of the value: pawn-shop clerk photographs
the item with the phone *in the app*.

**Step 2 (when PWA isn't enough): Capacitor wrapper.** Wrap the same web app
in Capacitor for a real App Store listing (~$99/yr Apple dev account).
Native-feel camera, push notifications ("your appraisal is ready"). Only do
this for the marketing value of the App Store listing; the code stays shared.

Native Swift is not on the roadmap — nothing in the product needs it.

## Phase 4 — video & heavyweight appraisals (higher tiers only)

- **Video:** don't send video to a model. Client-side, sample 1 frame/sec →
  dedupe near-identical frames → send ≤10 stills through the normal pipeline.
  That's a walkthrough-video real-estate appraisal at photo prices. Gate to
  Pro/Enterprise.
- **Real estate mode:** triage already categorizes `real_estate`; add a
  category-specific research prompt (recent sales by address radius via web
  search) and a disclaimer ("not a certified appraisal — use for triage").
- **Batch mode (CLI already supports it):** enterprise feature — CSV/folder
  in, appraisal JSONs out. This is the wedge for pawn/estate-sale chains.

## Differentiators to keep sharpening (the moat)

1. **Bounded interrogation** — asks only value-moving questions, max 2
   rounds, everything skippable. (Chatbots either don't ask or never stop.)
2. **Evidence-anchored** — every number cites sold comps and spot prices
   pulled live; report shows them.
3. **Fake-detection posture** — red flags are a first-class output, tuned per
   category (plated gold, resealed cards, replica bags).
4. **Same process every time** — the state machine, not model vibes.
5. Possible later: per-category expert prompt packs (watches, coins, cards)
   sold as add-ons; confidence-calibration by tracking user-reported actual
   sale prices against predictions.

## Known ceilings (deliberate, revisit on evidence)

- Sessions are in-memory locally (restart loses an in-flight appraisal).
- IP+UA fingerprint for anonymous gating is spoofable — acceptable while free
  runs use `:free` models that cost ~nothing.
- PDF support depends on the chosen model's file parsing.
- No accuracy benchmark yet: before marketing "reliable", run 20 known-value
  items through and publish the hit rate. This is the single highest-value
  next task.
