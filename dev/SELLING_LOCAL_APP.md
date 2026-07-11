# Selling the Local App (the zip-on-Shopify play)

You're right that this is the easy one. The local app is finished software:
zero dependencies, bring-your-own-key, nothing for you to host or support at
3am. Sell it as a digital download.

## Packaging

```bash
# from the repo root — ship exactly what's tested
zip -r Watto-v1.0.zip README.md TUTORIAL.md run.command run.sh run.ps1 \
    server.py engine.py cli.py static/ test_watto.py
```

Rules: version the filename; `TUTORIAL.md` is the onboarding (customers get
their own OpenRouter key — make that crystal clear on the product page so
nobody expects AI usage to be included); bump a `VERSION` line in README per
release.

## Storefront options (pick one)

| Option | Cut | Verdict |
|---|---|---|
| **Shopify Basic + Digital Downloads app** | $29/mo + 2.9% | Your instinct. Fine if you'll sell other things too; overkill for one zip. |
| **Gumroad** | 10% flat, $0/mo | Zero setup, handles EU VAT for you. **Start here** — switch to Shopify when volume makes 10% > $29+fees. |
| **Lemon Squeezy** | 5% + 50¢, $0/mo | Merchant-of-record (handles global sales tax), built-in **license keys**. Best if you want key-gating from day one. |

All three deliver the zip automatically after payment. You already have
Shopify MCP tooling wired up in this environment, so standing up the Shopify
version is a one-session job when you choose it.

## Pricing

- **$49 one-time** launch price ($79 list, "launch discount"). One-time beats
  subscription here: customers pay AI costs themselves, so your marginal cost
  is $0 and support is the only liability.
- Position against reality: one good pawn-shop catch pays for it. "Buy it
  once, appraise forever, pennies per item in AI costs you control."
- Optional later: "Watto Pro Updates" $19/yr for new versions (only once you
  actually ship updates).

## Licensing (keep it honest, not fortified)

v1: **no license enforcement.** It's Python source; determined people copy
it regardless, and DRM punishes paying customers. A `LICENSE.txt` stating
"one purchase = one business location, no redistribution" filters honest
customers, which is most of them.

If copying visibly hurts sales later: Lemon Squeezy license keys + a 10-line
startup check in `server.py` (validate key against their API once, cache
offline for 30 days). Add it then, not now.

## Support & updates

- Support = one email address (support@ on your domain, forwards to Gmail).
  The TUTORIAL's troubleshooting table should absorb 90% of tickets.
- Updates: re-upload zip, email past buyers (all three platforms can).
- Refunds: 14-day no-questions. Digital-goods disputes are unwinnable;
  refund fast, keep ratings clean.

## Product page skeleton

1. Hero: the app screenshot + "AI appraisals for pawn shops, resellers, and
   estate buyers. Your computer, your API key, no subscription."
2. 60-second demo video (screen recording of the gold-ring flow).
3. "How it's different from ChatGPT": asks the right follow-ups, checks live
   sold prices, flags fakes, same process every time.
4. Requirements box: macOS/Windows/Linux, Python 3.9+, OpenRouter account
   (~$0.05/appraisal, paid to OpenRouter not us).
5. FAQ + refund policy.
