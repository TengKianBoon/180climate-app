# OUTBOX — Builder → Cowork · WO-SUBDOMAIN-ROUTING-010 · 2026-06-30

## Status: CI GREEN ✅ — 446 tests pass (no new tests; backend untouched) — STOPPED for Cowork review

Subdomain + `?tool=` routing added to `frontend/index.html`. No backend change.

---

## What shipped

### `frontend/index.html` — two changes

**1. `<title>` sync in `switchScreen()`**

```js
document.title = which === 'eudr'
  ? '180Climate — EUDR Plot Check'
  : '180Climate — Carbon Pre-Feasibility Screening';
```

Previously the tab title was the static `<title>` from line 6 (`180Climate — Carbon Pre-Feasibility Screening`) and never updated when the user switched screens.

**2. `DOMContentLoaded` routing block**

```js
document.addEventListener('DOMContentLoaded', function() {
  var params = new URLSearchParams(window.location.search);
  var toolParam = (params.get('tool') || '').toLowerCase();
  var host = (window.location.hostname || '').toLowerCase();
  var defaultTool;
  if (toolParam === 'eudr' || toolParam === 'carbon') {
    defaultTool = toolParam;          // ?tool= wins
  } else if (host.indexOf('eudr.') === 0) {
    defaultTool = 'eudr';             // eudr.180climate.net
  } else if (host.indexOf('carbon.') === 0) {
    defaultTool = 'carbon';           // carbon.180climate.net
  } else {
    defaultTool = 'carbon';           // onrender.com / localhost / app.*
  }
  switchScreen(defaultTool);
});
```

Priority (highest to lowest):
1. `?tool=eudr` or `?tool=carbon` query param
2. `eudr.*` hostname → eudr
3. `carbon.*` hostname → carbon
4. Everything else (Render URL, `app.180climate.net`, localhost) → carbon

Both `.screen-tab` buttons remain visible and functional for cross-sell.

---

## Verify (no backend change; pytest 446 passed)

| Scenario | Expected |
|---|---|
| `/` (localhost / Render) | Carbon active, title "180Climate — Carbon Pre-Feasibility Screening" |
| `/?tool=eudr` | EUDR active, title "180Climate — EUDR Plot Check" |
| `/?tool=carbon` | Carbon active |
| `eudr.180climate.net/` | EUDR active (subdomain match) |
| `carbon.180climate.net/` | Carbon active (subdomain match) |
| Manual tab click | Both tabs switch correctly (unchanged behaviour) |
