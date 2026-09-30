from pathlib import Path
import json
import re
import subprocess
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "presentation" / "Risk_Assessment_Workbench_Genius_Hacks_2026.pptx"
EVAL_RESULTS = ROOT / "evals" / "results" / "latest.json"

# Palette: blues and white only
NAVY = RGBColor(0x0A, 0x25, 0x40)
NAVY_2 = RGBColor(0x12, 0x36, 0x5F)
BLUE = RGBColor(0x1F, 0x5F, 0xBF)
MID = RGBColor(0x3B, 0x82, 0xF6)
SKY = RGBColor(0x93, 0xC5, 0xFD)
ICE = RGBColor(0xDB, 0xEA, 0xFE)
PALE = RGBColor(0xEF, 0xF6, 0xFF)
BORDER = RGBColor(0xC7, 0xDB, 0xF5)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0x47, 0x55, 0x69)
HEAD_FONT = "Cambria"
BODY_FONT = "Calibri"

# Layout coordinates below are written for a 10 x 5.625 in canvas and scaled to 13.333 x 7.5 in.
S = 13.333 / 10


def evaluation_summary():
    data = json.loads(EVAL_RESULTS.read_text(encoding="utf-8"))
    successful = [item for item in data["results"] if item.get("success")]
    total_fields = sum(item.get("total_fields", 0) for item in successful)
    correct_fields = sum(item.get("correct_fields", 0) for item in successful)
    agreement_count = sum(bool(item.get("risk_agreement")) for item in successful)
    latency_values = [item["latency_ms"] for item in successful if "latency_ms" in item]
    return {
        "case_count": data.get("case_count", len(data["results"])),
        "successful_count": len(successful),
        "total_fields": total_fields,
        "correct_fields": correct_fields,
        "field_accuracy": correct_fields / total_fields if total_fields else None,
        "risk_agreement": agreement_count / len(successful) if successful else None,
        "mean_latency_ms": round(sum(latency_values) / len(latency_values)) if latency_values else None,
    }


def pytest_result():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "not verified"

    output = f"{result.stdout}\n{result.stderr}"
    match = re.search(r"(\d+) passed(?:,|\s|$)", output)
    if result.returncode == 0 and match:
        return f"{match.group(1)} passed"
    if match:
        return f"{match.group(1)} passed; failures"
    return "not verified"




def per_case_accuracy():
    """Field accuracy (%) for each successful case, read from the latest live evaluation."""
    data = json.loads(EVAL_RESULTS.read_text(encoding="utf-8"))
    rows = []
    for item in data["results"]:
        if item.get("success") and item.get("total_fields"):
            rows.append((item["case_id"].split("-")[-1], round(100 * item["correct_fields"] / item["total_fields"])))
    return rows


# ---------------------------------------------------------------- helpers
def _emu(v):
    return Inches(v * S)


def text_box(slide, text, x, y, w, h, size=13, color=NAVY, bold=False, font=BODY_FONT,
             align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, italic=False, spacing=None):
    shape = slide.shapes.add_textbox(_emu(x), _emu(y), _emu(w), _emu(h))
    frame = shape.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    frame.vertical_anchor = anchor
    lines = text if isinstance(text, list) else [text]
    for index, line in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.alignment = align
        if spacing:
            paragraph.space_after = Pt(spacing)
        run = paragraph.add_run()
        run.text = line
        run.font.name = font
        run.font.size = Pt(size * S)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = color
    return shape


def bullet_box(slide, items, x, y, w, h, size=13, color=NAVY):
    shape = slide.shapes.add_textbox(_emu(x), _emu(y), _emu(w), _emu(h))
    frame = shape.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
    frame.vertical_anchor = MSO_ANCHOR.TOP
    for index, item in enumerate(items):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.space_after = Pt(5 * S)
        run = paragraph.add_run()
        run.text = item
        run.font.name = BODY_FONT
        run.font.size = Pt(size * S)
        run.font.color.rgb = color
        # real bullet with a hanging indent (no literal bullet characters in the text)
        pPr = paragraph._p.get_or_add_pPr()
        pPr.set("marL", str(int(Inches(0.2))))
        pPr.set("indent", str(-int(Inches(0.2))))
        bu = pPr.makeelement("{http://schemas.openxmlformats.org/drawingml/2006/main}buChar", {"char": "\u2022"})
        pPr.append(bu)
    return shape


def shape(slide, kind, x, y, w, h, fill, line=None, radius=0.08, line_w=0.75):
    item = slide.shapes.add_shape(kind, _emu(x), _emu(y), _emu(w), _emu(h))
    item.fill.solid()
    item.fill.fore_color.rgb = fill
    item.line.color.rgb = line or fill
    item.line.width = Pt(line_w)
    item.shadow.inherit = False
    for ref in item._element.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}effectRef"):
        ref.set("idx", "0")  # no theme shadow in any renderer
    if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        item.adjustments[0] = min(0.5, radius / min(w, h))
    return item


def rrect(slide, x, y, w, h, fill, line=None):
    return shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill, line)


def card(slide, x, y, w, h, dark=False):
    return rrect(slide, x, y, w, h, NAVY_2 if dark else PALE, RGBColor(0x24, 0x50, 0x8A) if dark else BORDER)


def heading(slide, text, x, y, w, dark=False, size=15):
    return text_box(slide, text, x, y, w, 0.35, size, WHITE if dark else NAVY, True)


def badge(slide, number, x, y, d, fill):
    shape(slide, MSO_SHAPE.OVAL, x, y, d, d, fill)
    text_box(slide, str(number), x, y, d, d, 16, WHITE, True, HEAD_FONT, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)


def new_slide(prs, state, kicker, title_text, dark=False, notes=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    state["n"] += 1
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = NAVY if dark else WHITE
    if kicker:
        text_box(slide, kicker.upper(), 0.5, 0.3, 8, 0.3, 11, SKY if dark else BLUE, True)
        text_box(slide, title_text, 0.5, 0.6, 9, 0.65, 28, WHITE if dark else NAVY, True, HEAD_FONT)
        text_box(slide, "Risk Assessment Workbench  |  Genius Hacks 2026", 0.5, 5.25, 6, 0.25, 9, SKY if dark else MUTED)
        text_box(slide, str(state["n"]), 9.0, 5.25, 0.5, 0.25, 9, SKY if dark else MUTED, align=PP_ALIGN.RIGHT)
    if notes:
        slide.notes_slide.notes_text_frame.text = notes
    return slide


def flow(slide, labels, kinds, x0, y, bw, gap, h, size=14):
    for index, (label, kind) in enumerate(zip(labels, kinds)):
        x = x0 + index * (bw + gap)
        fill = {"ai": SKY, "code": NAVY, "human": BLUE}.get(kind, PALE)
        color = WHITE if kind in ("code", "human") else NAVY
        rrect(slide, x, y, bw, h, fill, BORDER if kind == "plain" else fill)
        text_box(slide, label, x, y, bw, h, size, color, True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        if index < len(labels) - 1:
            text_box(slide, "\u2192", x + bw, y, gap, h, 16, BLUE, False, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def style_chart(chart, title_text, max_value):
    chart.has_legend = False
    chart.has_title = True
    chart.chart_title.text_frame.text = title_text
    run = chart.chart_title.text_frame.paragraphs[0].runs[0]
    run.font.size = Pt(12 * S)
    run.font.bold = False
    run.font.name = BODY_FONT
    run.font.color.rgb = NAVY
    chart.value_axis.visible = False
    chart.value_axis.has_major_gridlines = False
    chart.value_axis.maximum_scale = max_value
    chart.value_axis.minimum_scale = 0
    chart.category_axis.has_major_gridlines = False
    chart.category_axis.format.line.color.rgb = BORDER
    chart.category_axis.tick_labels.font.size = Pt(11 * S)
    chart.category_axis.tick_labels.font.name = BODY_FONT
    chart.category_axis.tick_labels.font.color.rgb = NAVY
    plot = chart.plots[0]
    plot.gap_width = 55
    plot.has_data_labels = True
    labels = plot.data_labels
    labels.font.size = Pt(11 * S)
    labels.font.name = BODY_FONT
    labels.font.color.rgb = NAVY
    labels.show_value = True
    from pptx.enum.chart import XL_LABEL_POSITION
    labels.position = XL_LABEL_POSITION.OUTSIDE_END


# ---------------------------------------------------------------- deck
def build_deck():
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE

    evaluation = evaluation_summary()
    test_result = pytest_result()
    state = {"n": 0}
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 1. Title
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    state["n"] += 1
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = NAVY
    text_box(slide, "GENIUS HACKS 2026", 0.6, 0.9, 5.5, 0.3, 12, SKY, True)
    text_box(slide, "Risk Assessment Workbench", 0.6, 1.35, 5.6, 1.5, 40, WHITE, True, HEAD_FONT)
    text_box(slide, "From an unstructured change request to a governed, reviewable risk decision.", 0.6, 3.05, 5.4, 0.8, 16, ICE)
    text_box(slide, "A synthetic-data vertical slice for financial crimes risk management", 0.6, 4.7, 5.6, 0.3, 11, SKY)
    rrect(slide, 6.7, 0.9, 2.8, 3.8, NAVY_2, RGBColor(0x24, 0x50, 0x8A))
    text_box(slide, ["Prepare evidence.", "Preserve disagreement.", "Keep humans accountable."], 6.95, 1.3, 2.3, 3.0, 20, WHITE, True, HEAD_FONT, anchor=MSO_ANCHOR.MIDDLE, spacing=14 * S)
    slide.notes_slide.notes_text_frame.text = "0:00-0:20. One-sentence pitch: the system prepares the evidence, humans make the decision. Introduce the team and roles."

    # 2. Problem
    slide = new_slide(prs, state, "The problem", "Slow, variable, and hard to reconstruct",
                      notes="0:20-0:50. State the pain in numbers, then the design stance: nothing is approved or rejected automatically. The brief was half a page; it was expanded into docs/requirements.")
    rrect(slide, 0.5, 1.5, 3.0, 3.5, NAVY)
    text_box(slide, "15-20", 0.75, 1.65, 2.5, 0.8, 44, WHITE, True, HEAD_FONT)
    text_box(slide, "business days per assessment today", 0.75, 2.45, 2.5, 0.5, 13, ICE)
    text_box(slide, "~2", 0.75, 3.3, 2.5, 0.8, 44, SKY, True, HEAD_FONT)
    text_box(slide, "days to decision-ready: the target in the brief", 0.75, 4.1, 2.5, 0.6, 13, ICE)
    card(slide, 3.7, 1.5, 2.85, 3.5)
    heading(slide, "Today", 3.9, 1.65, 2.5)
    bullet_box(slide, ["Email, Word, Excel, SharePoint", "Different analysts reach different conclusions", "Examiner asks why it was rated this way: evidence is scattered and slow to rebuild"], 3.9, 2.1, 2.5, 2.8, 14)
    card(slide, 6.7, 1.5, 2.8, 3.5)
    heading(slide, "Our response", 6.9, 1.65, 2.4)
    bullet_box(slide, ["One governed case record", "AI structures the evidence", "Humans own the decision", "Every rating traceable to inputs and reasoning"], 6.9, 2.1, 2.4, 2.8, 14)

    # 3. Architecture
    slide = new_slide(prs, state, "Architecture", "A deliberately narrow AI boundary",
                      notes="0:50-1:50. Walk the pipeline left to right. Extraction is a probabilistic problem, scoring is not, so scoring is plain Python a committee can reproduce. This is the engineering-judgement answer.")
    flow(slide, ["PDF", "pypdf", "LLM JSON", "Rules", "SQLite", "Review"], ["plain", "plain", "ai", "code", "plain", "human"], 0.65, 1.55, 1.2, 0.3, 0.7)
    for index, (label, color) in enumerate([("Probabilistic (AI)", SKY), ("Deterministic (code)", NAVY), ("Human", BLUE)]):
        x = 0.65 + index * 2.6
        rrect(slide, x, 2.5, 0.22, 0.22, color)
        text_box(slide, label, x + 0.32, 2.44, 2.1, 0.34, 12, MUTED, anchor=MSO_ANCHOR.MIDDLE)
    card(slide, 0.5, 3.0, 4.4, 2.0)
    heading(slide, "AI does", 0.7, 3.12, 4.0)
    bullet_box(slide, ["Extract structure from unstructured text", "Identify stated risk factors", "Attempt semantic policy retrieval when configured"], 0.7, 3.55, 4.0, 1.35, 13)
    card(slide, 5.1, 3.0, 4.4, 2.0)
    heading(slide, "Code does", 5.3, 3.12, 4.0)
    bullet_box(slide, ["Validate schemas", "Calculate scores and thresholds", "Persist workflow events; policy lookup falls back to rules"], 5.3, 3.55, 4.0, 1.35, 13)

    # 4. Harness
    slide = new_slide(prs, state, "AI harness and context", "The document is data, not authority",
                      notes="1:50-2:50. Context management: untrusted-document boundary, schema-constrained output, versioned prompts. If asked why no multi-agent orchestration: one narrow extraction step does not need it, and every extra agent is another probabilistic step to govern and evaluate.")
    columns = [
        ("Context boundary", ["Source text is explicitly untrusted", "Embedded instructions cannot approve a case", "Prompt requires faithful extraction"]),
        ("Structured contract", ["Pydantic schema at the model boundary", "Malformed output fails loudly", "Extraction versions stay reconstructable"]),
        ("Traceable context", ["Synthetic policy IDs and source paths", "Prompt version telemetry", "Analyst can disagree with the rationale"]),
    ]
    for index, (name, items) in enumerate(columns):
        x = 0.5 + index * 3.075
        card(slide, x, 1.5, 2.85, 3.5)
        badge(slide, index + 1, x + 0.25, 1.7, 0.6, BLUE)
        heading(slide, name, x + 0.25, 2.5, 2.4)
        bullet_box(slide, items, x + 0.25, 2.95, 2.4, 1.95, 13)

    # 5. Scoring (native chart)
    slide = new_slide(prs, state, "Engineering judgement", "Scoring is explainable by construction",
                      notes="2:50-3:30. Deterministic versus probabilistic, justified. Be upfront that the weights are a prototype choice awaiting FCRM approval.")
    data = CategoryChartData()
    data.categories = ["Customer + geography", "Product + channel", "Third party", "Complexity"]
    data.add_series("Weight (%)", (35, 30, 20, 15))
    frame = slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, _emu(0.5), _emu(1.5), _emu(5.0), _emu(3.5), data)
    chart = frame.chart
    style_chart(chart, "Category weight in the risk score (%)", 45)
    chart.category_axis.reverse_order = True
    for index, color in enumerate([NAVY, BLUE, MID, SKY]):
        point = chart.plots[0].series[0].points[index]
        point.format.fill.solid()
        point.format.fill.fore_color.rgb = color
    card(slide, 5.7, 1.5, 3.8, 1.95)
    heading(slide, "Why not an LLM score?", 5.9, 1.62, 3.4)
    text_box(slide, "A committee must reproduce, challenge, and test the number. The model structures evidence; deterministic Python combines category scores.", 5.9, 2.0, 3.4, 1.35, 13)
    card(slide, 5.7, 3.6, 3.8, 1.4)
    heading(slide, "Honest limits", 5.9, 3.7, 3.4)
    text_box(slide, "Weights and policy material are synthetic, not approved supervisory mappings. Control effectiveness and residual risk are not yet modeled.", 5.9, 4.05, 3.4, 0.9, 12)

    # 6. Six stages
    slide = new_slide(prs, state, "Six stages", "AI is part of delivery, not only runtime code",
                      notes="3:30-4:15. One line per stage, naming the artifact: docs/requirements, docs/architecture, src and ai, tests and evals, ops. Point to docs/sdlc/ai-delivery-evidence.md. Move fast; the repo carries the detail.")
    stages = [("Requirements", "Brief \u2192 spec"), ("Design", "Options \u2192 decision"), ("Development", "Contract \u2192 code"),
              ("Testing", "Cases \u2192 metrics"), ("Deployment", "Image \u2192 runbook"), ("Operations", "Telemetry \u2192 feedback")]
    for index, (name, detail) in enumerate(stages):
        x = 0.5 + (index % 3) * 3.075
        y = 1.5 + (index // 3) * 1.65
        card(slide, x, y, 2.85, 1.5)
        badge(slide, index + 1, x + 0.25, y + 0.25, 0.55, BLUE if index % 2 else NAVY)
        text_box(slide, name, x + 0.95, y + 0.25, 1.8, 0.55, 16, NAVY, True, anchor=MSO_ANCHOR.MIDDLE)
        text_box(slide, detail, x + 0.25, y + 0.95, 2.4, 0.4, 13, MUTED, anchor=MSO_ANCHOR.MIDDLE)
    text_box(slide, "Each stage has an AI instruction, a human gate, and a repository artifact.", 0.5, 4.85, 9, 0.3, 13, BLUE, True)

    # 7. Governance
    slide = new_slide(prs, state, "Human-in-the-loop", "The system prepares; people decide",
                      notes="4:15-5:15. For each gate say what risk it controls: the analyst gate stops a bad extraction reaching the committee; the committee vote keeps the decision human; audit events answer the examiner months later. Nothing is auto-approved.")
    flow(slide, ["Draft", "Edit", "Finalize", "Committee", "Decision"], ["ai", "human", "human", "human", "human"], 0.5, 1.45, 1.5, 0.375, 0.55)
    gates = [
        ("Analyst gate", ["Accept or reject the draft", "Edit and rescore", "Rationale required"]),
        ("Committee rule", ["Three distinct votes required", "Approve / reject / defer / conditions", "Two approvals/rejections decide; otherwise defer"]),
        ("Audit evidence", ["UTC timestamps", "Append-only workflow events", "Original and edited versions kept"]),
    ]
    for index, (name, items) in enumerate(gates):
        x = 0.5 + index * 3.075
        card(slide, x, 2.3, 2.85, 2.35)
        badge(slide, index + 1, x + 0.25, 2.42, 0.4, BLUE)
        text_box(slide, name, x + 0.95, 2.42, 1.8, 0.4, 15, NAVY, True, anchor=MSO_ANCHOR.MIDDLE)
        bullet_box(slide, items, x + 0.25, 3.0, 2.4, 1.6, 13)
    text_box(slide, "Prototype only: demo identity, voting rule not approved as institutional policy, storage not tamper-proof.", 0.5, 4.8, 9, 0.3, 11, MUTED, italic=True)

    # 8. Demo
    slide = new_slide(prs, state, "Working demonstration", "One synthetic case, end to end",
                      notes="5:15-7:45 (about 2.5 minutes). Rehearse this path on the network you will use on the day. If OpenAI is unreachable: play the backup screen recording and show the eval results and passing tests. Say aloud what each role sees.")
    line = slide.shapes.add_connector(1, _emu(1.25), _emu(2.05), _emu(8.75), _emu(2.05))
    line.line.color.rgb = SKY
    line.line.width = Pt(2 * S)
    steps = ["Sign in as product-owner-1", "Upload synthetic PDF", "Inspect fields and score", "Switch to analyst-1", "Finalize with rationale", "Three committee votes"]
    for index, step in enumerate(steps):
        cx = 1.25 + index * 1.5
        shape(slide, MSO_SHAPE.OVAL, cx - 0.3, 1.75, 0.6, 0.6, NAVY if index < 3 else BLUE, WHITE, line_w=2)
        text_box(slide, str(index + 1), cx - 0.3, 1.75, 0.6, 0.6, 18, WHITE, True, HEAD_FONT, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
        text_box(slide, step, cx - 0.7, 2.5, 1.4, 0.8, 12, NAVY, True, align=PP_ALIGN.CENTER)
    card(slide, 0.5, 3.6, 9.0, 1.4)
    heading(slide, "Security boundary", 0.75, 3.72, 4)
    text_box(slide, "Synthetic data only. Demo identity is not production authentication, and the upload endpoint is not role-gated. Extraction needs the OpenAI API and has no offline fallback.", 0.75, 4.1, 8.5, 0.8, 13)

    # 9. Evaluation (numbers come from evals/results/latest.json)
    slide = new_slide(prs, state, "Testing and evidence", "We measure the model, not just the demo",
                      notes="7:45-9:45. Lead with the iteration story: baseline, what was classified as wrong, what changed, new number. Then failure handling: the office-network block, how it was detected (APIConnectionError, 0/8), recovery, and the bounded runtime retry added after testing. Also mention malformed PDFs now return a controlled 422. Token line: gpt-4o-mini, bounded input, per-call latency and token telemetry; quote measured tokens per case from the iteration log.")
    field_accuracy = f"{evaluation['field_accuracy']:.1%}" if evaluation["field_accuracy"] is not None else "N/A"
    risk_agreement = f"{evaluation['risk_agreement']:.0%}" if evaluation["risk_agreement"] is not None else "N/A"
    latency = f"{evaluation['mean_latency_ms'] / 1000:.1f} s" if evaluation["mean_latency_ms"] is not None else "N/A"
    tiles = [(f"{evaluation['successful_count']}/{evaluation['case_count']}", "live calls succeeded"),
             (field_accuracy, f"field accuracy ({evaluation['correct_fields']}/{evaluation['total_fields']})"),
             (risk_agreement, "risk-level agreement"), (latency, "mean latency per case")]
    for index, (value, label) in enumerate(tiles):
        x = 0.5 + index * 2.28
        fill = BLUE if index % 2 else NAVY
        rrect(slide, x, 1.4, 2.1, 1.0, fill)
        text_box(slide, value, x, 1.45, 2.1, 0.55, 26, WHITE, True, HEAD_FONT, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
        text_box(slide, label, x, 1.98, 2.1, 0.3, 11, ICE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    rows = per_case_accuracy()
    if rows:
        chart_data = CategoryChartData()
        chart_data.categories = [case for case, _ in rows]
        chart_data.add_series("Field accuracy (%)", [value for _, value in rows])
        frame = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, _emu(0.5), _emu(2.55), _emu(4.9), _emu(2.55), chart_data)
        style_chart(frame.chart, "Field accuracy by synthetic case (%)", 100)
        series = frame.chart.plots[0].series[0]
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = BLUE
    else:
        card(slide, 0.5, 2.55, 4.9, 2.55)
        heading(slide, "No successful extraction cases", 0.8, 2.85, 4.2)
        text_box(slide, "The latest evaluation could not measure field accuracy. Show the recorded provider errors and rerun when the model endpoint is reachable.", 0.8, 3.35, 4.2, 1.2, 14)
    card(slide, 5.6, 2.55, 3.9, 2.55)
    heading(slide, "Failure handled, and how to read this", 5.8, 2.65, 3.6)
    bullet_box(slide, [
        "Office-network incident: 0/8; recovered on an unblocked network. Runtime now retries transient provider failures up to three times",
        "Risk agreement comes from the deterministic scorer; it does not prove every field is right",
        f"Eight synthetic cases, not a production accuracy estimate. pytest: {test_result}",
    ], 5.8, 3.05, 3.55, 2.0, 11)

    # 10. Close
    slide = new_slide(prs, state, "Deployment and next steps", "Prototype-ready, with an honest path to production", dark=True,
                      notes="9:45-10:00. Close on the tagline, then stop on time. Leave the five minutes of Q&A for the decisions: why deterministic scoring, why no multi-agent orchestration, why field accuracy and risk agreement differ.")
    columns = [
        ("Current demo", ["Docker Compose", "SQLite named volume", "Synthetic data only", "OpenAI key for extraction"]),
        ("Free-first target", ["Ollama adapter", "PostgreSQL and MinIO", "Redis worker", "Prometheus and Grafana"]),
        ("Production gate", ["Real identity and authorization", "TLS and secrets manager", "Migrations and backups", "Alerts and rollback"]),
    ]
    for index, (name, items) in enumerate(columns):
        x = 0.5 + index * 3.075
        card(slide, x, 1.55, 2.85, 2.35, dark=True)
        heading(slide, name, x + 0.25, 1.68, 2.4, dark=True)
        bullet_box(slide, items, x + 0.25, 2.15, 2.4, 1.65, 13, WHITE)
    text_box(slide, "Prepare evidence. Preserve disagreement. Keep humans accountable.", 0.5, 4.2, 9, 0.6, 22, WHITE, True, HEAD_FONT, anchor=MSO_ANCHOR.MIDDLE)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build_deck()
