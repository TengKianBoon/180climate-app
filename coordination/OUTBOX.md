# OUTBOX — Builder → Cowork · WO-EUDR-RADD-LIVE-005B · 2026-06-30

## Status: CI GREEN ✅ — 400 tests pass (+16 new RADD live tests) — STOPPED for Cowork review

Live RADD query wired in `core/overlays/radd.py`. All mocked tests green. Key never in repo or logs.

---

## What shipped

### `core/overlays/radd.py` (rewritten)

| Change | Detail |
|---|---|
| `_DEFAULT_RADD_URL` | `https://data-api.globalforestwatch.org/dataset/wur_radd_alerts/latest/query` — no env var required for URL |
| Live activation | `RADD_API_KEY` alone enables live (URL has a default); `RADD_GFW_API_URL` overrides if GFW renames dataset |
| `_query_live()` | `httpx.post` with `x-api-key` header; SQL: `SELECT MAX(alert__date) AS latest, COUNT(*) AS n FROM results WHERE alert__date > '2020-12-31'` |
| Honesty | `True` = alert found; `False` = queried OK, none found; `None` = any failure (malformed response, HTTP error, network error) — NEVER fabricated |
| Malformed response | Non-dict body → `None`; `data` not a list → `None`; empty list → `False` (genuine negative) |
| Exception logging | `log.warning("RADD live query failed (%s); enrichment skipped", type(exc).__name__)` — key NEVER in log |
| Key never committed | Key lives in Render `RADD_API_KEY` env var only; no key in repo, fixtures, or logs |

### `tests/test_radd_live.py` (new, 16 tests)

| Test | Assertion |
|---|---|
| `test_default_url_points_to_wur_radd_alerts` | URL contains "wur_radd_alerts" + "data-api.globalforestwatch.org" |
| `test_live_alert_present` | n=5 → `alert_after_cutoff=True`, `latest_alert_date="2023-08-14"`, live `datasets_version` |
| `test_live_alert_present_high_count` | n=128 → `alert_after_cutoff=True` |
| `test_live_no_alerts_empty_data` | empty `data=[]` → `alert_after_cutoff=False`, `latest_alert_date=None`, live `datasets_version` |
| `test_live_no_alerts_n_zero` | `n=0` → `alert_after_cutoff=False` |
| `test_live_connection_error_returns_none` | `ConnectError` → `alert_after_cutoff=None` (never fabricated False) |
| `test_live_http_4xx_returns_none` | HTTP 403 → `alert_after_cutoff=None` |
| `test_live_malformed_body_non_dict_returns_none` | list body → `alert_after_cutoff=None` |
| `test_live_malformed_body_data_not_list_returns_none` | `data: "string"` → `alert_after_cutoff=None` |
| `test_live_missing_data_field_returns_none` | no `data` key → `alert_after_cutoff=None` |
| `test_no_key_returns_stub` | no `RADD_API_KEY` → `None`; `httpx.post` NOT called |
| `test_disable_live_skips_live_call` | `RADD_DISABLE_LIVE=true` → `None`; `httpx.post` NOT called |
| `test_disable_live_uses_stub_datasets_version` | confirms stub `datasets_version` returned |
| `test_key_never_appears_in_log_output` | scans captured `WARNING` log records — key absent |
| `test_key_never_appears_in_result_note` | key absent from `result.note` |
| `test_radd_gfw_api_url_env_override` | custom URL env var reaches `httpx.post` as the call target |

All 16 tests use `httpx.post` mocked — zero network calls. Key `"test-key-never-logged"` verifiably absent from all log output and result notes.

---

## Live verification

The live RADD path verifies on the **deployed app** — `RADD_API_KEY` is set in Render, not locally. No live smoke required here.

---

## mypy

```
mypy core/contracts/__init__.py --ignore-missing-imports
Success: no issues found in 1 source file
```

---

## pytest

```
400 passed, 1 warning in 8.75s
```

(Was 384; +16 new RADD live tests.)
