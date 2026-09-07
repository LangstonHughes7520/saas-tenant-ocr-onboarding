from onboarding_policy import AccountStatus, decide_account_status


def test_missing_admin_email_routes_account_to_review() -> None:
    result = decide_account_status(
        "Acme Tools",
        "owner@acme.example",
        "ACME TOOLS tenant application. Administrator signature is present.",
    )

    assert result.account_status is AccountStatus.NEEDS_REVIEW
    assert result.matched_tenant_name is True
    assert result.matched_admin_email is False
