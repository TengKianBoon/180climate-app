(() => {
  "use strict";
  const accessForm = document.querySelector("#operator-access");
  const contactToggle = document.querySelector("#include-contacts");
  const error = document.querySelector("#operator-error");
  const requestTarget = document.querySelector("#requests");
  const providerTarget = document.querySelector("#providers");
  let token = "";

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
  }
  function headers() { return { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" }; }
  function showError(message) { error.textContent = message; error.hidden = false; error.focus(); }

  function statusControl(reference, type) {
    const choices = type === "request"
      ? ["needs_information", "qualified", "matching", "blocked", "no_match", "archived"]
      : ["profile_incomplete", "match_ready", "temporarily_unavailable", "restricted", "archived"];
    return `<form class="status-update" data-reference="${escapeHtml(reference)}"><select aria-label="New status">${choices.map((item) => `<option value="${item}">${item}</option>`).join("")}</select><input aria-label="Reason" placeholder="Reason" maxlength="500"><button class="button quiet" type="submit">Update</button></form>`;
  }

  function renderRequests(rows) {
    if (!rows.length) { requestTarget.innerHTML = '<p class="empty">No requests received.</p>'; return; }
    requestTarget.innerHTML = `<table><thead><tr><th>Reference / status</th><th>Result and location</th><th>Authority / risk</th><th>Operator action</th></tr></thead><tbody>${rows.map((row) => `<tr><td><strong>${escapeHtml(row.reference)}</strong><br><span class="status-pill">${escapeHtml(row.status)}</span>${row.name ? `<br>${escapeHtml(row.name)}<br>${escapeHtml(row.contact)}` : ""}</td><td>${escapeHtml(row.desired_result)}<br><small>${escapeHtml(row.broad_location)} · ${escapeHtml(row.timing)}</small></td><td>Authority: ${escapeHtml(row.authority_status)}<br>Hazard: ${escapeHtml(row.hazard_status)}<br>Permit: ${escapeHtml(row.permit_status)}<br>Restricted: ${escapeHtml(row.restricted_status)}${row.block_reason ? `<br><strong>${escapeHtml(row.block_reason)}</strong>` : ""}</td><td>${statusControl(row.reference, "request")}</td></tr>`).join("")}</tbody></table>`;
  }

  function renderProviders(rows) {
    if (!rows.length) { providerTarget.innerHTML = '<p class="empty">No provider profiles received.</p>'; return; }
    providerTarget.innerHTML = `<table><thead><tr><th>Reference / status</th><th>Capability</th><th>Area / availability</th><th>Operator action</th></tr></thead><tbody>${rows.map((row) => `<tr><td><strong>${escapeHtml(row.reference)}</strong><br><span class="status-pill">${escapeHtml(row.status)}</span>${row.name ? `<br>${escapeHtml(row.name)}<br>${escapeHtml(row.contact)}` : ""}</td><td><strong>${escapeHtml(row.role_title)}</strong><br>${escapeHtml(row.services)}<br><small>Credentials: ${escapeHtml(row.credentials)}</small></td><td>${escapeHtml(row.service_area)}<br>${escapeHtml(row.availability)}<br><small>Exclusions: ${escapeHtml(row.exclusions)}</small></td><td>${statusControl(row.reference, "provider")}</td></tr>`).join("")}</tbody></table>`;
  }

  async function loadQueue() {
    error.hidden = true;
    const response = await fetch(`/api/fieldwork/operator/queue?include_contacts=${contactToggle.checked}`, { headers: headers() });
    const payload = await response.json();
    if (!response.ok) throw new Error("Operator access was not accepted.");
    renderRequests(payload.requests || []);
    renderProviders(payload.providers || []);
    document.querySelectorAll(".status-update").forEach((form) => {
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const select = form.querySelector("select");
        const reason = form.querySelector("input").value;
        try {
          const response = await fetch(`/api/fieldwork/operator/records/${encodeURIComponent(form.dataset.reference)}/status`, { method: "POST", headers: headers(), body: JSON.stringify({ status: select.value, reason }) });
          const payload = await response.json();
          if (!response.ok) throw new Error(payload.detail?.code || "Status was not changed");
          await loadQueue();
        } catch (err) { showError(err.message || "Status was not changed"); }
      });
    });
  }

  accessForm.addEventListener("submit", async (event) => {
    event.preventDefault(); token = document.querySelector("#operator-token").value;
    try { await loadQueue(); } catch (err) { showError(err.message || "Queue unavailable"); }
  });
  contactToggle.addEventListener("change", async () => { if (token) { try { await loadQueue(); } catch (err) { showError(err.message); } } });

  document.querySelector("#proposal-form").addEventListener("submit", async (event) => {
    event.preventDefault(); const target = document.querySelector("#proposal-result");
    const fields = ["name", "contact"];
    if (document.querySelector("#share-role").checked) fields.push("role_title");
    if (document.querySelector("#share-location").checked) fields.push("broad_location");
    try {
      const response = await fetch("/api/fieldwork/operator/introductions", { method: "POST", headers: headers(), body: JSON.stringify({ request_reference: document.querySelector("#request-reference").value, provider_reference: document.querySelector("#provider-reference").value, shared_fields: fields }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail?.code || "Introduction preview was not created");
      target.innerHTML = `<div class="result"><span class="status-pill">${escapeHtml(payload.status)}</span><h3>${escapeHtml(payload.reference)}</h3><p>Both parties must now confirm the named disclosure in their private status pages.</p></div>`;
      document.querySelector("#introduction-reference").value = payload.reference;
      await loadQueue();
    } catch (err) { showError(err.message || "Introduction preview was not created"); }
  });

  document.querySelector("#finalize-form").addEventListener("submit", async (event) => {
    event.preventDefault(); const reference = document.querySelector("#introduction-reference").value; const target = document.querySelector("#finalize-result");
    try {
      const response = await fetch(`/api/fieldwork/operator/introductions/${encodeURIComponent(reference)}/finalize`, { method: "POST", headers: headers(), body: JSON.stringify({ confirm: true }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail?.code || "Introduction is not ready");
      target.innerHTML = `<div class="result"><span class="status-pill">introduced</span><h3>${escapeHtml(payload.reference)}</h3><p>${escapeHtml(payload.message)}</p><div class="key-box"><strong>Requester</strong>${escapeHtml(payload.disclosure.requester.display_name)} · ${escapeHtml(payload.disclosure.requester.contact_value)}<strong>Provider</strong>${escapeHtml(payload.disclosure.provider.display_name)} · ${escapeHtml(payload.disclosure.provider.contact_value)}</div></div>`;
      await loadQueue();
    } catch (err) { showError(err.message || "Introduction is not ready"); }
  });
})();
