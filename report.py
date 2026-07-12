"""Watto appraisal report — professional PDF, generated with the stdlib only.

A fixed template driven entirely by the session dict; every field is optional
and missing data simply collapses its section, so malformed model output can
never break report generation. Letter pages, Helvetica core fonts (no font
embedding needed), JPEG photos embedded via DCTDecode.
"""
import textwrap
import time

W, H = 612, 792          # US Letter, points
MARGIN = 54
CONTENT_W = W - 2 * MARGIN

GREEN = (0.075, 0.45, 0.22)
GREEN_DARK = (0.05, 0.32, 0.16)
GREEN_LIGHT = (0.87, 0.97, 0.90)
INK = (0.11, 0.10, 0.09)
MUTED = (0.44, 0.43, 0.41)
RED = (0.70, 0.11, 0.11)
RULE = (0.88, 0.88, 0.87)
WHITE = (1, 1, 1)


def _esc(s):
    # cp1252 bytes decoded as latin-1 survive the final latin-1 encode 1:1,
    # and the fonts declare /WinAnsiEncoding, so em dashes etc. render right.
    s = str(s).encode("cp1252", "replace").decode("latin-1")
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _money(v, currency="USD"):
    n = _num(v)
    if n is None:
        return "—"
    prefix = "$" if (currency or "USD").upper() == "USD" else f"{currency} "
    return f"{prefix}{n:,.0f}"


def jpeg_info(data):
    """(width, height, n_components) from a JPEG, or None if not parseable."""
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h = int.from_bytes(data[i + 5:i + 7], "big")
            w = int.from_bytes(data[i + 7:i + 9], "big")
            ncomp = data[i + 9]
            return w, h, ncomp
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    return None


class _Doc:
    """Page/cursor bookkeeping. y is in PDF coords (0 = bottom), moving down."""

    def __init__(self):
        self.pages = []           # each: {"ops": [str], "imgs": set()}
        self.images = []          # (data, w, h, ncomp) -> /Im{index}
        self.new_page()

    def new_page(self):
        self.pages.append({"ops": [], "imgs": set()})
        self.y = H - MARGIN

    @property
    def ops(self):
        return self.pages[-1]["ops"]

    def ensure(self, need):
        if self.y - need < MARGIN + 26:   # keep clear of the footer
            self.new_page()

    # -- primitives (absolute PDF coords) --
    def rect(self, x, y_bottom, w, h, color):
        self.ops.append("%.3f %.3f %.3f rg %.1f %.1f %.1f %.1f re f"
                        % (*color, x, y_bottom, w, h))

    def hline(self, y, x1=MARGIN, x2=W - MARGIN, color=RULE, width=0.7):
        self.ops.append("%.1f w %.3f %.3f %.3f RG %.1f %.1f m %.1f %.1f l S"
                        % (width, *color, x1, y, x2, y))

    def raw_text(self, x, y, size, s, font="F1", color=INK, char_space=0):
        self.ops.append("BT /%s %.1f Tf %.2f Tc %.3f %.3f %.3f rg %.1f %.1f Td (%s) Tj ET"
                        % (font, size, char_space, *color, x, y, _esc(s)))

    # -- flowing text (wraps, page-breaks) --
    def text(self, s, size=10, font="F1", color=INK, x=MARGIN,
             width=CONTENT_W, leading=None, gap=0):
        leading = leading or size * 1.4
        max_chars = max(8, int(width / (size * 0.5)))
        for para in str(s).split("\n"):
            for line in textwrap.wrap(para, max_chars) or [""]:
                self.ensure(leading)
                self.y -= leading
                self.raw_text(x, self.y, size, line, font, color)
        self.y -= gap

    def bullets(self, items, size=10, color=INK, marker_color=GREEN):
        for item in items:
            leading = size * 1.4
            max_chars = max(8, int((CONTENT_W - 14) / (size * 0.5)))
            lines = textwrap.wrap(str(item), max_chars) or [""]
            self.ensure(leading * len(lines))
            first = True
            for line in lines:
                self.y -= leading
                if first:
                    self.raw_text(MARGIN + 2, self.y, size, "\x95", "F2", marker_color)
                    first = False
                self.raw_text(MARGIN + 14, self.y, size, line, "F1", color)
        self.y -= 4

    def section(self, title):
        self.ensure(46)
        self.y -= 30
        self.raw_text(MARGIN, self.y, 9.5, title.upper(), "F2", GREEN, char_space=1.4)
        self.y -= 7
        self.hline(self.y)
        self.y -= 4

    def add_image(self, data):
        info = jpeg_info(data)
        if not info or info[2] not in (1, 3):
            return None                       # not an embeddable JPEG — skip
        self.images.append((data, *info))
        return len(self.images)               # 1-based /Im index


def _est(s, size):                            # crude Helvetica width estimate
    return len(str(s)) * size * 0.5


# ---------------------------------------------------------------- template

def _header(doc, session, result, triage):
    band_h = 92
    doc.rect(0, H - band_h, W, band_h, GREEN)
    doc.rect(0, H - band_h - 3, W, 3, GREEN_DARK)
    doc.raw_text(MARGIN, H - 46, 30, "Watto", "F2", WHITE)
    doc.raw_text(MARGIN, H - 66, 10, "APPRAISAL REPORT", "F2", GREEN_LIGHT, char_space=2.2)
    report_no = "Report No. WA-" + session.get("id", "000000")[:6].upper()
    date_s = time.strftime("%B %d, %Y")
    doc.raw_text(W - MARGIN - _est(report_no, 10), H - 42, 10, report_no, "F2", WHITE)
    doc.raw_text(W - MARGIN - _est(date_s, 10), H - 58, 10, date_s, "F1", GREEN_LIGHT)
    doc.y = H - band_h - 30

    # meta strip
    cells = [("CATEGORY", (triage.get("category") or "general").replace("_", " ")),
             ("CONFIDENCE", str(result.get("confidence", "—")).upper()),
             ("ID CERTAINTY", f"{round(float(triage.get('confidence', 0)) * 100)}%"
              if _num(triage.get("confidence")) is not None else "—"),
             ("PHOTOS/DOCS", str(len(session.get("attachments") or [])))]
    cw = CONTENT_W / len(cells)
    for i, (label, value) in enumerate(cells):
        x = MARGIN + i * cw
        doc.raw_text(x, doc.y, 7.5, label, "F2", MUTED, char_space=1)
        doc.raw_text(x, doc.y - 14, 11, value, "F2", INK)
    doc.y -= 26
    doc.hline(doc.y)


def _value_box(doc, result):
    box_h = 92
    doc.ensure(box_h + 16)
    top = doc.y - 10
    doc.rect(MARGIN, top - box_h, CONTENT_W, box_h, GREEN_LIGHT)
    doc.rect(MARGIN, top - box_h, 4, box_h, GREEN)
    cur = result.get("currency", "USD")
    rng = f"{_money(result.get('low'), cur)}  -  {_money(result.get('high'), cur)}"
    likely = f"Most likely sale price: {_money(result.get('most_likely'), cur)}"
    cx = MARGIN + CONTENT_W / 2
    doc.raw_text(cx - _est("APPRAISED VALUE RANGE", 8.5) / 2 - 8, top - 22, 8.5,
                 "APPRAISED VALUE RANGE", "F2", GREEN_DARK, char_space=1.6)
    doc.raw_text(cx - _est(rng, 25) / 2, top - 52, 25, rng, "F2", GREEN_DARK)
    doc.raw_text(cx - _est(likely, 10.5) / 2, top - 74, 10.5, likely, "F1", INK)
    doc.y = top - box_h - 6


def _photos(doc, session):
    embeddable = []
    listed_only = []
    for i, a in enumerate(session.get("attachments") or [], 1):
        try:
            import base64
            data = base64.b64decode(a.get("data_b64", ""))
        except Exception:
            data = b""
        name = a.get("name", f"file-{i}")
        idx = doc.add_image(data)
        if idx:
            embeddable.append((idx, name))
        else:
            listed_only.append(name)
    if not embeddable and not listed_only:
        return
    doc.section("Photographs & Documents")
    cell_w = (CONTENT_W - 16) / 2
    col = 0
    for idx, name in embeddable[:8]:
        data, iw, ih, _ = doc.images[idx - 1]
        scale = min(cell_w / iw, 180 / ih, 1.0)
        w, h = iw * scale, ih * scale
        if col == 0:
            doc.ensure(h + 26)
            row_top = doc.y - 8
        x = MARGIN + col * (cell_w + 16)
        y_bottom = row_top - h
        doc.pages[-1]["imgs"].add(idx)
        doc.ops.append("q %.1f 0 0 %.1f %.1f %.1f cm /Im%d Do Q" % (w, h, x, y_bottom, idx))
        doc.raw_text(x, y_bottom - 11, 8, name[:60], "F1", MUTED)
        col += 1
        if col == 2:
            doc.y = y_bottom - 22
            col = 0
    if col == 1:
        doc.y = y_bottom - 22
    if listed_only:
        doc.text("Also on file: " + ", ".join(listed_only), 9, "F3", MUTED, gap=2)


def _footers(doc):
    total = len(doc.pages)
    for i, page in enumerate(doc.pages, 1):
        page["ops"].append("%.1f w %.3f %.3f %.3f RG %.1f %.1f m %.1f %.1f l S"
                           % (0.7, *RULE, MARGIN, MARGIN - 6, W - MARGIN, MARGIN - 6))
        left = "Generated by Watto — AI-assisted market estimate, not a certified appraisal."
        right = f"Page {i} of {total}"
        page["ops"].append("BT /F1 7.5 Tf %.3f %.3f %.3f rg %.1f %.1f Td (%s) Tj ET"
                           % (*MUTED, MARGIN, MARGIN - 18, _esc(left)))
        page["ops"].append("BT /F1 7.5 Tf %.3f %.3f %.3f rg %.1f %.1f Td (%s) Tj ET"
                           % (*MUTED, W - MARGIN - _est(right, 7.5), MARGIN - 18, _esc(right)))


def build_pdf(session):
    result = session.get("result") or {}
    triage = session.get("triage") or {}
    research = session.get("research") or {}

    doc = _Doc()
    _header(doc, session, result, triage)

    ident = triage.get("identification") or session.get("description") or "Item"
    doc.y -= 26
    doc.text(ident, 16, "F2", gap=2)
    if session.get("description"):
        doc.text('Owner description: "%s"' % session["description"], 9.5, "F3", MUTED, gap=4)

    _value_box(doc, result)
    if result.get("summary"):
        doc.text(result["summary"], 10.5, "F1", INK, gap=2)

    facts = {k: v for k, v in (session.get("facts") or {}).items()}
    if facts:
        doc.section("Verified Item Details")
        for k, v in facts.items():
            label = k.replace("_", " ").capitalize()
            doc.text(f"{label}:  {v}", 10, gap=0)
        doc.y -= 4

    _photos(doc, session)

    comps = research.get("comps") or []
    spot = research.get("spot_prices") or {}
    notes = research.get("market_notes") or ""
    if comps or spot or notes:
        doc.section("Market Evidence")
        comp_lines = []
        for c in comps[:10]:
            if isinstance(c, dict):
                line = f"{c.get('title', 'Comparable sale')} - {c.get('price', '')}"
                src = c.get("source") or c.get("url") or ""
                if src:
                    line += f"  ({src})"
                comp_lines.append(line)
        if comp_lines:
            doc.bullets(comp_lines)
        for k, v in spot.items():
            doc.text(f"{k.replace('_', ' ').capitalize()}: {v}", 10, "F2", gap=0)
        if notes:
            doc.y -= 2
            doc.text(notes, 10, "F1", MUTED, gap=0)
    if research.get("error"):
        doc.section("Market Evidence")
        doc.text("Live market research was unavailable for this report; the "
                 "valuation relies on the appraisal model's knowledge and the "
                 "confidence rating has been reduced accordingly.", 10, "F3", MUTED)

    if result.get("red_flags"):
        doc.section("Risk Factors & Authenticity Notes")
        doc.bullets(result["red_flags"], marker_color=RED, color=RED)

    if result.get("reasoning"):
        doc.section("Valuation Reasoning")
        doc.text(result["reasoning"], 10, gap=2)

    if result.get("what_would_narrow_range"):
        doc.section("What Would Narrow This Range")
        doc.bullets(result["what_would_narrow_range"])

    if result.get("resale_channels"):
        doc.section("Recommended Sale Channels")
        doc.bullets(result["resale_channels"])

    doc.section("Terms")
    doc.text("This report is an AI-assisted market value estimate based on the "
             "photographs, information, and market data available at the time of "
             "generation. It is not a certified appraisal, does not constitute a "
             "guarantee of sale price or authenticity, and should not be used as "
             "the sole basis for insurance, legal, or lending decisions.",
             8.5, "F1", MUTED)

    _footers(doc)
    return _assemble(doc)


# ---------------------------------------------------------------- assembly

def _assemble(doc):
    n_imgs = len(doc.images)
    # object numbers: 1 catalog, 2 pages, 3-5 fonts, 6..5+n images, then per page (content, page)
    first_page_obj = 6 + n_imgs
    page_ids = [first_page_obj + 2 * i + 1 for i in range(len(doc.pages))]

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []

    def add(body):
        offsets.append(len(out))
        out.extend(f"{len(offsets)} 0 obj\n".encode("latin-1"))
        out.extend(body if isinstance(body, bytes) else body.encode("latin-1"))
        out.extend(b"\nendobj\n")

    add("<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{p} 0 R" for p in page_ids)
    add(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")
    for base in ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique"):
        add(f"<< /Type /Font /Subtype /Type1 /BaseFont /{base} /Encoding /WinAnsiEncoding >>")
    for data, w, h, ncomp in doc.images:
        cs = "/DeviceGray" if ncomp == 1 else "/DeviceRGB"
        head = (f"<< /Type /XObject /Subtype /Image /Width {w} /Height {h} "
                f"/ColorSpace {cs} /BitsPerComponent 8 /Filter /DCTDecode "
                f"/Length {len(data)} >>\nstream\n").encode("latin-1")
        add(head + data + b"\nendstream")
    for page in doc.pages:
        stream = "\n".join(page["ops"]).encode("latin-1")
        add(f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream")
        xobj = ""
        if page["imgs"]:
            refs = " ".join(f"/Im{i} {5 + i} 0 R" for i in sorted(page["imgs"]))
            xobj = f" /XObject << {refs} >>"
        content_id = len(offsets)
        add(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >>{xobj} >> "
            f"/Contents {content_id} 0 R >>")

    xref_at = len(out)
    out.extend(f"xref\n0 {len(offsets) + 1}\n".encode("latin-1"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets:
        out.extend(f"{off:010d} 00000 n \n".encode("latin-1"))
    out.extend((f"trailer\n<< /Size {len(offsets) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_at}\n%%EOF\n").encode("latin-1"))
    return bytes(out)
