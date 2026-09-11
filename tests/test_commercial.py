"""Commercial catalogue, scope and Stripe handoff controls."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app, raise_server_exceptions=True)
ROOT = Path(__file__).parents[1]
LINK_ENVS = (
    "STRIPE_EUDR_REVIEW_PAYMENT_LINK",
    "STRIPE_CARBON_REVIEW_PAYMENT_LINK",
    "STRIPE_LAND_EVIDENCE_PILOT_PAYMENT_LINK",
)
CONTROL_ENVS = (
    "COMMERCIAL_LIVE_APPROVAL_ID",
    "COMMERCIAL_TERMS_VERSION",
    "COMMERCIAL_REFUND_POLICY_VERSION",
    "COMMERCIAL_TAX_DISPLAY",
)


def _clear_commercial_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("COMMERCIAL_CHECKOUT_MODE", raising=False)
    for name in LINK_ENVS + CONTROL_ENVS:
        monkeypatch.delenv(name, raising=False)


def test_commercial_catalogue_has_approved_prices_and_fieldwork_boundary(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear_commercial_env(monkeypatch)
    response = client.get("/.well-known/180climate-commercial.json")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    catalogue = response.json()
    assert catalogue == client.get("/api/commercial/catalog").json()
    assert catalogue["checkout_mode"] == "off"
    assert "pay directly" in catalogue["fieldwork_payment_status"]
    offers = {offer["offer_id"]: offer for offer in catalogue["offers"]}
    assert offers["eudr_evidence_readiness_review_v1"]["price_amount"] == 39500
    assert offers["carbon_eligibility_review_v1"]["price_amount"] == 75000
    assert offers["indonesia_land_evidence_pilot_v1"]["price_amount"] == 380000
    assert offers["carbon_full_pre_fs_quote_v1"]["price_amount"] == 980000
    assert all(offer["requires_immediate_user_approval"] for offer in offers.values())
    assert all(offer["checkout_availability"] == "closed" for offer in offers.values())
    assert "checkout_url" not in json.dumps(catalogue)


def test_checkout_fails_closed_without_configuration_or_approval(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear_commercial_env(monkeypatch)
    path = "/api/commercial/offers/eudr_evidence_readiness_review_v1/checkout"
    missing_approval = client.post(
        path,
        json={"customer_approved": False, "scope_acknowledged": True, "currency": "SGD"},
    )
    assert missing_approval.status_code == 409
    assert missing_approval.json()["detail"]["code"] == "immediate_user_approval_required"

    closed = client.post(
        path,
        json={"customer_approved": True, "scope_acknowledged": True, "currency": "SGD"},
    )
    assert closed.status_code == 503
    assert closed.json()["detail"]["code"] == "checkout_not_configured"


def test_test_mode_accepts_only_stripe_test_payment_links(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear_commercial_env(monkeypatch)
    monkeypatch.setenv("COMMERCIAL_CHECKOUT_MODE", "test")
    monkeypatch.setenv("STRIPE_EUDR_REVIEW_PAYMENT_LINK", "https://buy.stripe.com/test_example123")
    catalogue = client.get("/api/commercial/catalog").json()
    offer = next(item for item in catalogue["offers"] if item["offer_id"] == "eudr_evidence_readiness_review_v1")
    assert offer["checkout_availability"] == "test_ready"

    response = client.post(
        offer["checkout_action"],
        json={"customer_approved": True, "scope_acknowledged": True, "currency": "SGD"},
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["checkout_url"] == "https://buy.stripe.com/test_example123"
    assert response.json()["checkout_mode"] == "test"

    monkeypatch.setenv("STRIPE_EUDR_REVIEW_PAYMENT_LINK", "https://example.com/test_example123")
    assert client.post(
        offer["checkout_action"],
        json={"customer_approved": True, "scope_acknowledged": True, "currency": "SGD"},
    ).status_code == 503


def test_live_mode_requires_all_commercial_controls(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear_commercial_env(monkeypatch)
    monkeypatch.setenv("COMMERCIAL_CHECKOUT_MODE", "live")
    monkeypatch.setenv("STRIPE_CARBON_REVIEW_PAYMENT_LINK", "https://buy.stripe.com/liveExample123")
    path = "/api/commercial/offers/carbon_eligibility_review_v1/checkout"
    payload = {"customer_approved": True, "scope_acknowledged": True, "currency": "SGD"}
    assert client.post(path, json=payload).status_code == 503

    for name in CONTROL_ENVS:
        monkeypatch.setenv(name, "recorded-v1")
    response = client.post(path, json=payload)
    assert response.status_code == 200
    assert response.json()["checkout_mode"] == "live"


def test_quote_offer_cannot_be_bought_automatically(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear_commercial_env(monkeypatch)
    response = client.post(
        "/api/commercial/offers/carbon_full_pre_fs_quote_v1/checkout",
        json={"customer_approved": True, "scope_acknowledged": True, "currency": "SGD"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "quote_required"


def test_commercial_page_and_schema_are_public_but_checkout_is_not_live(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _clear_commercial_env(monkeypatch)
    page = client.get("/commercial")
    assert page.status_code == 200
    assert "EUDR Evidence Readiness Review" in page.text
    assert "Fieldwork matching remains free and separate" in page.text
    assert "/commercial-assets/commercial.js?v=1" in page.text
    assert client.get("/commercial-assets/commercial.css").status_code == 200
    assert client.get("/commercial-assets/unknown.js").status_code == 404

    schema = client.get("/schemas/commercial-catalogue-v1.json")
    assert schema.status_code == 200
    parsed = schema.json()
    assert parsed["$id"] == "/schemas/commercial-catalogue-v1.json"
    assert (ROOT / "frontend" / "schemas" / "commercial-catalogue-v1.json").exists()
