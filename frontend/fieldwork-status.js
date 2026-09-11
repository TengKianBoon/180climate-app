(() => {
  "use strict";
  const form = document.querySelector("#status-form");
  const result = document.querySelector("#status-result");
  const error = document.querySelector("#status-error");

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
  }

  function readStoredAccess() {
    try {
      const value = JSON.parse(sessionStorage.getItem("fieldworkStatus") || "null");
      if (value && value.reference && value.status_key) {
        form.elements.reference.value = value.reference;
        form.elements.status_key.value = value.status_key;
      }
    } catch (_) { /* no stored status */ }
  }

  function showError(message) {
    error.textContent = message;
    error.hidden = false;
    error.focus();
  }

  function renderStatus(data) {
    const block = data.block_reason ? `<p class="result blocked">${escapeHtml(data.block_reason)}</p>` : "";
    const introductions = (data.introductions || []).map((intro) => {
      const fields = intro.shared_fields.map(escapeHtml).join(", ");
      const consent = intro.status === "consent_required" && !intro.own_consent
        ? `<form class="consent-form" data-intro="${escapeHtml(intro.reference)}"><div class="check"><input id="consent-${escapeHtml(intro.reference)}" type="checkbox" required><label for="consent-${escapeHtml(intro.reference)}">I consent to the named introduction process sharing these fields after the other party also consents and an operator confirms: ${fields}.</label></div><button class="button" type="submit">Confirm this disclosure</button></form>`
        : `<p>Your disclosure choice: ${intro.own_consent ? "confirmed" : "not confirmed"}.</p>`;
      return `<article class="status-card"><span class="status-pill">${escapeHtml(intro.status)}</span><h3>Introduction ${escapeHtml(intro.reference)}</h3><p>Proposed fields: ${fields}</p>${consent}</article>`;
    }).join("") || `<div class="status-card empty">No introduction has been proposed. A submission is not a match or booking.</div>`;
    result.innerHTML = `<article class="status-card"><span class="status-pill">${escapeHtml(data.status)}</span><h2>${escapeHtml(data.reference)}</h2><p>${escapeHtml(data.summary)}</p><p><strong>Broad location:</strong> ${escapeHtml(data.broad_location)}</p>${block}<p class="hint">Last updated ${escapeHtml(data.updated_at)}</p></article><section class="operator-section"><h2>Introductions</h2>${introductions}</section>`;
    result.querySelectorAll(".consent-form").forEach((consentForm) => {
      consentForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const button = consentForm.querySelector("button");
        button.disabled = true;
        try {
          const response = await fetch("/api/fieldwork/introductions/consent", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              reference: form.elements.reference.value.trim(),
              status_key: form.elements.status_key.value,
              introduction_reference: consentForm.dataset.intro,
              confirm: true
            })
          });
          const payload = await response.json();
          if (!response.ok) throw new Error(payload.detail?.code || "Consent was not recorded");
          await lookup();
        } catch (err) {
          showError(err.message || "Consent was not recorded");
        } finally { button.disabled = false; }
      });
    });
  }

  async function lookup() {
    error.hidden = true;
    const button = form.querySelector("button");
    button.disabled = true;
    try {
      const response = await fetch("/api/fieldwork/status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reference: form.elements.reference.value.trim(), status_key: form.elements.status_key.value })
      });
      const payload = await response.json();
      if (!response.ok) {
        const code = payload.detail?.code;
        throw new Error(code === "status_key_expired" ? "This status key has expired. Contact 180Climate through its public contact route." : "Reference and status key were not recognised.");
      }
      renderStatus(payload);
    } catch (err) {
      result.innerHTML = "";
      showError(err.message || "Status is temporarily unavailable.");
    } finally { button.disabled = false; }
  }

  form.addEventListener("submit", (event) => { event.preventDefault(); lookup(); });
  readStoredAccess();
})();
