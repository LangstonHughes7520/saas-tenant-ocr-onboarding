from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AccountStatus(str, Enum):
    ACTIVE = "active"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class AccountDecision:
    account_status: AccountStatus
    matched_tenant_name: bool
    matched_admin_email: bool


def decide_account_status(
    tenant_name: str, admin_email: str, searchable_text: str
) -> AccountDecision:
    normalized = searchable_text.casefold()
    name_match = tenant_name.casefold() in normalized
    email_match = admin_email.casefold() in normalized
    status = AccountStatus.ACTIVE if name_match and email_match else AccountStatus.NEEDS_REVIEW
    return AccountDecision(status, name_match, email_match)

