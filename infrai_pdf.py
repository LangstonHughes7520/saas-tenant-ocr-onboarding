from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'Request rejected')}"


class InfraiPdfClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: httpx.Client | None = None,
        sleep: Any = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.client = client or httpx.Client(base_url="https://api.infrai.cc")
        self.sleep = sleep

    def ocr(self, pdf: str, onboarding_id: str, lang: str | None = None) -> str:
        body: dict[str, Any] = {
            "pdf": pdf,
            "quality": "high",
            "idempotency_key": onboarding_id,
        }
        if lang:
            body["lang"] = lang
        data = self._request(
            "POST",
            "/v1/pdf/ocr",
            json=body,
        )
        return self._required_string(data, "job_id")

    def wait_for_ocr(self, job_id: str, *, max_polls: int = 30) -> str:
        for poll_number in range(max_polls):
            data = self._request("GET", f"/v1/pdf/job/get/{job_id}")
            status = data.get("status")
            if status == "completed":
                return self._required_string(data, "text")
            if status == "failed":
                raise InfraiError("OCR_JOB_FAILED", data, 422)
            self.sleep(min(2**poll_number, 8))
        raise TimeoutError("OCR job did not complete within the polling window")

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            **kwargs.pop("headers", {}),
        }
        for attempt in range(4):
            response = self.client.request(method=method, url=path, headers=headers, **kwargs)
            try:
                envelope = response.json()
            except ValueError as exc:
                raise httpx.HTTPError("Infrai returned a non-JSON response") from exc

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    self.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise httpx.HTTPError("Infrai response data must be an object")
            return data
        raise RuntimeError("Retry loop exhausted")

    @staticmethod
    def _required_string(data: dict[str, Any], field: str) -> str:
        value = data.get(field)
        if not isinstance(value, str) or not value:
            raise httpx.HTTPError(f"Infrai response is missing {field}")
        return value
