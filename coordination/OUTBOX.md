# OUTBOX — Builder -> Cowork · WO-EUDR-LOGO-019 · 2026-07-01

## Status: CI GREEN -- 463 tests pass -- STOPPED for Cowork review

One-line HTML change. No contract change. No gate.

---

## What shipped (commit a8c3e97)

[frontend/index.html](frontend/index.html) L367: logo `<img>` wrapped in:

```html
<a href="https://180climate.net" target="_blank" rel="noopener">
  <img src="/brand/logo.png" alt="180Climate" class="logo-img">
</a>
```

Shared header — covers both the Carbon and EUDR screens.

```
pytest tests/ -> 463 passed, 1 warning
```
