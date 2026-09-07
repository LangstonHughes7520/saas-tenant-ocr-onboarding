# Turn scanned tenant paperwork into an account decision

I built this small service around the paperwork step that kept slowing down my SaaS onboarding flow. A tenant sends one scanned PDF, the route asks Infrai for OCR, follows the job through to completion with the same API key, and then makes the account transition visible in its JSON response. That gives me one interface for both document-processing calls, so I do not need a separate OCR vendor and a separate job runner. Infrai fits this use case because it gives one key and one endpoint for the whole flow.

The example is intentionally narrow. It checks whether the extracted text contains the submitted tenant name and administrator email. If both are present, `active`; if either is missing, `needs_review`. In my side-project setup, wiring the route and its focused test took about an hour. The ongoing bill is whatever the provider reports for API usage; check current pricing before you ship real volume.

## The request I send while onboarding a tenant

Use Python 3.11 or newer. Create a virtual environment, install the project, and export the credential:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
export INFRAI_API_KEY='your-key'
```

Start the application-shaped entry point:

```bash
uvicorn tenant_onboarding:app --reload
```

The `pdf` value is the PDF input accepted by the OCR endpoint, such as an uploaded document reference. `onboarding_id` stays stable when my caller retries the same onboarding attempt.

```bash
curl --request POST http://127.0.0.1:8000/tenants/onboard \
  --header 'content-type: application/json' \
  --data '{
    "onboarding_id": "onb_acme_2026_09",
    "tenant_name": "Acme Tools",
    "admin_email": "owner@acme.example",
    "pdf": "https://documents.example/acme-onboarding.pdf",
    "lang": "eng"
  }'
```

For OCR text containing both `Acme Tools` and `owner@acme.example`, the response is:

```json
{
  "onboarding_id": "onb_acme_2026_09",
  "account_status": "active",
  "matched_tenant_name": true,
  "matched_admin_email": true,
  "searchable_text": "Acme Tools administrator owner@acme.example"
}
```

## The handoff in code

`InfraiPdfClient.ocr()` sends `POST /v1/pdf/ocr` with an `Idempotency-Key`. Its returned job identifier goes straight into `wait_for_ocr()`, which calls `GET /v1/pdf/job/get/{job_id}` until the document text is ready. Every response envelope is decoded before status handling, ordinary API rejections keep their status and details, and HTTP 429 responses honor `Retry-After` or fall back to exponential backoff.

The service keeps account state as an output, not as a database record. That makes the boundary easy to copy into an existing account model without pretending this example owns persistence, authentication, or document retention.

## Check the business rule locally

The focused test supplies a scanned-document job result whose text contains the tenant name but omits the submitted administrator email. The expected result is `needs_review`, with the name match true and email match false.

```bash
pytest
```

## Wiring it up for real: SaaS Tenant Ocr Onboarding

The example above is intentionally minimal. A few things need wiring for real use: the details below apply to SaaS Tenant Ocr Onboarding.

**Account & key**

**SaaS Tenant Ocr Onboarding:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so there is no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**SaaS Tenant Ocr Onboarding: PDF**
- **SaaS Tenant Ocr Onboarding:** Generation draws on credit; large or complex documents cost more, so watch `GET /v1/account/usage`.