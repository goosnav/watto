# Watto — know what it's worth

A generalist AI appraiser. Give it photos and a one-line description of
anything — jewelry, trading cards, electronics, art, documents, real estate —
and it identifies the item, asks **only** the follow-up questions that
actually change the value (weight for a gold ring, edition for a Pokémon
card, nothing for either that doesn't matter), researches live market prices,
and returns a defensible price range with red flags and resale advice.

Unlike a plain chatbot, Watto is a **deterministic pipeline**: code owns the
process (identify → gather facts → research market → appraise), and the AI
models are swappable components inside it. It never gives up because you
don't own a scale — skipped questions just widen the range.

## Quick start (60 seconds)

1. **Get a key:** create one at [openrouter.ai/keys](https://openrouter.ai/keys)
   (one key = every major AI model; add $5 credit to start).
2. **Launch:** double-click `run.command` (macOS) — or `run.sh` (Linux) /
   `run.ps1` (Windows). Your browser opens automatically.
3. **Paste the key** in Settings (gear icon, top right). It is stored only on
   this computer (`~/.watto/settings.json`, owner-readable only).
4. Drop in a photo, type a sentence, hit **Appraise it**.

Requires only Python 3.9+ (preinstalled on macOS; [python.org](https://python.org)
on Windows). **Zero dependencies to install.**

## What's in the box

| File | What it is |
|---|---|
| `run.command` / `run.sh` / `run.ps1` | double-click launchers |
| `server.py` | local web server (binds 127.0.0.1 only — never exposed to the network) |
| `engine.py` | the appraisal state machine (shared by web, CLI, and the future hosted version) |
| `cli.py` | command-line interface for developers/automation |
| `static/index.html` | the entire UI |
| `test_watto.py` | offline self-test: `python3 test_watto.py` |
| `dev/` | architecture, hosted-SaaS launch guide, sales guide, roadmap |
| `TUTORIAL.md` | full walkthrough with examples |

## Models

Three roles, all configurable in Settings (any [OpenRouter model slug](https://openrouter.ai/models)):

- **Triage** — fast/cheap vision model that identifies the item and picks questions. Default `google/gemini-2.5-flash`.
- **Research** — gets OpenRouter's `:online` web-search plugin automatically; pulls sold comps and spot metal prices. Default `google/gemini-2.5-flash`.
- **Appraisal** — your smartest model; produces the final number. Default `anthropic/claude-sonnet-4.5`.

Free `:free` model slugs work too (quality is lower and rate limits apply).

## CLI (for automation)

```bash
python3 cli.py "gold ring with red stone, made in Russia" -i ring.jpg          # interactive
python3 cli.py "1st edition Charizard" -i card.jpg --auto --json               # one-shot, machine-readable
python3 cli.py "gold ring" -i ring.jpg --fact weight_grams=12 --auto           # pre-answered
```

`--auto` never prompts (skipped questions widen the range); `--json` emits the
full structured result for pipelines.

## Troubleshooting

- **"No OpenRouter API key set"** — gear icon → paste key → Save.
- **Browser didn't open** — go to `http://127.0.0.1:8177` manually.
- **macOS blocks run.command** — right-click → Open (first launch only), or
  `chmod +x run.command` in Terminal.
- **"OpenRouter error 402"** — your OpenRouter account is out of credit.
- **A model errors or returns garbage** — switch that role to another slug in
  Settings; free models are the usual culprits.
- **Port already in use** — `python3 server.py --port 8200 --open`.

## Verify the install

```bash
python3 test_watto.py   # runs the full pipeline offline — no key needed
```
