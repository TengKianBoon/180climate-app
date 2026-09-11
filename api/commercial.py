"""Fail-closed commercial catalogue and Stripe-hosted checkout handoff.

This module never handles card data, creates charges, or pays fieldwork providers.
It only returns a preconfigured Stripe Payment Link after a user has explicitly
approved the scoped 180Climate professional service.
"""
from __future__ import annotations

import os
from typing import Any, Literal
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel


router = APIRouter(prefix="/api/commercial", tags=["commercial"])

_OFFERS: tuple[dict[str, Any], ...] = (
    {
        "offer_id": "eudr_evidence_readiness_review_v1",
        "service_id": "eudr.plot_screen.v1",
        "name": "EUDR Evidence Readiness Review",
        "price_amount": 39500,
        "price_currency": "SGD",
        "price_type": "fixed_launch_price",
        "delivery": "Human-reviewed evidence-gap memo and one review call",
        "scope": ["one supplier or portfolio", "up to 25 plots", "up to 2.5 review hours", "one 30-minute call", "one consolidated revision"],
        "exclusions": ["DDS or TRACES filing", "legal opinion", "compliance certification", "travel and third-party data"],
        "payment_link_env": "STRIPE_EUDR_REVIEW_PAYMENT_LINK",
    },
    {
        "offer_id": "carbon_eligibility_review_v1",
        "service_id": "carbon.pre_fs.v1",
        "name": "Carbon Eligibility Review",
        "price_amount": 75000,
        "price_currency": "SGD",
        "price_type": "fixed_launch_price",
        "delivery": "Human-reviewed eligibility and evidence-gap memo with one review call",
        "scope": ["one site or landholding", "up to 3 specialist hours", "one 45-minute call", "one consolidated revision"],
        "exclusions": ["bankable feasibility study", "valuation", "investment advice", "validation or registry submission", "travel and third-party data"],
        "payment_link_env": "STRIPE_CARBON_REVIEW_PAYMENT_LINK",
    },
    {
        "offer_id": "indonesia_land_evidence_pilot_v1",
        "service_id": "commercial.land_evidence_pilot.v1",
        "name": "Indonesia Land Evidence Pilot",
        "price_amount": 380000,
        "price_currency": "SGD",
        "price_type": "fixed_launch_price",
        "delivery": "A 30-day combined evidence-readiness pilot",
        "scope": ["up to 20 blended delivery hours", "automated screening", "evidence-gap plan", "one scoped fieldwork brief", "one consolidated review"],
        "exclusions": ["field-provider fees", "travel", "laboratory or specialist fees", "paid satellite or registry data", "legal or regulated conclusions"],
        "payment_link_env": "STRIPE_LAND_EVIDENCE_PILOT_PAYMENT_LINK",
    },
    {
        "offer_id": "carbon_full_pre_fs_quote_v1",
        "service_id": "carbon.pre_fs.v1",
        "name": "Full Carbon Pre-Feasibility Study",
        "price_amount": 980000,
        "price_currency": "SGD",
        "price_type": "from_price_requires_quote",
        "delivery": "Quotation after scope, data, methodology and specialist needs are established",
        "scope": ["project-specific written scope", "milestone contract", "priced data, travel and specialist assumptions"],
        "exclusions": ["automatic purchase", "uncapped revisions", "unpriced third-party work", "guaranteed validation, registration, finance or credit issuance"],
        "payment_link_env": None,
    },
)

_OFFER_BY_ID = {offer["offer_id"]: offer for offer in _OFFERS}
_LIVE_CONTROL_ENV = (
    "COMMERCIAL_LIVE_APPROVAL_ID",
    "COMMERCIAL_TERMS_VERSION",
    "COMMERCIAL_REFUND_POLICY_VERSION",
    "COMMERCIAL_TAX_DISPLAY",
)


class CheckoutHandoffRequest(BaseModel):
    customer_approved: bool
    scope_acknowledged: bool
    currency: Literal["SGD"] = "SGD"


def _mode() -> Literal["off", "test", "live"]:
    value = os.getenv("COMMERCIAL_CHECKOUT_MODE", "off").strip().lower()
    if value == "test":
        return "test"
    if value == "live":
        return "live"
    return "off"


def _live_controls_complete() -> bool:
    return all(os.getenv(name, "").strip() for name in _LIVE_CONTROL_ENV)


def _valid_stripe_link(value: str, mode: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    if parsed.scheme != "https" or parsed.hostname != "buy.stripe.com":
        return False
    is_test_link = parsed.path.startswith("/test_")
    return (mode == "test" and is_test_link) or (mode == "live" and not is_test_link)


def _checkout_link(offer: dict[str, Any], mode: str) -> str | None:
    env_name = offer.get("payment_link_env")
    if not env_name or mode == "off":
        return None
    if mode == "live" and not _live_controls_complete():
        return None
    value = os.getenv(str(env_name), "").strip()
    return value if value and _valid_stripe_link(value, mode) else None


def _public_offer(offer: dict[str, Any], mode: str) -> dict[str, Any]:
    link = _checkout_link(offer, mode)
    public = {key: value for key, value in offer.items() if key != "payment_link_env"}
    public.update(
        {
            "checkout_availability": f"{mode}_ready" if link else "closed",
            "checkout_action": (
                f"/api/commercial/offers/{offer['offer_id']}/checkout"
                if offer["price_type"] != "from_price_requires_quote"
                else None
            ),
            "requires_immediate_user_approval": True,
        }
    )
    return public


def commercial_catalogue_payload() -> dict[str, Any]:
    mode = _mode()
    return {
        "$schema": "/schemas/commercial-catalogue-v1.json",
        "catalogue_version": "1.0.0",
        "updated_at": "2026-09-11",
        "provider": {"legal_name": "180Climate Pte Ltd", "website": "https://www.180climate.net/"},
        "currency": "SGD",
        "checkout_mode": mode,
        "payment_processor": "Stripe-hosted checkout",
        "payment_data_boundary": "180Climate does not collect or store card or bank credentials",
        "fieldwork_payment_status": "not_offered; requester and provider contract and pay directly",
        "agent_rule": "An authorised agent may compare and prepare an offer, but must obtain the user's immediate approval before requesting or opening checkout. An agent must never confirm payment autonomously.",
        "offers": [_public_offer(offer, mode) for offer in _OFFERS],
    }


@router.get(
    "/catalog",
    operation_id="getCommercialCatalogue",
    summary="Read fixed-scope professional-service offers and checkout readiness",
    openapi_extra={
        "x-agent-tool-annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    },
)
def commercial_catalogue() -> JSONResponse:
    return JSONResponse(
        commercial_catalogue_payload(),
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post(
    "/offers/{offer_id}/checkout",
    operation_id="prepareStripeCheckoutHandoff",
    summary="Return a Stripe-hosted checkout link after immediate user approval",
    openapi_extra={
        "x-agent-tool-annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        }
    },
)
def prepare_checkout_handoff(offer_id: str, request: CheckoutHandoffRequest) -> JSONResponse:
    offer = _OFFER_BY_ID.get(offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail={"code": "offer_not_found"})
    if offer["price_type"] == "from_price_requires_quote":
        raise HTTPException(status_code=409, detail={"code": "quote_required"})
    if not request.customer_approved or not request.scope_acknowledged:
        raise HTTPException(status_code=409, detail={"code": "immediate_user_approval_required"})
    mode = _mode()
    link = _checkout_link(offer, mode)
    if not link:
        raise HTTPException(status_code=503, detail={"code": "checkout_not_configured"})
    return JSONResponse(
        {
            "offer_id": offer_id,
            "price_amount": offer["price_amount"],
            "price_currency": offer["price_currency"],
            "checkout_mode": mode,
            "checkout_url": link,
            "processor": "Stripe",
            "warning": "Opening checkout does not itself complete payment. Review the Stripe-hosted page before confirming the transaction.",
        },
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )
