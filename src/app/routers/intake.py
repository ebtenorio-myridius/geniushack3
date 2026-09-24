import logging

from fastapi import APIRouter, File, Form, Header, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from src.app.models.schemas import AnalystReview, CaseStatus, ExtractedChangeRequest, UserRole
from src.app.services.dependencies import case_store
from src.app.services.llm_service import draft_extraction
from src.app.services.pdf_extraction import PdfExtractionError, extract_text_from_pdf
from src.app.services.risk_scoring import score_change_request
from src.app.services.policy_service import find_policy_evidence
from src.app.services.auth import require_role, validate_demo_login
from src.app.templating import templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intake", tags=["intake"])
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _identity(request: Request) -> tuple[str | None, str | None]:
    return (
        request.headers.get("X-Demo-User") or request.cookies.get("demo_user"),
        request.headers.get("X-Demo-Role") or request.cookies.get("demo_role"),
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/login")
async def login(request: Request, role: UserRole = Form(...), user: str = Form(...)):
    user = user.strip()
    if not validate_demo_login(user, role):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Use analyst-1 for the analyst role or committee-1 for the committee role."},
            status_code=403,
        )
    destination = "/intake/analyst/dashboard/demo" if role == UserRole.analyst else "/intake/committee/dashboard/demo"
    response = RedirectResponse(destination, status_code=303)
    response.set_cookie("demo_user", user, httponly=True, samesite="lax")
    response.set_cookie("demo_role", role.value, httponly=True, samesite="lax")
    return response


@router.post("/logout")
async def logout():
    response = RedirectResponse("/intake/login", status_code=303)
    response.delete_cookie("demo_user")
    response.delete_cookie("demo_role")
    return response


@router.get("", response_class=HTMLResponse)
async def intake_form(request: Request):
    user, role = _identity(request)
    return templates.TemplateResponse(request, "intake.html", {"demo_user": user, "demo_role": role})


def _queue_context(cases):
    return {
        "cases": cases,
        "events_by_case": {case.case_id: case_store.list_events(case.case_id) for case in cases},
    }


def _decision_status_labels(cases):
    labels = {}
    decision_labels = {
        "approve": ("Approved", "approved"),
        "reject": ("Rejected", "rejected"),
        "defer": ("Deferred", "deferred"),
        "approve_with_conditions": ("Approved with conditions", "approved-conditions"),
    }
    for case in cases:
        decision_events = [
            event for event in case_store.list_events(case.case_id)
            if event["event_type"] == CaseStatus.decisioned.value
        ]
        if not decision_events:
            continue
        decision = decision_events[-1]["rationale"].split(":", 1)[0]
        label, css_class = decision_labels.get(decision, (CaseStatus.decisioned.value.replace("_", " "), "decisioned"))
        labels[case.case_id] = {"label": label, "class": css_class}
    return labels


@router.get("/analyst/dashboard/demo", response_class=HTMLResponse)
async def analyst_dashboard(request: Request):
    user, role = _identity(request)
    require_role(UserRole.analyst, user, role)
    cases = case_store.list_cases()
    return templates.TemplateResponse(
        request,
        "analyst_dashboard.html",
        _queue_context(cases) | {
            "decisioned_cases": [case for case in cases if case.status == CaseStatus.decisioned],
            "detail_base": "/intake/analyst/cases",
        },
    )


@router.get("/committee/dashboard/demo", response_class=HTMLResponse)
async def committee_dashboard(request: Request):
    user, role = _identity(request)
    require_role(UserRole.committee, user, role)
    cases = case_store.list_cases((CaseStatus.committee_review,))
    return templates.TemplateResponse(
        request,
        "committee_dashboard.html",
        _queue_context(cases) | {"detail_base": "/intake/committee/cases"},
    )


@router.get("/analyst/decisioned", response_class=HTMLResponse)
async def analyst_decisioned(request: Request):
    user, role = _identity(request)
    require_role(UserRole.analyst, user, role)
    cases = case_store.list_cases((CaseStatus.decisioned,))
    return templates.TemplateResponse(request, "case_list.html", {"title": "Decisioned cases", "role": "analyst", "cases": cases, "detail_base": "/intake/analyst/cases", "status_labels": _decision_status_labels(cases)})


@router.get("/analyst/committee-cases", response_class=HTMLResponse)
async def analyst_committee_cases(request: Request):
    user, role = _identity(request)
    require_role(UserRole.analyst, user, role)
    cases = case_store.list_cases((CaseStatus.committee_review,))
    return templates.TemplateResponse(
        request,
        "case_list.html",
        {"title": "Cases awaiting committee decision", "role": "analyst", "cases": cases, "detail_base": "/intake/analyst/cases"},
    )


@router.get("/committee/decisioned", response_class=HTMLResponse)
async def committee_decisioned(request: Request):
    user, role = _identity(request)
    require_role(UserRole.committee, user, role)
    cases = case_store.list_cases((CaseStatus.decisioned,))
    return templates.TemplateResponse(request, "case_list.html", {"title": "Decisioned cases", "role": "committee", "cases": cases, "detail_base": "/intake/committee/cases", "status_labels": _decision_status_labels(cases)})


@router.get("/committee/cases/{case_id}", response_class=HTMLResponse)
async def committee_case_detail(request: Request, case_id: str):
    user, role = _identity(request)
    require_role(UserRole.committee, user, role)
    case = case_store.get_case(case_id)
    if case is None:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    return templates.TemplateResponse(
        request,
        "committee_case.html",
        {"case": case, "events": case_store.list_events(case_id)},
    )


@router.get("/analyst/cases/{case_id}", response_class=HTMLResponse)
async def analyst_case_detail(request: Request, case_id: str):
    user, role = _identity(request)
    require_role(UserRole.analyst, user, role)
    case = case_store.get_case(case_id)
    if case is None:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    return templates.TemplateResponse(
        request,
        "analyst_case.html",
        {"case": case, "events": case_store.list_events(case_id)},
    )


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
    require_role(UserRole.analyst, demo_user or request.cookies.get("demo_user"), demo_role or request.cookies.get("demo_role"))
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
    require_role(UserRole.analyst, demo_user or request.cookies.get("demo_user"), demo_role or request.cookies.get("demo_role"))
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
        user, role = _identity(request)
        require_role(UserRole.analyst, user, role)
        case = case_store.submit_committee(case_id, actor, rationale)
    except KeyError:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    except ValueError as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)
    return templates.TemplateResponse(request, "partials/review_result.html", {"case": case})


@router.get("/committee-queue", response_class=HTMLResponse)
async def committee_queue(request: Request):
    user, role = _identity(request)
    if role != UserRole.committee.value:
        return templates.TemplateResponse(
            request,
            "partials/committee_access.html",
            {},
            status_code=403,
        )
    cases = case_store.list_committee_cases()
    return templates.TemplateResponse(
        request,
        "partials/committee_queue.html",
        {"cases": cases, "events_by_case": {case.case_id: case_store.list_events(case.case_id) for case in cases}},
    )


@router.get("/committee-queue/demo", response_class=HTMLResponse)
async def demo_committee_queue(request: Request):
    """Browser-friendly local demo entry point for the committee queue."""
    return templates.TemplateResponse(
        request,
        "committee_queue.html",
        {"cases": (cases := case_store.list_committee_cases()), "events_by_case": {case.case_id: case_store.list_events(case.case_id) for case in cases}},
    )


@router.post("/{case_id}/committee/decision", response_class=HTMLResponse)
async def committee_decision(request: Request, case_id: str, decision: str = Form(...), actor: str = Form(...), rationale: str = Form(...), conditions: str = Form("")):
    from src.app.models.schemas import CommitteeDecision, CommitteeReview
    user, role = _identity(request)
    require_role(UserRole.committee, user, role)
    try:
        case = case_store.decide_committee(case_id, CommitteeReview(decision=CommitteeDecision(decision), actor=actor, rationale=rationale, conditions=conditions))
    except (KeyError, ValueError) as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)
    return templates.TemplateResponse(request, "partials/review_result.html", {"case": case})
