#!/usr/bin/env python3
"""Watto CLI — the same appraisal pipeline, scriptable for automation.

Interactive:      python3 cli.py "gold ring with red stone, made in Russia" -i ring.jpg
Non-interactive:  python3 cli.py "1st edition Charizard" -i card.jpg --auto --json
Pre-answered:     python3 cli.py "gold ring" -i ring.jpg --fact weight_grams=12 --auto

When a question asks for a photo, you may answer with a file path and it
will be attached. --auto skips anything not covered by --fact.
"""
import argparse
import base64
import json
import mimetypes
import sys
from pathlib import Path

import engine


def load_attachment(path):
    p = Path(path)
    mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
    return {"name": p.name, "mime": mime,
            "data_b64": base64.b64encode(p.read_bytes()).decode()}


def main():
    parser = argparse.ArgumentParser(
        description="Watto — AI appraiser CLI",
        epilog="API key: stored via the web app Settings, or pass --api-key.")
    parser.add_argument("description", help="what the item is, in your own words")
    parser.add_argument("-i", "--image", action="append", default=[],
                        metavar="FILE", help="image or PDF (repeatable)")
    parser.add_argument("--fact", action="append", default=[], metavar="KEY=VALUE",
                        help="pre-answer a question, e.g. weight_grams=12")
    parser.add_argument("--auto", action="store_true",
                        help="never prompt; unanswered questions are skipped")
    parser.add_argument("--json", action="store_true", help="print raw JSON")
    parser.add_argument("--api-key", help="override the stored OpenRouter key")
    args = parser.parse_args()

    settings = engine.load_settings()
    if args.api_key:
        settings["api_key"] = args.api_key
    prefacts = dict(f.split("=", 1) for f in args.fact if "=" in f)

    appraiser = engine.Appraiser(settings)
    try:
        session = appraiser.new_session(args.description,
                                        [load_attachment(x) for x in args.image])
        while session["stage"] == "questions":
            answers, new_photos = {}, []
            for q in session["pending"]:
                if q["id"] in prefacts:
                    answers[q["id"]] = prefacts[q["id"]]
                    continue
                if args.auto:
                    answers[q["id"]] = ""
                    continue
                hint = f"  ({q['hint']})" if q.get("hint") else ""
                ans = input(f"? {q['question']}{hint}\n  [enter to skip] > ").strip()
                if ans and Path(ans).is_file():
                    new_photos.append(load_attachment(ans))
                    ans = f"(photo attached: {Path(ans).name})"
                answers[q["id"]] = ans
            appraiser.submit_answers(session, answers, new_photos)
    except engine.EngineError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(engine.public_view(session), indent=2))
        return

    r = session["result"]
    triage = session["triage"] or {}
    cur = r.get("currency", "USD")
    print(f"\n  {triage.get('identification', args.description)}")
    print(f"  {'-' * 56}")
    print(f"  Range:        {r['low']:,.0f} - {r['high']:,.0f} {cur}")
    print(f"  Most likely:  {r['most_likely']:,.0f} {cur}   (confidence: {r['confidence']})")
    if r.get("summary"):
        print(f"\n  {r['summary']}")
    for label, key in (("Red flags", "red_flags"),
                       ("Would narrow the range", "what_would_narrow_range"),
                       ("Where to sell", "resale_channels")):
        if r.get(key):
            print(f"\n  {label}:")
            for item in r[key]:
                print(f"   - {item}")
    if session.get("saved_dir"):
        print(f"\n  Saved (photos, record, PDF report): {session['saved_dir']}")
    print()


if __name__ == "__main__":
    main()
