from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from infrai_pdf import InfraiError, InfraiPdfClient
from onboarding_policy import AccountStatus, decide_account_status


class TenantOnboardingRequest(BaseModel):
    onboarding_id: str = Field(min_length=1)
    tenant_name: str = Field(min_length=1)
    admin_email: str = Field(min_length=3)
    pdf: str = Field(min_length=1)
    lang: str | None = None


class TenantOnboardingResult(BaseModel):
    onboarding_id: str
    account_status: AccountStatus
    matched_tenant_name: bool
    matched_admin_email: bool
    searchable_text: str


app = FastAPI(title="Tenant document onboarding")


def get_pdf_client() -> InfraiPdfClient:
    return InfraiPdfClient()


@app.post("/tenants/onboard", response_model=TenantOnboardingResult)
def onboard_tenant(
    request: TenantOnboardingRequest,
    client: InfraiPdfClient = Depends(get_pdf_client),
) -> TenantOnboardingResult:
    try:
        job_id = client.ocr(request.pdf, request.onboarding_id, request.lang)
        searchable_text = client.wait_for_ocr(job_id)
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail=exc.detail) from exc
    except (TimeoutError, OSError) as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    decision = decide_account_status(
        request.tenant_name, request.admin_email, searchable_text
    )
    return TenantOnboardingResult(
        onboarding_id=request.onboarding_id,
        account_status=decision.account_status,
        matched_tenant_name=decision.matched_tenant_name,
        matched_admin_email=decision.matched_admin_email,
        searchable_text=searchable_text,
    )
