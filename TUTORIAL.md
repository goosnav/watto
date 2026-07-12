# Watto Tutorial — from zero to your first appraisal

## 1. Setup (one time, ~3 minutes)

### Get your OpenRouter API key
Watto uses [OpenRouter](https://openrouter.ai), a single gateway to every
major AI model (Claude, Gemini, GPT, free models). One key, one bill.

1. Go to **openrouter.ai** → Sign up (Google login works).
2. Top-right menu → **Keys** → **Create Key**. Name it "Watto". Copy it
   (starts with `sk-or-`).
3. Menu → **Credits** → add **$5**. That's roughly 100–300 appraisals on the
   default models.

### Launch Watto
- **macOS:** double-click **`Watto.app`**. First time, macOS warns about an
  unidentified developer — right-click it → **Open** → **Open** (once). It
  runs quietly in the background; quit from Settings → Quit Watto.
- **Windows:** install Python from python.org (check "Add to PATH"), then
  double-click **`Watto.bat`**.
- **Linux:** `./run.sh`

Keep the launcher inside the Watto folder — it runs the code sitting next to
it. Launching twice is safe: Watto notices it's already running and just
reopens your browser, and it finds a free port by itself if 8177 is taken.

Your browser opens to Watto. Click the **gear icon** (top right), paste your
key, **Save**. Done forever — the key lives only in `~/.watto/settings.json`
on this machine.

## 2. Your first appraisal

Try the classic hard case — a maybe-gold ring:

1. Take 2–3 photos with your phone: the whole ring, the stone, and the
   inside of the band (any stamps). Email/AirDrop them to the computer, or
   run Watto on the same computer you sync photos to.
2. Drag the photos into the drop zone.
3. Describe it: *"gold ring with a red stone, bought in Russia in the 90s"*.
4. Click **Appraise it**.

Watto will identify it, then ask **only what matters** — typically:
- *How much does it weigh in grams?* (kitchen scale is fine — **or leave it
  blank**; Watto estimates from the photos and widens the range)
- *Photo of the stamp inside the band?* (Soviet gold is stamped 583/585 —
  this one stamp can double the answer)

Answer what you can, skip what you can't, hit **Continue**. In ~30–60
seconds you get:

- **Price range + most-likely price** (what a real buyer pays, not retail fantasy)
- **Confidence** (low/medium/high — honest about what's unverified)
- **Red flags** — e.g. *"stone is almost certainly synthetic; standard for
  Soviet rings"* or *"stamp looks etched, possibly fake"*
- **Market comps** — actual recent sold listings it found
- **What would narrow the range** — e.g. *"an acid test would confirm purity
  and tighten the range to ±10%"*
- **Where to sell** — melt buyer vs eBay vs specialist auction
- **A printable PDF report** — click *View / print report*. Every appraisal
  also lands in `~/Watto Appraisals/<date>-<item>/` with the photos,
  `appraisal.json` (the full record), and `report.pdf` — an official-looking
  document with the value range, market comps, red flags, and full reasoning,
  ready to hand to a customer or keep on file.

## 3. What else can it eat?

- **Trading cards:** photo of front + back. It will ask about edition/set
  symbols only if it can't read them, then check eBay sold prices.
- **Electronics/tools:** photo + model number. Asks "does it power on?".
- **Documents & real estate:** drop a **PDF** (listing sheet, old deed,
  inspection report) plus photos. For real estate it asks location and square
  footage, then pulls comparable sales. (Treat real-estate numbers as a
  starting point, not a certified appraisal.)
- **Anything weird:** taxidermy, vintage tools, grandma's china — the triage
  stage picks the right questions per category on its own.

**Tips for better numbers:** natural light, one item per appraisal, include
any markings/labels/serials, and mention how you got it ("estate sale",
"bought new in 2019") — provenance changes value.

## 4. Choosing models (Settings)

| You want | Triage | Research | Appraisal |
|---|---|---|---|
| Best quality (default) | `google/gemini-2.5-flash` | `google/gemini-2.5-flash` | `anthropic/claude-sonnet-4.5` |
| Cheapest that's still good | `google/gemini-2.5-flash` | `google/gemini-2.5-flash` | `google/gemini-2.5-flash` |
| Free (testing only) | `qwen/qwen2.5-vl-72b-instruct:free` | same | same |

Any slug from **openrouter.ai/models** works (slugs change over time — that
page is the source of truth). Vision support is required for triage and
appraisal. "Research live market prices" can be toggled off to halve cost;
confidence drops accordingly.

## 5. CLI for developers

```bash
# One-shot appraisal in a script, JSON out:
python3 cli.py "Rolex Datejust 36, 1985" -i watch.jpg --auto --json > result.json

# Feed known facts up front so nothing prompts:
python3 cli.py "gold ring" -i ring.jpg -i stamp.jpg \
  --fact weight_grams=12.4 --fact stamp="583 with star" --auto

# Interactive mode answers questions on stdin; a file path answer attaches a photo.
```

Exit code 0 = success; errors print to stderr and exit 1. The JSON schema is
the `public_view` structure in `engine.py` (stable: `result.low/high/
most_likely/confidence/red_flags/...`).

## 6. FAQ

- **Is this a certified appraisal?** No — it's a fast, evidence-based
  estimate. For insurance/legal purposes hire a certified appraiser (Watto's
  report is a great brief to hand them).
- **Where does my money go?** Only to OpenRouter, for the models you use.
  Watto itself has no server and phones home to no one.
- **Cost per appraisal?** Default models: roughly $0.02–0.10 depending on
  photo count and research depth.
- **Offline?** No — the models and market research live on the internet.
