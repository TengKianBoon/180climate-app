# Commercial and Stripe foundation

**Status:** locally implemented, fail-closed; no Stripe account, live Payment Link, charge, push or deployment is established by this document.

**Decision date:** 11 September 2026.

## Business decision

180Climate will keep the automated EUDR and carbon screens free and test demand through fixed-scope, human-reviewed professional services:

| Offer | Launch price | Delivery boundary |
|---|---:|---|
| EUDR Evidence Readiness Review | S$395 | One supplier/portfolio, up to 25 plots and 2.5 review hours |
| Carbon Eligibility Review | S$750 | One site/landholding and up to 3 specialist hours |
| Indonesia Land Evidence Pilot | S$3,800 | Thirty days and up to 20 blended hours |
| Full Carbon Pre-FS | From S$9,800 | Written quotation and milestone contract required |

Fieldwork registration, matching and consent-controlled introduction remain free. Requesters and providers continue to contract and pay directly; 180Climate does not receive or release provider money.

The existing Wix Light plan is retained for the corporate site. The payment foundation uses direct Stripe-hosted links rather than making an additional Wix commerce subscription a dependency. Wix remains a navigation and content surface; the FastAPI application remains the machine-discovery and control surface; Stripe is the licensed payment processor for 180Climate's own paid services.

## Implemented architecture

```text
human or authorised agent
        |
        | read prices and scope
        v
/.well-known/180climate-commercial.json
        |
        | immediate user approval + scope acknowledgement
        v
POST /api/commercial/offers/{offer_id}/checkout
        |
        | strict mode, control and hostname checks
        v
Stripe-hosted Payment Link
```

The application:

- stores prices and delivery boundaries in a typed, versioned public catalogue;
- defaults `COMMERCIAL_CHECKOUT_MODE` to `off`;
- distinguishes `off`, Stripe `test` and Stripe `live` links;
- accepts only HTTPS links on `buy.stripe.com` and rejects mode/link mismatches;
- requires an explicit user approval and scope acknowledgement for the checkout handoff;
- keeps the full Pre-FS quotation-only;
- requires live approval, terms, refund-policy and tax-display control values before a live link can be returned;
- never receives card or bank credentials and does not create charges or payouts;
- returns no configured checkout URL in the discovery catalogue.

## Agent-facing contract

The stable discovery URL is `/.well-known/180climate-commercial.json`. An agent may read and compare offers without side effects. Before asking for a checkout handoff, it must show the represented user the exact offer, SGD price, scope, exclusions, destination and payment consequence and obtain immediate approval.

The handoff returns a Stripe URL; it does not complete payment. The human must review and confirm any charge on Stripe. Automated acceptance of terms, transaction confirmation, refund, payout, contract formation and Fieldwork dispatch remain blocked.

## Configuration

The public repository contains variable names only. Values belong in the private deployment environment:

```text
COMMERCIAL_CHECKOUT_MODE=off|test|live
STRIPE_EUDR_REVIEW_PAYMENT_LINK=
STRIPE_CARBON_REVIEW_PAYMENT_LINK=
STRIPE_LAND_EVIDENCE_PILOT_PAYMENT_LINK=
COMMERCIAL_LIVE_APPROVAL_ID=
COMMERCIAL_TERMS_VERSION=
COMMERCIAL_REFUND_POLICY_VERSION=
COMMERCIAL_TAX_DISPLAY=
```

Test mode accepts only a Stripe link whose path begins `/test_`. Live mode rejects a test link and remains closed until every live control above is non-empty.

## Verification and remaining gates

Automated tests cover the offer amounts, Fieldwork separation, approval requirement, default-closed state, Stripe hostname and test/live mismatch, live-control completeness, quotation-only Pre-FS and public page/schema delivery.

Before live activation:

1. create or verify the 180Climate Pte Ltd Stripe merchant account and settlement details;
2. approve customer terms, tax display, cancellation/refund treatment and delivery acceptance;
3. create the three exact Stripe products and Payment Links in test mode;
4. run successful, declined, cancelled and refunded test transactions;
5. record company approval for the exact live products and prices;
6. create live Payment Links and configure deployment secrets;
7. separately approve public push, deployment and Wix navigation changes;
8. verify the live price, currency, descriptor, receipt, support route and no-card-data boundary.

Creating credentials, upgrading Wix, connecting an account, confirming a purchase, activating a live product, pushing or deploying are consequential actions and are not implied by the local implementation.
