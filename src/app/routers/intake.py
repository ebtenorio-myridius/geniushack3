import logging

from fastapi import APIRouter, File, Form, Header, Request, UploadFile
from fastapi.responses import HTMLResponse

from src.app.models.schemas import AnalystReview, CaseStatus, ExtractedChangeRequest, UserRole
from src.app.services.dependencies import case_store
from src.app.services.llm_service import draft_extraction
from src.app.services.pdf_extraction import PdfExtractionError, extract_text_from_pdf
from src.app.services.risk_scoring import score_change_request
from src.app.services.policy_service import find_policy_evidence
from src.app.services.auth import require_role
from src.app.templating import templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intake", tags=["intake"])
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.get("", response_class=HTMLResponse)
async def intake_form(request: Request):
    return templates.TemplateResponse(request, "intake.html", {})


@router.post("/upload", response_class=HTMLResponse)
async def upload_change_request(request: Request, file: UploadFile = File(...)):
    """Handles the PDF upload from the intake form and returns an HTML
    fragment (not a full page) — this is the endpoint HTMX swaps into the
    page, so the person never leaves the intake form while it processes.
    """
    if file.content_type != "application/pdf":
        return templates.TemplateResponse(
            request, "partials/error.html", {"message": "Only PDF documents are accepted."}, status_code=415
        )

    file_bytes = await file.read(_MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > _MAX_UPLOAD_BYTES:
        return templates.TemplateResponse(
            request, "partials/error.html", {"message": "The PDF exceeds the 10 MB upload limit."}, status_code=413
        )

    try:
        raw_text = extract_text_from_pdf(file_bytes)
    except PdfExtractionError as exc:
        return templates.TemplateResponse(
            request, "partials/error.html", {"message": str(exc)}, status_code=422
        )

    try:
        extracted = await draft_extraction(raw_text)
    except Exception:
        logger.exception("LLM extraction failed for %s", file.filename)
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {"message": "The model couldn't produce a valid extraction. Try again, or check the source document."},
            status_code=502,
        )

    assessment = score_change_request(extracted)
    case = case_store.create_case(file.filename or "unnamed.pdf", extracted, assessment, find_policy_evidence(extracted))

    return templates.TemplateResponse(
        request,
        "partials/extraction_result.html",
        {
            "filename": file.filename,
            "case_id": case.case_id,
            "status": case.status,
            "extracted": extracted,
            "assessment": assessment,
            "policy_evidence": case.policy_evidence,
        },
    )


@router.post("/{case_id}/review", response_class=HTMLResponse)
async def review_change_request(
    request: Request,
    case_id: str,
    decision: CaseStatus = Form(...),
    actor: str = Form(...),
    rationale: str = Form(...),
    demo_user: str | None = Header(default=None, alias="X-Demo-User"),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
):
    require_role(UserRole.analyst, demo_user, demo_role)
    try:
        case = case_store.review_case(case_id, AnalystReview(decision=decision, actor=actor, rationale=rationale))
    except KeyError:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    except ValueError as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)

    return templates.TemplateResponse(
        request,
        "partials/review_result.html",
        {"case": case},
    )


@router.post("/{case_id}/edit", response_class=HTMLResponse)
async def edit_change_request(
    request: Request,
    case_id: str,
    change_title: str = Form(...),
    change_type: str = Form(...),
    business_unit: str = Form(...),
    description: str = Form(...),
    geographies_involved: str = Form(""),
    customer_segments_involved: str = Form(""),
    vendor_involved: bool = Form(False),
    vendor_name: str = Form(""),
    products_involved: str = Form(""),
    stated_risk_factors: str = Form(""),
    actor: str = Form(...),
    rationale: str = Form(...),
    demo_user: str | None = Header(default=None, alias="X-Demo-User"),
    demo_role: str | None = Header(default=None, alias="X-Demo-Role"),
):
    require_role(UserRole.analyst, demo_user, demo_role)
    extracted = ExtractedChangeRequest(
        change_title=change_title,
        change_type=change_type,
        business_unit=business_unit,
        description=description,
        geographies_involved=[item.strip() for item in geographies_involved.split(",") if item.strip()],
        customer_segments_involved=[item.strip() for item in customer_segments_involved.split(",") if item.strip()],
        vendor_involved=vendor_involved,
        vendor_name=vendor_name or None,
        products_involved=[item.strip() for item in products_involved.split(",") if item.strip()],
        stated_risk_factors=[item.strip() for item in stated_risk_factors.split(",") if item.strip()],
        extraction_confidence=1.0,
    )
    try:
        case = case_store.update_extraction(case_id, extracted, score_change_request(extracted), actor, rationale, find_policy_evidence(extracted))
    except KeyError:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    except ValueError as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)
    return templates.TemplateResponse(request, "partials/review_result.html", {"case": case})


@router.post("/{case_id}/committee/submit", response_class=HTMLResponse)
async def submit_committee_review(request: Request, case_id: str, actor: str = Form(...), rationale: str = Form(...)):
    try:
        require_role(UserRole.analyst, request.headers.get("X-Demo-User"), request.headers.get("X-Demo-Role"))
        case = case_store.submit_committee(case_id, actor, rationale)
    except KeyError:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    except ValueError as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)
    return templates.TemplateResponse(request, "partials/review_result.html", {"case": case})


@router.get("/committee-queue", response_class=HTMLResponse)
async def committee_queue(request: Request):
    require_role(UserRole.committee, request.headers.get("X-Demo-User"), request.headers.get("X-Demo-Role"))
    return templates.TemplateResponse(request, "partials/committee_queue.html", {"cases": case_store.list_committee_cases()})


@router.post("/{case_id}/committee/decision", response_class=HTMLResponse)
async def committee_decision(request: Request, case_id: str, decision: str = Form(...), actor: str = Form(...), rationale: str = Form(...), conditions: str = Form("")):
    from src.app.models.schemas import CommitteeDecision, CommitteeReview
    require_role(UserRole.committee, request.headers.get("X-Demo-User"), request.headers.get("X-Demo-Role"))
    try:
        case = case_store.decide_committee(case_id, CommitteeReview(decision=CommitteeDecision(decision), actor=actor, rationale=rationale, conditions=conditions))
    except (KeyError, ValueError) as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)
    return templates.TemplateResponse(request, "partials/review_result.html", {"case": case})
