#!/usr/bin/env python3
"""Offline smoke test — full state machine against a scripted fake LLM.
No network, no API key needed.  Run: python3 test_watto.py"""
import json

import engine

TRIAGE_WITH_QS = json.dumps({
    "identification": "Gold ring with red stone, possibly Soviet 583 gold",
    "category": "jewelry", "confidence": 0.6, "needs_research": True,
    "questions": [
        {"id": "weight_grams", "question": "How much does it weigh in grams?",
         "type": "text", "hint": "Kitchen scale is fine; skip if you have none"},
        {"id": "hallmark_photo", "question": "Close-up of any stamp inside the band?",
         "type": "photo", "hint": "Look inside the ring"},
    ],
})
TRIAGE_DONE = json.dumps({
    "identification": "Soviet 583 (14k) gold ring, ~12g, synthetic ruby",
    "category": "jewelry", "confidence": 0.9, "needs_research": True, "questions": [],
})
RESEARCH = json.dumps({
    "comps": [{"title": "Soviet 583 ring 11.8g", "price": "$310 sold",
               "source": "ebay", "url": "https://example.com"}],
    "spot_prices": {"gold_usd_per_gram": "$108"},
    "market_notes": "Soviet gold trades near melt plus a small collector premium.",
})
APPRAISE = json.dumps({
    "low": 280, "high": 420, "most_likely": 340, "currency": "USD",
    "confidence": "medium", "summary": "Melt-value driven.",
    "reasoning": "12g x 0.583 x $108 = ~$755 retail melt... resale discount applied.",
    "red_flags": ["Stone is likely synthetic (standard for Soviet rings)"],
    "what_would_narrow_range": ["Acid test would confirm purity"],
    "resale_channels": ["Local gold buyer", "eBay"],
})


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, settings, model, system, parts):
        self.calls.append(model)
        return self.replies.pop(0)


def test_full_flow():
    settings = dict(engine.DEFAULTS, api_key="test", web_search=True)
    llm = FakeLLM([TRIAGE_WITH_QS, TRIAGE_DONE, RESEARCH, APPRAISE])
    ap = engine.Appraiser(settings, llm=llm)

    s = ap.new_session("gold ring from Russia",
                       [{"name": "ring.jpg", "mime": "image/jpeg", "data_b64": "aGk="}])
    assert s["stage"] == "questions", s["stage"]
    assert len(s["pending"]) == 2

    ap.submit_answers(s, {"weight_grams": "12"})  # hallmark photo skipped
    assert s["stage"] == "done"
    assert s["facts"]["weight_grams"] == "12"
    assert "skipped" in s["facts"]["hallmark_photo"]
    assert s["result"]["most_likely"] == 340
    assert s["research"]["comps"][0]["source"] == "ebay"
    assert ":online" in llm.calls[2], "research must use the web plugin"

    view = engine.public_view(s)
    assert view["stage"] == "done" and view["result"]["low"] == 280
    assert "attachments" not in view


def test_no_questions_short_circuit():
    settings = dict(engine.DEFAULTS, api_key="test", web_search=False)
    llm = FakeLLM([TRIAGE_DONE, APPRAISE])
    s = engine.Appraiser(settings, llm=llm).new_session("charizard card")
    assert s["stage"] == "done"
    assert s["research"] is None  # web_search off -> no research call


def test_research_failure_degrades_gracefully():
    settings = dict(engine.DEFAULTS, api_key="test", web_search=True)
    llm = FakeLLM([TRIAGE_DONE, APPRAISE])

    def wrapper(settings_, model, system, parts):
        if ":online" in model:
            raise engine.EngineError("web plugin down")
        return llm(settings_, model, system, parts)

    s = engine.Appraiser(settings, llm=wrapper).new_session("gold ring")
    assert s["stage"] == "done"
    assert s["research"]["error"] == "web plugin down"
    assert s["result"]["most_likely"] == 340


def test_extract_json():
    ej = engine.extract_json
    assert ej('{"a": 1}') == {"a": 1}
    assert ej('Sure! ```json\n{"a": 1}\n``` hope that helps') == {"a": 1}
    assert ej('preamble {"a": {"b": 2}} trailing') == {"a": {"b": 2}}
    assert ej('no json here') is None


def test_json_retry():
    settings = dict(engine.DEFAULTS, api_key="test")
    llm = FakeLLM(["not json at all", '{"ok": true}'])
    ap = engine.Appraiser(settings, llm=llm)
    assert ap._json_call("m", "sys", [{"type": "text", "text": "x"}]) == {"ok": True}
    assert len(llm.calls) == 2


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
    print("all tests passed")
