# Production-Hardening Roadmap

*180Climate — Carbon & EUDR platform*

The live apps are a deliberate MVP: they solve the user's problem end-to-end on a deterministic core, with layered verification and human gates. The workstreams below are the known path from **solid MVP → production-grade by industry standards**. They are **deferred on purpose** — building them ahead of real usage would be over-engineering — but each is understood, scoped, and sequenced. This document exists so the plan is *explicit, not aspirational*.

**Suggested sequence:** analytics + observability first (cheap, high signal) → security before any paid promotion → the eval harness to scale trust → scale/CD when volume demands it.

---

### 1. Observability & monitoring
- **Why deferred:** low traffic; the append-only journal + application logs suffice today.
- **Trigger:** first sustained real traffic, or before any promotion.
- **Approach:** Sentry (error tracking) · an uptime monitor (BetterStack / UptimeRobot) on a `/health` endpoint · structured request + latency logging to a dashboard (Grafana Cloud free tier) · event instrumentation for signals already computed (screening run, lead captured, overlay-fetch failures = the amber-rate).
- **Rough effort:** 1–2 days.

### 2. Automated eval harness
- **Why deferred:** the independent advisor agent covers high-stakes review manually today.
- **Trigger:** before broad launch; to make trust repeatable at scale.
- **Approach:** reuse the golden-case fixtures + an **LLM-as-judge** over the `narrative/` output (faithful to the deterministic numbers, plain-language, zero banned claims) · a **red-team suite** that actively tries to force a banned claim / a false-green / an over-claim · offline in CI + sampled online on real runs · track the **amber / inconclusive rate** as the live "don't over-conserve" lever.
- **Rough effort:** 2–3 days.

### 3. Security & abuse hardening
- **Why deferred:** limited exposure before promotion.
- **Trigger:** before any paid promotion or wide sharing.
- **Approach:** rate-limiting (slowapi, or Cloudflare in front) · upload size/complexity limits · a bot check on the lead form (Cloudflare Turnstile / hCaptcha) · dependency scanning (Dependabot + `pip-audit`) · a secrets-hygiene audit · a lightweight threat model for the public endpoints · tighten CORS / allowed-hosts.
- **Rough effort:** 1–2 days.

### 4. Scale & continuous delivery
- **Why deferred:** free-tier capacity fits current volume; auto-deploy on push is adequate.
- **Trigger:** when cold starts or volume degrade UX.
- **Approach:** a **staging** environment + a **post-deploy smoke test** (hit `/health` + a golden screening) + a **rollback** path · **cache the overlay reads** (JRC COG / Hansen tiles) to cut latency and external calls · move off the free instance when cold starts bite · a CDN (Cloudflare) in front · a small datastore only if lead/state volume outgrows email + Sheet.
- **Rough effort:** 2–4 days.

### 5. Product analytics
- **Why deferred:** nothing to optimise without traffic.
- **Trigger:** as soon as there's a steady stream.
- **Approach:** privacy-friendly analytics (Plausible / PostHog) instrumenting the **funnel** — visit → start screening → see result → submit lead → download report — plus the carbon-vs-EUDR split and per-step drop-off. Feeds lead-gen conversion optimisation (the app's business purpose).
- **Rough effort:** 1 day.

---

*Each workstream is a clean, self-contained next chapter — deliberately staged behind real usage, in the same "right-size the rigour" spirit as the product itself.*
