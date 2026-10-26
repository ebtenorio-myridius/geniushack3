import hashlib
import io
import json
import logging
import zipfile
from datetime import date, datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from src.app.models.governance import GovernanceRules
from src.app.models.schemas import (
    AnalystReview,
    CaseRecord,
    CaseStatus,
    CommitteeDecision,
    CommitteeReview,
    EvidenceCitation,
    ExtractedChangeRequest,
    UserRole,
)
from src.app.services.dependencies import case_store
from src.app.services.llm_service import draft_extraction
from src.app.services.pdf_extraction import PdfExtractionError, extract_text_by_page_from_pdf
from src.app.services.risk_scoring import score_change_request
from src.app.services.policy_service import find_policy_evidence
from src.app.services.source_evidence import page_marked_text, validate_extraction_evidence
from src.app.services.auth import require_role, validate_demo_login
from src.app.templating import templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intake", tags=["intake"])
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _identity(request: Request) -> tuple[str | None, str | None]:
    return (
        request.cookies.get("demo_user"),
        request.cookies.get("demo_role"),
    )


def _apply_edit_citations(
    extracted: ExtractedChangeRequest,
    case: CaseRecord,
    citation_lines: str,
) -> None:
    before = case.extracted.model_dump(mode="python")
    after = extracted.model_dump(mode="python")
    changed_fields = {
        field
        for field in after
        if field not in {"evidence", "extraction_confidence"} and after[field] != before[field]
    }
    parsed_citations = []
    for line_number, line in enumerate(citation_lines.splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split("|", 2)
        if len(parts) != 3:
            raise ValueError(f"Citation line {line_number} must use: field_name | page_number | exact quote")
        field_name, page_number_text, quote = (part.strip() for part in parts)
        if field_name not in changed_fields:
            raise ValueError(f"Citation line {line_number} must cite a changed field")
        try:
            page_number = int(page_number_text)
        except ValueError as exc:
            raise ValueError(f"Citation line {line_number} has an invalid page number") from exc
        parsed_citations.append(
            EvidenceCitation(field_name=field_name, page_number=page_number, quote=quote)
        )

    existing_citations = [
        citation
        for citation in case.extracted.evidence
        if citation.field_name not in changed_fields
    ]
    if changed_fields and not case_store.get_source_document(case.case_id):
        raise ValueError("This case has no retained source document; corrected fields cannot be verified.")
    extracted.evidence = existing_citations + parsed_citations
    if case_store.get_source_document(case.case_id):
        pages = [page["page_text"] for page in case_store.list_source_pages(case.case_id)]
        validate_extraction_evidence(extracted, pages)
    elif extracted.evidence:
        raise ValueError("Source pages are unavailable for validating the recorded citations.")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "hide_header_identity": True,
            "selected_role": "",
            "demo_user": "",
        },
    )


@router.post("/login")
async def login(request: Request, role: UserRole = Form(...), user: str = Form(...)):
    user = user.strip()
    if not validate_demo_login(user, role):
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "error": "Use product-owner-1, analyst-1, or committee-1/2/3 for the matching demo role.",
                "hide_header_identity": True,
                "selected_role": role.value,
                "demo_user": user,
            },
            status_code=403,
        )
    destinations = {
        UserRole.product_owner: "/intake/product-owner/dashboard/demo",
        UserRole.analyst: "/intake/analyst/dashboard/demo",
        UserRole.committee: "/intake/committee/dashboard/demo",
    }
    destination = destinations[role]
    response = RedirectResponse(destination, status_code=303)
    response.set_cookie("demo_user", user, httponly=True, samesite="lax")
    response.set_cookie("demo_role", role.value, httponly=True, samesite="lax")
    return response


@router.post("/logout")
async def logout():
    response = RedirectResponse("/intake/login", status_code=303)
    _clear_identity_cookies(response)
    return response


@router.get("/switch-role")
async def switch_role():
    response = RedirectResponse("/intake/login", status_code=303)
    _clear_identity_cookies(response)
    return response


def _clear_identity_cookies(response: RedirectResponse) -> None:
    response.delete_cookie("demo_user")
    response.delete_cookie("demo_role")


@router.get("", response_class=HTMLResponse)
async def intake_form(request: Request):
    user, role = _identity(request)
    try:
        authenticated = bool(user and role and validate_demo_login(user, UserRole(role)))
    except ValueError:
        authenticated = False
    if not authenticated:
        return RedirectResponse("/intake/login")
    return templates.TemplateResponse(request, "intake.html", {"demo_user": user, "demo_role": role})


def _queue_context(cases):
    now = datetime.now(timezone.utc)
    return {
        "cases": cases,
        "events_by_case": {case.case_id: case_store.list_events(case.case_id) for case in cases},
        "age_days_by_case": {
            case.case_id: max(0, (now - case.updated_at.astimezone(timezone.utc)).days)
            for case in cases
        },
    }


def _case_detail_context(case_id: str):
    today = datetime.now(timezone.utc).date().isoformat()
    conditions = case_store.list_conditions(case_id)
    for condition in conditions:
        condition["overdue"] = condition["status"] == "open" and condition["due_date"] < today
    case = case_store.get_case(case_id)
    if case is None:
        raise KeyError(case_id)
    evidence_by_field: dict[str, list[dict]] = {}
    for citation in case.extracted.evidence:
        evidence_by_field.setdefault(citation.field_name, []).append(citation.model_dump())
    return {
        "conditions": conditions,
        "versions": case_store.list_extraction_versions(case_id),
        "evidence_by_field": evidence_by_field,
        "source_document": case_store.get_source_document(case_id),
        "audit_verification": case_store.verify_audit_chain(case_id),
        "cycle_metrics": case_store.cycle_time_metrics(case_id),
        "workflow_rules": (GovernanceRules.model_validate(case.ruleset_snapshot) if case.ruleset_snapshot else case_store.governance_rules).workflow,
    }


@router.get("/product-owner/dashboard/demo", response_class=HTMLResponse)
async def product_owner_dashboard(request: Request):
    user, role = _identity(request)
    require_role(UserRole.product_owner, user, role)
    cases = case_store.list_cases()
    owner_cases = [case for case in cases if case.submitted_by == user]
    return templates.TemplateResponse(
        request,
        "product_owner_dashboard.html",
        _queue_context(owner_cases)
        | {
            "detail_base": "/intake/product-owner/cases",
            "status_labels": _decision_status_labels(owner_cases),
        },
    )


def _decision_status_labels(cases):
    labels = {}
    decision_labels = {
        CommitteeDecision.approve: ("Approved", "approved"),
        CommitteeDecision.reject: ("Rejected", "rejected"),
        CommitteeDecision.defer: ("Deferred", "deferred"),
        CommitteeDecision.approve_with_conditions: ("Approved with conditions", "approved-conditions"),
    }
    pending_status_labels = {
        CaseStatus.draft: ("Draft", "pending"),
        CaseStatus.analyst_review: ("Pending analyst review", "pending"),
        CaseStatus.needs_information: ("Information requested", "pending"),
        CaseStatus.analyst_finalized: ("Pending committee submission", "pending"),
        CaseStatus.committee_review: ("Pending committee decision", "pending"),
    }
    for case in cases:
        decision = case.decision
        if decision is None and case.status in (CaseStatus.decisioned, CaseStatus.conditions_pending, CaseStatus.closed):
            decision_events = [
                event for event in case_store.list_events(case.case_id)
                if event["event_type"] == CaseStatus.decisioned.value
            ]
            if decision_events:
                decision_value = decision_events[-1]["rationale"].split(":", 1)[0]
                decision = next((item for item in decision_labels if item.value == decision_value), None)
        if decision is not None:
            label, css_class = decision_labels[decision]
            if case.status == CaseStatus.conditions_pending:
                label = f"{label} (conditions pending)"
            elif case.status == CaseStatus.closed:
                label = f"{label} (closed)"
        elif case.status == CaseStatus.conditions_pending:
            label, css_class = "Conditions pending", "pending"
        elif case.status in (CaseStatus.decisioned, CaseStatus.closed):
            label, css_class = "Decision recorded", "decisioned"
        else:
            label, css_class = pending_status_labels.get(
                case.status,
                (case.status.value.replace("_", " ").capitalize(), "pending"),
            )
        labels[case.case_id] = {"label": label, "class": css_class}
    return labels


@router.get("/analyst/dashboard/demo", response_class=HTMLResponse)
async def analyst_dashboard(request: Request):
    user, role = _identity(request)
    require_role(UserRole.analyst, user, role)
    cases = case_store.list_cases((CaseStatus.analyst_review, CaseStatus.needs_information))
    return templates.TemplateResponse(
        request,
        "analyst_dashboard.html",
        _queue_context(cases) | {"detail_base": "/intake/analyst/cases"},
    )


@router.get("/analyst/metrics", response_class=HTMLResponse)
async def analyst_cycle_time_metrics(request: Request):
    user, role = _identity(request)
    require_role(UserRole.analyst, user, role)
    return templates.TemplateResponse(
        request,
        "cycle_time_metrics.html",
        {"report": case_store.cycle_time_report(), "demo_user": user},
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
    cases = case_store.list_cases((CaseStatus.decisioned, CaseStatus.conditions_pending, CaseStatus.closed))
    return templates.TemplateResponse(request, "case_list.html", _queue_context(cases) | {"title": "Decisioned cases", "role": "analyst", "detail_base": "/intake/analyst/cases", "status_labels": _decision_status_labels(cases)})


@router.get("/analyst/committee-cases", response_class=HTMLResponse)
async def analyst_committee_cases(request: Request):
    user, role = _identity(request)
    require_role(UserRole.analyst, user, role)
    cases = case_store.list_cases((CaseStatus.committee_review,))
    return templates.TemplateResponse(
        request,
        "case_list.html",
        _queue_context(cases) | {"title": "Cases awaiting committee decision", "role": "analyst", "detail_base": "/intake/analyst/cases"},
    )


@router.get("/committee/decisioned", response_class=HTMLResponse)
async def committee_decisioned(request: Request):
    user, role = _identity(request)
    require_role(UserRole.committee, user, role)
    cases = case_store.list_cases((CaseStatus.decisioned, CaseStatus.conditions_pending, CaseStatus.closed))
    return templates.TemplateResponse(request, "case_list.html", _queue_context(cases) | {"title": "Decisioned cases", "role": "committee", "detail_base": "/intake/committee/cases", "status_labels": _decision_status_labels(cases)})


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
        {"case": case, "events": case_store.list_events(case_id), "vote_summary": case_store.committee_vote_summary(case_id), "demo_user": user} | _case_detail_context(case_id),
    )


@router.get("/product-owner/cases/{case_id}", response_class=HTMLResponse)
async def product_owner_case_detail(request: Request, case_id: str):
    user, role = _identity(request)
    require_role(UserRole.product_owner, user, role)
    case = case_store.get_case(case_id)
    if case is None or case.submitted_by != user:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    return templates.TemplateResponse(
        request,
        "product_owner_case.html",
        {"case": case, "events": case_store.list_events(case_id), "demo_user": user} | _case_detail_context(case_id),
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
        {"case": case, "events": case_store.list_events(case_id), "demo_user": user, "vote_summary": case_store.committee_vote_summary(case_id)} | _case_detail_context(case_id),
    )


@router.get("/{case_id}/source-document")
async def source_document_download(request: Request, case_id: str):
    user, role = _identity(request)
    case = case_store.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    if role == UserRole.product_owner.value:
        require_role(UserRole.product_owner, user, role)
        if case.submitted_by != user:
            raise HTTPException(status_code=404, detail="Case not found.")
    elif role == UserRole.analyst.value:
        require_role(UserRole.analyst, user, role)
    elif role == UserRole.committee.value:
        require_role(UserRole.committee, user, role)
    else:
        raise HTTPException(status_code=403, detail="A signed-in workflow role is required.")
    audit = case_store.verify_audit_chain(case_id)
    if not audit["valid"]:
        raise HTTPException(
            status_code=409,
            detail=audit.get("error") or f"Audit chain verification failed at event {audit['first_invalid_event_id']}.",
        )
    try:
        _, content = case_store.read_source_document(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="No retained source document is available.") from exc
    except (OSError, ValueError) as exc:
        logger.exception("Source document integrity/read failure for %s", case_id)
        raise HTTPException(status_code=409, detail="The retained source document could not be verified.") from exc
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{case_id}-source.pdf"'},
    )


@router.get("/{case_id}/examiner-export")
async def examiner_export(request: Request, case_id: str):
    user, role = _identity(request)
    if role == UserRole.analyst.value:
        require_role(UserRole.analyst, user, role)
    elif role == UserRole.committee.value:
        require_role(UserRole.committee, user, role)
    else:
        raise HTTPException(status_code=403, detail="Analyst or committee role required.")

    case = case_store.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    audit = case_store.verify_audit_chain(case_id)
    if not audit["valid"]:
        raise HTTPException(
            status_code=409,
            detail=audit.get("error") or f"Audit chain verification failed at event {audit['first_invalid_event_id']}.",
        )

    source_metadata = case_store.get_source_document(case_id)
    source_bytes = None
    if source_metadata:
        try:
            source_metadata, source_bytes = case_store.read_source_document(case_id)
        except KeyError as exc:
            raise HTTPException(status_code=409, detail="The retained source document record is missing.") from exc
        except (OSError, ValueError) as exc:
            logger.exception("Cannot create export due to source-document integrity failure for %s", case_id)
            raise HTTPException(status_code=409, detail="The retained source document could not be verified.") from exc

    record = {
        "package_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "guarantee": "Local prototype export; not immutable or examiner-certified.",
        "case": case.model_dump(mode="json"),
        "source_document": {
            key: source_metadata[key]
            for key in ("filename", "sha256", "byte_length", "uploaded_at")
        } if source_metadata else None,
        "source_pages": case_store.list_source_pages(case_id),
        "extraction_versions": case_store.list_extraction_versions(case_id),
        "workflow_events": case_store.list_events(case_id),
        "committee_votes": case_store.list_committee_votes(case_id),
        "conditions": case_store.list_conditions(case_id),
        "cycle_time": case_store.cycle_time_metrics(case_id),
        "audit_verification": audit,
        "governance_rules_snapshot": case.ruleset_snapshot,
        "limitations": [
            "Demo-cookie identities are not independently verified.",
            "A local database owner can rewrite the event chain and recompute its hashes.",
            "Preserve this export and its manifest outside the app to establish an independent reference point.",
        ],
    }
    record_bytes = json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")
    files = {"case-record.json": record_bytes}
    if source_bytes is not None:
        files["source-document.pdf"] = source_bytes
    manifest = {
        "case_id": case_id,
        "files": {
            name: {"sha256": hashlib.sha256(content).hexdigest(), "byte_length": len(content)}
            for name, content in files.items()
        },
        "audit_chain_head": audit["chain_head"],
        "audit_events_checked": audit["events_checked"],
    }

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, content in files.items():
            bundle.writestr(name, content)
        bundle.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
    return Response(
        content=archive.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{case_id}-examiner-export.zip"'},
    )


@router.post("/upload", response_class=HTMLResponse)
async def upload_change_request(request: Request, file: UploadFile = File(...)):
    """Handles the PDF upload from the intake form and returns an HTML
    fragment (not a full page) — this is the endpoint HTMX swaps into the
    page, so the person never leaves the intake form while it processes.
    """
    user, role = _identity(request)
    owner = require_role(UserRole.product_owner, user, role)
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
        source_pages = extract_text_by_page_from_pdf(file_bytes)
    except PdfExtractionError as exc:
        return templates.TemplateResponse(
            request, "partials/error.html", {"message": str(exc)}, status_code=422
        )

    try:
        extracted = await draft_extraction(page_marked_text(source_pages))
    except Exception:
        logger.exception("LLM extraction failed for %s", file.filename)
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {"message": "The model couldn't produce a valid extraction. Try again, or check the source document."},
            status_code=502,
        )

    try:
        validate_extraction_evidence(extracted, source_pages)
    except ValueError as exc:
        logger.warning("Extraction citations failed validation for %s: %s", file.filename, exc)
        return templates.TemplateResponse(
            request,
            "partials/error.html",
            {"message": f"The extraction did not include verifiable source citations: {exc}"},
            status_code=422,
        )

    assessment = score_change_request(extracted)
    case = case_store.create_case(
        file.filename or "unnamed.pdf",
        extracted,
        assessment,
        find_policy_evidence(extracted),
        submitted_by=owner,
        source_document_bytes=file_bytes,
        source_pages=source_pages,
    )

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
            "submitted_by": case.submitted_by,
            "source_document": case_store.get_source_document(case.case_id),
        },
    )


@router.post("/{case_id}/review", response_class=HTMLResponse)
async def review_change_request(
    request: Request,
    case_id: str,
    decision: CaseStatus = Form(...),
    rationale: str = Form(...),
):
    analyst_actor = require_role(
        UserRole.analyst,
        request.cookies.get("demo_user"),
        request.cookies.get("demo_role"),
    )
    try:
        case = case_store.get_case(case_id)
        if case is None:
            raise KeyError(case_id)
        if case.status != CaseStatus.analyst_review:
            raise ValueError("Only submitted cases in analyst review can be finalized")
        case = case_store.review_case(case_id, AnalystReview(decision=decision, actor=analyst_actor, rationale=rationale))
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
    source_citations: str = Form(""),
    rationale: str = Form(...),
):
    analyst = require_role(UserRole.analyst, request.cookies.get("demo_user"), request.cookies.get("demo_role"))
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
        case_before_edit = case_store.get_case(case_id)
        if case_before_edit is None:
            raise KeyError(case_id)
        if case_before_edit.status != CaseStatus.analyst_review:
            raise ValueError("Only submitted cases in analyst review can be edited")
        _apply_edit_citations(extracted, case_before_edit, source_citations)
        rules = case_before_edit.assessment.ruleset_snapshot
        governance = GovernanceRules.model_validate(rules) if rules else None
        case = case_store.update_extraction(
            case_id,
            extracted,
            score_change_request(extracted, governance),
            analyst,
            rationale,
            find_policy_evidence(extracted),
        )
    except KeyError:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    except ValueError as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)
    response = templates.TemplateResponse(request, "partials/review_result.html", {"case": case})
    response.headers["HX-Refresh"] = "true"
    return response


@router.post("/{case_id}/committee/submit", response_class=HTMLResponse)
async def submit_committee_review(request: Request, case_id: str, rationale: str = Form(...)):
    try:
        user, role = _identity(request)
        verified_actor = require_role(UserRole.analyst, user, role)
        case = case_store.submit_committee(case_id, verified_actor, rationale)
    except KeyError:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    except ValueError as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)
    return templates.TemplateResponse(request, "partials/review_result.html", {"case": case})


@router.get("/committee-queue", response_class=HTMLResponse)
async def committee_queue(request: Request):
    user, role = _identity(request)
    require_role(UserRole.committee, user, role)
    cases = case_store.list_committee_cases()
    return templates.TemplateResponse(
        request,
        "partials/committee_queue.html",
        _queue_context(cases) | {"vote_summary_by_case": {case.case_id: case_store.committee_vote_summary(case.case_id) for case in cases}},
    )


@router.get("/committee-queue/demo", response_class=HTMLResponse)
async def demo_committee_queue(request: Request):
    """Browser-friendly local demo entry point for the committee queue."""
    user, role = _identity(request)
    require_role(UserRole.committee, user, role)
    cases = case_store.list_committee_cases()
    return templates.TemplateResponse(
        request,
        "committee_queue.html",
        _queue_context(cases) | {"vote_summary_by_case": {case.case_id: case_store.committee_vote_summary(case.case_id) for case in cases}},
    )


@router.post("/{case_id}/committee/decision", response_class=HTMLResponse)
async def committee_decision(
    request: Request,
    case_id: str,
    decision: str = Form(...),
    rationale: str = Form(...),
    conditions: str = Form(""),
    conditions_owner: str = Form(""),
    conditions_due_date: str = Form(""),
):
    user, role = _identity(request)
    actor = require_role(UserRole.committee, user, role)
    try:
        due_date = date.fromisoformat(conditions_due_date) if conditions_due_date else None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Condition due date must be a valid date.") from exc
    try:
        case = case_store.cast_committee_vote(
            case_id,
            CommitteeReview(
                decision=CommitteeDecision(decision),
                actor=actor,
                rationale=rationale,
                conditions=conditions,
                conditions_owner=conditions_owner,
                conditions_due_date=due_date,
            ),
        )
    except (KeyError, ValueError) as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)
    return templates.TemplateResponse(request, "partials/review_result.html", {"case": case})


@router.post("/{case_id}/submit", response_class=HTMLResponse)
async def submit_change_request(request: Request, case_id: str):
    user, role = _identity(request)
    actor = require_role(UserRole.product_owner, user, role)
    try:
        case = case_store.get_case(case_id)
        if case is None:
            raise KeyError(case_id)
        if case.submitted_by != actor:
            raise ValueError("Only the submitting product owner can submit this case")
        case = case_store.submit_case(case_id, actor)
    except KeyError:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    except ValueError as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)
    return templates.TemplateResponse(request, "partials/review_result.html", {"case": case})


@router.post("/{case_id}/draft/edit", response_class=HTMLResponse)
async def edit_product_owner_draft(
    request: Request,
    case_id: str,
    change_title: str = Form(...),
    business_unit: str = Form(...),
    description: str = Form(...),
    source_citations: str = Form(""),
    rationale: str = Form(...),
):
    user, role = _identity(request)
    actor = require_role(UserRole.product_owner, user, role)
    try:
        case = case_store.get_case(case_id)
        if case is None:
            raise KeyError(case_id)
        if case.submitted_by != actor:
            raise ValueError("Only the submitting product owner can edit this draft")
        extracted = ExtractedChangeRequest(
            **(case.extracted.model_dump() | {
                "change_title": change_title,
                "business_unit": business_unit,
                "description": description,
            })
        )
        _apply_edit_citations(extracted, case, source_citations)
        rules = case.assessment.ruleset_snapshot
        governance = GovernanceRules.model_validate(rules) if rules else None
        case = case_store.update_draft(
            case_id,
            extracted,
            score_change_request(extracted, governance),
            actor,
            rationale,
            find_policy_evidence(extracted),
        )
    except KeyError:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    except ValueError as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)
    return templates.TemplateResponse(request, "partials/review_result.html", {"case": case})


@router.post("/{case_id}/request-information", response_class=HTMLResponse)
async def request_case_information(request: Request, case_id: str, rationale: str = Form(...)):
    user, role = _identity(request)
    if role == UserRole.analyst.value:
        actor = require_role(UserRole.analyst, user, role)
    elif role == UserRole.committee.value:
        actor = require_role(UserRole.committee, user, role)
    else:
        raise HTTPException(status_code=403, detail="Analyst or committee role required")
    try:
        case = case_store.request_information(case_id, actor, rationale)
    except KeyError:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    except ValueError as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)
    return templates.TemplateResponse(request, "partials/review_result.html", {"case": case})


@router.post("/{case_id}/information-response", response_class=HTMLResponse)
async def respond_to_case_information(request: Request, case_id: str, response: str = Form(...)):
    user, role = _identity(request)
    actor = require_role(UserRole.product_owner, user, role)
    try:
        case = case_store.respond_to_information(case_id, actor, response)
    except KeyError:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    except ValueError as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)
    return templates.TemplateResponse(request, "partials/review_result.html", {"case": case})


@router.post("/{case_id}/conditions/{condition_id}/complete", response_class=HTMLResponse)
async def complete_case_condition(request: Request, case_id: str, condition_id: int, evidence: str = Form(...)):
    user, role = _identity(request)
    actor = require_role(UserRole.product_owner, user, role)
    try:
        case = case_store.complete_condition(case_id, condition_id, actor, evidence)
    except KeyError:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    except ValueError as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)
    return templates.TemplateResponse(request, "partials/review_result.html", {"case": case})


@router.post("/{case_id}/close", response_class=HTMLResponse)
async def close_case(request: Request, case_id: str, rationale: str = Form(...)):
    user, role = _identity(request)
    actor = require_role(UserRole.analyst, user, role)
    try:
        case = case_store.close_case(case_id, actor, rationale)
    except KeyError:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    except ValueError as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)
    return templates.TemplateResponse(request, "partials/review_result.html", {"case": case})


@router.post("/{case_id}/reassess", response_class=HTMLResponse)
async def reassess_case(request: Request, case_id: str):
    user, role = _identity(request)
    actor = require_role(UserRole.analyst, user, role)
    try:
        case = case_store.create_reassessment(case_id, actor)
    except KeyError:
        return templates.TemplateResponse(request, "partials/error.html", {"message": "Case not found."}, status_code=404)
    except ValueError as exc:
        return templates.TemplateResponse(request, "partials/error.html", {"message": str(exc)}, status_code=409)
    return templates.TemplateResponse(request, "partials/reassessment_result.html", {"case": case})
