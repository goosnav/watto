"""Watto appraisal engine — a deterministic pipeline that uses LLMs as components.

Code owns the state transitions; models only fill slots, and every model
reply must be strict JSON (one retry, then a clean error).

    triage   -> identify the item, decide which facts actually change value
    gather   -> ask the user only for those facts (max 2 rounds, all skippable)
    research -> web-search comps / spot prices (OpenRouter ':online' plugin)
    appraise -> strong model produces the final valuation JSON

Shared by server.py (web), cli.py (automation), and later the hosted API.
"""
import base64
import json
import re
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import report

SETTINGS_PATH = Path.home() / ".watto" / "settings.json"
APPRAISALS_DIR = Path.home() / "Watto Appraisals"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULTS = {
    "api_key": "",
    "triage_model": "google/gemini-2.5-flash",
    "research_model": "google/gemini-2.5-flash",
    "appraise_model": "anthropic/claude-sonnet-4.5",
    "web_search": True,
}

MAX_ROUNDS = 2  # question rounds before we appraise with whatever we have


class EngineError(Exception):
    """User-presentable failure (bad key, network, model gibberish)."""


# ---------------------------------------------------------------- settings

def load_settings():
    settings = dict(DEFAULTS)
    try:
        settings.update(json.loads(SETTINGS_PATH.read_text()))
    except (OSError, ValueError):
        pass
    return settings


def save_settings(updates):
    settings = load_settings()
    settings.update({k: v for k, v in updates.items() if k in DEFAULTS})
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))
    SETTINGS_PATH.chmod(0o600)  # the key is a secret
    return settings


# ---------------------------------------------------------------- LLM I/O

def extract_json(text):
    """Best effort: direct parse, fenced block, then first balanced {...}."""
    candidates = [text] + re.findall(r"```(?:json)?\s*(.*?)```", text, re.S)
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except ValueError:
            pass
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except ValueError:
                        break
        start = text.find("{", start + 1)
    return None


def call_openrouter(settings, model, system, parts, timeout=300):
    if not settings.get("api_key"):
        raise EngineError(
            "No OpenRouter API key set. Open Settings (gear icon) and paste "
            "your key from openrouter.ai/keys.")
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": parts},
        ],
    }).encode()
    req = urllib.request.Request(
        OPENROUTER_URL, data=body, method="POST",
        headers={
            "Authorization": "Bearer " + settings["api_key"],
            "Content-Type": "application/json",
            "X-Title": "Watto",
        })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        raise EngineError(f"OpenRouter error {e.code} for model '{model}': {detail}") from e
    except urllib.error.URLError as e:
        raise EngineError(f"Network error reaching OpenRouter: {e.reason}") from e
    if data.get("error"):
        raise EngineError(f"OpenRouter: {data['error'].get('message', data['error'])}")
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise EngineError(f"Unexpected OpenRouter response: {json.dumps(data)[:400]}") from e


def attachment_parts(attachments):
    parts = []
    for a in attachments or []:
        mime = a.get("mime") or "image/jpeg"
        if mime == "application/pdf":
            parts.append({"type": "file", "file": {
                "filename": a.get("name", "document.pdf"),
                "file_data": f"data:{mime};base64,{a['data_b64']}"}})
        else:
            parts.append({"type": "image_url", "image_url": {
                "url": f"data:{mime};base64,{a['data_b64']}"}})
    return parts


# ---------------------------------------------------------------- prompts

TRIAGE_SYSTEM = """You are the triage stage of Watto, a deterministic appraisal pipeline. \
Identify the item from the photos/documents/description and decide which ADDITIONAL facts \
are needed to appraise it accurately. You do NOT give a price.

Rules:
- Ask ONLY questions whose answers would materially change the appraised value. \
A trading card needs set/edition/condition, never weight. Jewelry needs weight, \
hallmarks/stamps, stone details. Real estate needs location, square footage, condition. \
Electronics need model number and working condition.
- Maximum 4 questions. If the photos and description are already sufficient, return an \
empty questions list — do not pad.
- Never re-ask a fact listed as known, and never re-ask one marked "(user does not know / skipped)" \
— work without it.
- Every question must be answerable by an ordinary person. If it needs a tool (scale, ruler), \
the hint must say it is fine to skip.
- If a close-up photo would materially help (hallmark, stamp, card edges, signature, serial \
number), ask for it with "type": "photo".
- "needs_research" is true when current market data (sold listings, spot metal prices) \
would improve the appraisal — true for almost everything except items with no resale market.

Return ONLY JSON:
{"identification": "<what this appears to be, specific>",
 "category": "<jewelry|trading_card|collectible|electronics|art|vehicle|real_estate|document|other>",
 "confidence": <0.0-1.0 that identification is correct>,
 "needs_research": <bool>,
 "questions": [{"id": "<snake_case>", "question": "<plain question>", "type": "text"|"photo", "hint": "<how to answer / ok to skip>"}]}"""

RESEARCH_SYSTEM = """You are the market-research stage of Watto, an appraisal pipeline. \
Search the web for CURRENT prices of items comparable to the one described: recent sold \
listings (eBay sold, auction results), current asking prices, and — when the item involves \
precious metals or gems — today's spot prices (e.g. gold USD/gram). Prefer sold prices over \
asking prices. Note any market trend that affects value.

Return ONLY JSON:
{"comps": [{"title": "<listing>", "price": "<e.g. $142 sold>", "source": "<site>", "url": "<link or empty>"}],
 "spot_prices": {"<metal or index>": "<current price>"},
 "market_notes": "<2-4 sentences: demand, trend, what drives value here>"}"""

APPRAISE_SYSTEM = """You are the final appraisal stage of Watto. Using the photos/documents, \
the verified facts, and the market research, produce a defensible valuation — the realistic \
price the item would fetch, not a hopeful one.

Rules:
- Be blunt about authenticity risk: fake or plated gold, counterfeit cards, glass stones, \
replica goods. Cheap origin cues (e.g. unmarked metal, suspicious stamps) belong in red_flags.
- If key facts were skipped, widen the range and lower confidence rather than guessing narrowly.
- Anchor to the research comps when available; say so in the reasoning.
- most_likely is what a knowledgeable buyer actually pays (pawn/resale reality, not retail dreams).

Return ONLY JSON:
{"low": <number>, "high": <number>, "most_likely": <number>, "currency": "USD",
 "confidence": "low"|"medium"|"high",
 "summary": "<2-3 sentence verdict a pawn-shop clerk can read aloud>",
 "reasoning": "<the full chain: identification, facts used, comps used, math>",
 "red_flags": ["<authenticity or condition concern>"],
 "what_would_narrow_range": ["<missing fact and how it moves the number>"],
 "resale_channels": ["<best places to sell this and why>"]}"""


def _facts_block(session):
    if not session["facts"]:
        return "No extra facts beyond the description."
    return "Facts gathered from the user:\n" + "\n".join(
        f"- {k}: {v}" for k, v in session["facts"].items())


# ---------------------------------------------------------------- pipeline

class Appraiser:
    def __init__(self, settings, llm=None):
        self.settings = settings
        self.llm = llm or call_openrouter

    def _json_call(self, model, system, parts):
        reply = self.llm(self.settings, model, system, parts)
        obj = extract_json(reply)
        if obj is None:
            retry = parts + [{"type": "text", "text":
                              "Your previous reply was not valid JSON. Reply with ONLY the JSON object."}]
            obj = extract_json(self.llm(self.settings, model, system, retry))
        if not isinstance(obj, dict):
            raise EngineError(f"Model '{model}' did not return valid JSON. "
                              "Try a different model in Settings.")
        return obj

    def new_session(self, description, attachments=None):
        session = {
            "id": uuid.uuid4().hex[:12],
            "stage": "triage",
            "description": description or "",
            "attachments": list(attachments or []),
            "facts": {},
            "rounds": 0,
            "pending": [],
            "triage": None,
            "research": None,
            "result": None,
        }
        return self._advance(session)

    def submit_answers(self, session, answers=None, attachments=None):
        answers = answers or {}
        for q in session["pending"]:
            value = str(answers.get(q["id"], "")).strip()
            session["facts"][q["id"]] = value or "(user does not know / skipped)"
        if attachments:
            session["attachments"].extend(attachments)
        session["pending"] = []
        session["rounds"] += 1
        return self._advance(session)

    def _advance(self, session):
        triage = self._triage(session)
        session["triage"] = triage
        questions = [q for q in (triage.get("questions") or [])
                     if isinstance(q, dict) and q.get("id") and q.get("question")]
        if questions and session["rounds"] < MAX_ROUNDS:
            session["stage"] = "questions"
            session["pending"] = questions[:4]
            return session
        if triage.get("needs_research", True) and self.settings.get("web_search", True):
            try:
                session["research"] = self._research(session)
            except EngineError as e:
                # research is best-effort: appraise anyway, at lower confidence
                session["research"] = {"error": str(e), "comps": [], "market_notes": ""}
        session["result"] = self._appraise(session)
        session["stage"] = "done"
        try:
            save_appraisal(session)
        except Exception as e:
            # saving is a convenience; never let it kill a finished appraisal
            session["save_error"] = f"Could not save the appraisal folder: {e}"
        return session

    def _triage(self, session):
        text = (f"Item description from the user:\n{session['description'] or '(none)'}\n\n"
                f"{_facts_block(session)}")
        parts = [{"type": "text", "text": text}] + attachment_parts(session["attachments"])
        return self._json_call(self.settings["triage_model"], TRIAGE_SYSTEM, parts)

    def _research(self, session):
        model = self.settings["research_model"]
        if ":online" not in model:
            model += ":online"  # OpenRouter web-search plugin
        triage = session["triage"] or {}
        text = (f"Item: {triage.get('identification', session['description'])}\n"
                f"Category: {triage.get('category', 'unknown')}\n"
                f"Description: {session['description']}\n{_facts_block(session)}")
        return self._json_call(model, RESEARCH_SYSTEM, [{"type": "text", "text": text}])

    def _appraise(self, session):
        research = session["research"]
        research_text = (json.dumps(research, indent=2) if research
                         else "No market research was performed.")
        if research and research.get("error"):
            research_text = ("Market research FAILED (cap confidence at medium): "
                             + research["error"])
        text = (f"Item description: {session['description'] or '(none)'}\n\n"
                f"Triage identification:\n{json.dumps(session['triage'], indent=2)}\n\n"
                f"{_facts_block(session)}\n\n"
                f"Market research:\n{research_text}")
        parts = [{"type": "text", "text": text}] + attachment_parts(session["attachments"])
        result = self._json_call(self.settings["appraise_model"], APPRAISE_SYSTEM, parts)
        for key, default in (("low", 0), ("high", 0), ("most_likely", 0),
                             ("currency", "USD"), ("confidence", "low"),
                             ("summary", ""), ("reasoning", ""), ("red_flags", []),
                             ("what_would_narrow_range", []), ("resale_channels", [])):
            result.setdefault(key, default)
        return result


def save_appraisal(session):
    """One folder per appraised item: photos, full record JSON, PDF report."""
    triage = session["triage"] or {}
    slug = re.sub(r"[^a-z0-9]+", "-",
                  (triage.get("identification") or session["description"] or "item")
                  .lower()).strip("-")[:40] or "item"
    folder = APPRAISALS_DIR / f"{time.strftime('%Y-%m-%d_%H%M')}-{slug}-{session['id'][:6]}"
    folder.mkdir(parents=True, exist_ok=True)
    for i, a in enumerate(session["attachments"], 1):
        ext = ".pdf" if a.get("mime") == "application/pdf" else ".jpg"
        try:
            (folder / f"photo-{i}{ext}").write_bytes(base64.b64decode(a.get("data_b64", "")))
        except Exception:
            pass  # one corrupt upload shouldn't lose the rest
    record = {k: session[k] for k in
              ("id", "description", "facts", "triage", "research", "result")}
    record["saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (folder / "appraisal.json").write_text(json.dumps(record, indent=2))
    (folder / "report.pdf").write_bytes(report.build_pdf(session))
    session["saved_dir"] = str(folder)
    session["report_pdf"] = str(folder / "report.pdf")
    return folder


def public_view(session):
    """What the web/CLI clients see (no raw attachments echoed back)."""
    triage = session["triage"] or {}
    return {
        "session_id": session["id"],
        "stage": session["stage"],
        "identification": triage.get("identification"),
        "category": triage.get("category"),
        "questions": session["pending"],
        "research": session["research"],
        "result": session["result"],
        "saved_dir": session.get("saved_dir"),
        "report_available": bool(session.get("report_pdf")),
        "save_error": session.get("save_error"),
    }
