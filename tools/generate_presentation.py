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

NAVY = RGBColor(15, 28, 42)
NAVY_2 = RGBColor(24, 43, 61)
TEAL = RGBColor(47, 174, 164)
ORANGE = RGBColor(244, 151, 76)
WHITE = RGBColor(244, 247, 248)
MUTED = RGBColor(170, 188, 198)
RED = RGBColor(224, 102, 92)
GREEN = RGBColor(105, 196, 139)


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


def text_box(slide, text, x, y, w, h, size=18, color=WHITE, bold=False, font="Aptos", align=PP_ALIGN.LEFT):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = Inches(0.04)
    frame.margin_right = Inches(0.04)
    frame.margin_top = Inches(0.02)
    frame.vertical_anchor = MSO_ANCHOR.TOP
    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    run = paragraph.add_run()
    run.text = text
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return shape


def rich_text_box(slide, lines, x, y, w, h, size=16, color=WHITE, bullet=True):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = Inches(0.05)
    frame.margin_right = Inches(0.05)
    for index, line in enumerate(lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.level = 0
        paragraph.font.name = "Aptos"
        paragraph.font.size = Pt(size)
        paragraph.font.color.rgb = color
        paragraph.space_after = Pt(9)
        if bullet:
            paragraph.text = f"•  {line}"
    return shape


def rect(slide, x, y, w, h, fill, radius=False, line=None):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line or fill
    return shape


def base(slide, number, section):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = NAVY
    rect(slide, 0, 0, 13.333, 0.08, TEAL)
    text_box(slide, f"GENIUS HACKS 2026  /  {section.upper()}", 0.55, 0.28, 8, 0.25, 9, MUTED, True)
    text_box(slide, f"{number:02d}", 12.15, 7.08, 0.55, 0.25, 10, MUTED, True, align=PP_ALIGN.RIGHT)


def title(slide, heading, kicker=None):
    if kicker:
        text_box(slide, kicker.upper(), 0.65, 0.9, 8, 0.3, 11, ORANGE, True)
    text_box(slide, heading, 0.62, 1.22, 11.7, 0.7, 30, WHITE, True)


def card(slide, heading, body, x, y, w, h, accent=TEAL, body_size=15):
    rect(slide, x, y, w, h, NAVY_2, True, NAVY_2)
    rect(slide, x, y, 0.08, h, accent)
    text_box(slide, heading, x + 0.25, y + 0.2, w - 0.45, 0.35, 16, WHITE, True)
    if isinstance(body, list):
        rich_text_box(slide, body, x + 0.25, y + 0.68, w - 0.45, h - 0.82, body_size, MUTED)
    else:
        text_box(slide, body, x + 0.25, y + 0.68, w - 0.45, h - 0.82, body_size, MUTED)


def add_flow(slide, labels, y=3.0):
    x = 0.7
    width = 1.72
    for index, label in enumerate(labels):
        fill = TEAL if index in (1, 4) else NAVY_2
        rect(slide, x, y, width, 0.82, fill, True)
        text_box(slide, label, x + 0.1, y + 0.2, width - 0.2, 0.4, 13, NAVY if fill == TEAL else WHITE, True, align=PP_ALIGN.CENTER)
        if index < len(labels) - 1:
            text_box(slide, "→", x + width + 0.04, y + 0.22, 0.36, 0.3, 20, ORANGE, True, align=PP_ALIGN.CENTER)
        x += 2.08


def add_slide(prs, number, section, heading, kicker=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    base(slide, number, section)
    title(slide, heading, kicker)
    return slide


def build_deck():
    evaluation = evaluation_summary()
    test_result = pytest_result()
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = NAVY
    rect(slide, 0, 0, 13.333, 0.12, TEAL)
    rect(slide, 8.85, 0.12, 4.48, 7.38, NAVY_2)
    text_box(slide, "GENIUS HACKS 2026", 0.78, 1.1, 5.8, 0.35, 14, ORANGE, True)
    text_box(slide, "Risk Assessment\nWorkbench", 0.75, 1.65, 7.4, 1.55, 38, WHITE, True)
    text_box(slide, "From an unstructured change request to a governed, reviewable risk decision.", 0.8, 3.55, 6.8, 0.8, 20, MUTED)
    text_box(slide, "A synthetic-data vertical slice for FCRM", 0.8, 6.55, 5.5, 0.3, 13, TEAL, True)
    rect(slide, 9.45, 1.15, 2.9, 0.1, ORANGE)
    text_box(slide, "PREPARE\nEVIDENCE\nKEEP HUMANS\nACCOUNTABLE", 9.45, 1.55, 2.9, 2.2, 23, WHITE, True)
    text_box(slide, "28 September 2026", 9.45, 6.55, 2.9, 0.3, 12, MUTED)

    slide = add_slide(prs, 2, "Problem", "The process is slow, variable, and hard to reconstruct", "The problem")
    card(slide, "Today", ["Email, Word, Excel, SharePoint", "15–20 business days per assessment", "Different analysts can reach different conclusions"], 0.7, 2.25, 3.8, 3.3, RED)
    card(slide, "Examiner question", ["Why was this change rated this way?", "Evidence is scattered", "Reconstruction is slow and incomplete"], 4.78, 2.25, 3.8, 3.3, ORANGE)
    card(slide, "Our response", ["One governed case record", "AI structures evidence", "Humans own the decision"], 8.86, 2.25, 3.8, 3.3, TEAL)

    slide = add_slide(prs, 3, "Product", "One case, one traceable path to decision", "Expanded product definition")
    add_flow(slide, ["Submitted", "Extracted", "Analyst review", "Finalized", "Committee", "Decisioned"], 2.45)
    card(slide, "Product owner", "Signs in with a demo role and submits the source document.", 0.8, 4.25, 3.75, 1.45, ORANGE, 14)
    card(slide, "FCRM analyst", "Verifies facts, edits the draft, owns the assessment, and records rationale.", 4.8, 4.25, 3.75, 1.45, TEAL, 14)
    card(slide, "Risk committee", "Reviews escalated cases and records a vote with rationale.", 8.8, 4.25, 3.75, 1.45, GREEN, 14)

    slide = add_slide(prs, 4, "Architecture", "A deliberately narrow AI boundary", "What we built")
    add_flow(slide, ["PDF", "pypdf", "LLM JSON", "Rules", "SQLite", "Review"], 2.45)
    text_box(slide, "Probabilistic", 1.15, 3.72, 3.2, 0.3, 13, ORANGE, True, align=PP_ALIGN.CENTER)
    text_box(slide, "Deterministic", 6.1, 3.72, 3.2, 0.3, 13, TEAL, True, align=PP_ALIGN.CENTER)
    card(slide, "AI does", ["Extract structure from unstructured text", "Identify stated risk factors", "Attempt semantic policy retrieval when configured"], 0.85, 4.25, 5.45, 1.7, ORANGE, 14)
    card(slide, "Code does", ["Validate schemas", "Calculate scores and thresholds", "Persist workflow events; policy lookup falls back to rules"], 7.0, 4.25, 5.45, 1.7, TEAL, 14)

    slide = add_slide(prs, 5, "Harness", "The document is data, not authority", "AI harness and context")
    card(slide, "Context boundary", ["Source text is explicitly untrusted", "Embedded instructions cannot approve a case", "The prompt requires faithful extraction"], 0.8, 2.1, 3.8, 3.5, ORANGE)
    card(slide, "Structured contract", ["Pydantic schema at the model boundary", "Malformed output fails loudly", "Extraction versions remain reconstructable"], 4.78, 2.1, 3.8, 3.5, TEAL)
    card(slide, "Traceable context", ["Synthetic policy IDs and source paths", "Prompt version telemetry", "Analyst can disagree with rationale"], 8.76, 2.1, 3.8, 3.5, GREEN)

    slide = add_slide(prs, 6, "Governance", "The system prepares; people decide", "Human-in-the-loop")
    add_flow(slide, ["Draft", "Edit", "Finalize", "Committee", "Decision"], 2.45)
    card(slide, "Analyst gate", ["Accept or reject", "Edit and rescore", "Rationale required; demo identity"], 0.8, 4.1, 3.75, 1.65, TEAL, 14)
    card(slide, "Committee rule", ["Three distinct votes required", "Approve / reject / conditions", "Two approvals approve; otherwise reject"], 4.8, 4.1, 3.75, 1.65, ORANGE, 14)
    card(slide, "Audit evidence", ["UTC timestamps", "Application-level append-only events", "Original and edited extraction versions"], 8.8, 4.1, 3.75, 1.65, GREEN, 14)
    text_box(slide, "Prototype only: identity and endpoint authorization are incomplete; the voting rule is not approved institutional policy; storage is not tamper-proof.", 0.7, 6.25, 12.0, 0.42, 11, MUTED, False, align=PP_ALIGN.CENTER)

    slide = add_slide(prs, 7, "Risk", "Scoring is explainable by construction", "Engineering judgement")
    categories = [("Customer + geography", "35%", TEAL), ("Product + channel", "30%", ORANGE), ("Third party", "20%", GREEN), ("Complexity", "15%", MUTED)]
    y = 2.1
    for label, value, color in categories:
        text_box(slide, label, 1.0, y, 2.7, 0.3, 15, WHITE, True)
        rect(slide, 3.8, y + 0.03, float(value[:-1]) / 10, 0.28, color, True)
        text_box(slide, value, 7.6, y, 0.8, 0.3, 15, color, True)
        y += 0.7
    card(slide, "Why not an LLM score?", "A committee must reproduce, challenge, and test the number. The model structures evidence; deterministic Python combines category scores.", 8.7, 2.05, 3.7, 2.5, TEAL, 15)
    card(slide, "Grounding", "Weights and synthetic policy material are not approved supervisory mappings. Control effectiveness and residual risk are not modeled.", 8.7, 4.85, 3.7, 1.45, ORANGE, 13)

    slide = add_slide(prs, 8, "Evaluation", "We measure the model, not just the demo", "Testing and evidence")
    field_accuracy = f"{evaluation['field_accuracy']:.1%}" if evaluation["field_accuracy"] is not None else "N/A"
    risk_agreement = f"{evaluation['risk_agreement']:.0%}" if evaluation["risk_agreement"] is not None else "N/A"
    successful = f"{evaluation['successful_count']}/{evaluation['case_count']}"
    text_box(slide, str(evaluation["case_count"]), 0.95, 2.05, 1.2, 0.8, 42, TEAL, True, align=PP_ALIGN.CENTER)
    text_box(slide, "synthetic cases", 0.65, 2.95, 2.0, 0.3, 14, MUTED, True, align=PP_ALIGN.CENTER)
    text_box(slide, successful, 3.45, 2.05, 2.1, 0.8, 36, ORANGE, True, align=PP_ALIGN.CENTER)
    text_box(slide, "live calls succeeded", 3.1, 2.95, 2.8, 0.3, 14, MUTED, True, align=PP_ALIGN.CENTER)
    text_box(slide, field_accuracy, 6.45, 2.05, 2.1, 0.8, 36, GREEN, True, align=PP_ALIGN.CENTER)
    text_box(slide, f"field accuracy ({evaluation['correct_fields']}/{evaluation['total_fields']})", 6.0, 2.95, 3.0, 0.3, 13, MUTED, True, align=PP_ALIGN.CENTER)
    text_box(slide, risk_agreement, 9.55, 2.05, 1.8, 0.8, 36, TEAL, True, align=PP_ALIGN.CENTER)
    text_box(slide, "risk-level agreement", 9.1, 2.95, 2.8, 0.3, 14, MUTED, True, align=PP_ALIGN.CENTER)
    latency = f"Mean latency: {evaluation['mean_latency_ms']:,} ms" if evaluation["mean_latency_ms"] is not None else "Mean latency: N/A"
    text_box(slide, f"{latency}  /  pytest: {test_result}", 2.0, 3.45, 9.3, 0.3, 13, WHITE, True, align=PP_ALIGN.CENTER)
    card(slide, "Interpretation", ["Eight synthetic cases; not a production accuracy estimate", "Perfect score agreement does not mean extraction fields were all correct", "Field-level errors remain visible for prompt iteration"], 2.3, 4.15, 8.7, 1.45, ORANGE, 14)

    slide = add_slide(prs, 9, "Six stages", "AI is part of delivery, not only runtime code", "SDLC evidence")
    stages = [("01", "Requirements", "Brief → spec", ORANGE), ("02", "Design", "Options → decision", TEAL), ("03", "Development", "Contract → code", GREEN), ("04", "Testing", "Cases → metrics", ORANGE), ("05", "Deployment", "Image → runbook", TEAL), ("06", "Operations", "Telemetry → feedback", GREEN)]
    x = 0.75
    for number, label, detail, color in stages:
        rect(slide, x, 2.0, 1.9, 2.45, NAVY_2, True)
        text_box(slide, number, x + 0.16, 2.22, 0.55, 0.45, 22, color, True)
        text_box(slide, label, x + 0.16, 2.9, 1.55, 0.45, 14, WHITE, True)
        text_box(slide, detail, x + 0.16, 3.65, 1.55, 0.45, 12, MUTED)
        x += 2.08
    text_box(slide, "Each stage has an AI instruction, a human gate, and a repository artifact.", 1.0, 5.35, 11.3, 0.4, 18, WHITE, True, align=PP_ALIGN.CENTER)

    slide = add_slide(prs, 10, "Deployment", "Free-first locally, credible path to production", "Deployment and operations")
    card(slide, "Current demo", ["Docker Compose", "SQLite named volume", "Synthetic data only", "OpenAI key required for extraction"], 0.8, 2.0, 3.75, 3.2, TEAL)
    card(slide, "Free-first target", ["Ollama adapter", "PostgreSQL", "MinIO", "Redis worker", "Prometheus/Grafana"], 4.8, 2.0, 3.75, 3.2, ORANGE)
    card(slide, "Production gate", ["Real identity + endpoint authorization", "TLS and secrets manager", "Migrations and backups", "Malware scanning", "Alerts and rollback"], 8.8, 2.0, 3.75, 3.2, RED)
    text_box(slide, "The demo is intentionally honest: prototype-ready, not a bank production deployment.", 1.0, 6.0, 11.3, 0.35, 17, MUTED, True, align=PP_ALIGN.CENTER)

    slide = add_slide(prs, 11, "Demo", "One synthetic case, end to end", "Working demonstration")
    steps = ["Sign in: product-owner-1", "Upload sample PDF", "Inspect fields + score", "Switch to analyst-1", "Finalize with rationale", "Three committee votes"]
    y = 1.9
    for index, step in enumerate(steps, start=1):
        rect(slide, 1.25, y, 0.55, 0.55, TEAL if index % 2 else ORANGE, True)
        text_box(slide, str(index), 1.25, y + 0.12, 0.55, 0.25, 15, NAVY, True, align=PP_ALIGN.CENTER)
        text_box(slide, step, 2.05, y + 0.08, 6.6, 0.35, 18, WHITE, True)
        y += 0.72
    card(slide, "Security boundary", "Use only synthetic data. Demo identity is not production authentication, and the upload endpoint is not role-gated. If OpenAI is unavailable, show recorded metrics and tests; extraction has no offline fallback.", 9.0, 2.1, 3.1, 3.3, MUTED, 13)

    slide = add_slide(prs, 12, "Close", "The workbench makes reasoning visible", "What the panel should remember")
    text_box(slide, "Prepare evidence.\nPreserve disagreement.\nKeep humans accountable.", 0.9, 1.7, 6.7, 2.0, 30, WHITE, True)
    card(slide, "Demonstrated", ["AI-assisted extraction", "Deterministic scoring", "Policy evidence", "Versioned review", "Committee decisions", "Synthetic evaluation"], 8.0, 1.65, 4.3, 3.2, TEAL, 14)
    text_box(slide, "Risk Assessment Workbench  /  Genius Hacks 2026", 0.9, 6.35, 7.5, 0.3, 13, MUTED, True)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build_deck()