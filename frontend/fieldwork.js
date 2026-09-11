(() => {
  "use strict";

  const root = document.documentElement;
  const banner = document.querySelector("#pilot-banner");
  const languageButton = document.querySelector("#lang-toggle");
  const externalIntake = banner.dataset.intake === "wix";
  let pilotOpen = false;

  const text = {
    en: {
      loading: "Checking invited-pilot availability…",
      open: "Invited-pilot intake is open. Use only your private invitation code.",
      closed: "Preview only — real-user intake is closed until the privacy, legal, processor, retention and deployment gates are approved.",
      external: "Invited-pilot applications are open through 180Climate's private Wix review form.",
      fix: "Please complete the highlighted required field before continuing.",
      unavailable: "The service could not receive this submission. Your information was not confirmed as saved.",
      submitting: "Submitting…",
      save: "Save these separately. The status key is shown once and is not placed in a URL.",
      closedSubmit: "Pilot not open"
    },
    id: {
      loading: "Memeriksa ketersediaan uji coba…",
      open: "Pendaftaran uji coba terbuka. Gunakan hanya kode undangan privat Anda.",
      closed: "Hanya pratinjau — pendaftaran pengguna nyata ditutup sampai gerbang privasi, hukum, pemroses, retensi, dan penerapan disetujui.",
      external: "Pendaftaran uji coba undangan dibuka melalui formulir tinjauan privat Wix 180Climate.",
      fix: "Lengkapi bidang wajib yang ditandai sebelum melanjutkan.",
      unavailable: "Layanan tidak dapat menerima kiriman ini. Informasi Anda belum dikonfirmasi tersimpan.",
      submitting: "Mengirim…",
      save: "Simpan keduanya secara terpisah. Kunci status hanya ditampilkan sekali dan tidak ditempatkan di URL.",
      closedSubmit: "Uji coba belum dibuka"
    }
  };

  const locale = () => root.dataset.lang === "id" ? "id" : "en";

  function setLanguage(next) {
    root.dataset.lang = next;
    root.lang = next;
    languageButton.textContent = next === "en" ? "ID" : "EN";
    document.querySelectorAll('input[name="locale"]').forEach((input) => { input.value = next; });
    renderBanner(banner.dataset.state || "loading");
  }

  languageButton.addEventListener("click", () => setLanguage(locale() === "en" ? "id" : "en"));

  function renderBanner(state) {
    banner.dataset.state = state === "external" ? "open" : state;
    banner.textContent = text[locale()][state] || text[locale()].loading;
  }

  function makeIdempotencyKey() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") return window.crypto.randomUUID();
    return `fw-${Date.now()}-${Math.random().toString(16).slice(2)}-${Math.random().toString(16).slice(2)}`;
  }

  async function recordEvent(event) {
    try {
      await fetch("/api/fieldwork/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event }),
        keepalive: true
      });
    } catch (_) {
      // Analytics is aggregate and non-essential; form operation never depends on it.
    }
  }

  async function loadConfig() {
    try {
      const response = await fetch("/api/fieldwork/config", { headers: { "Accept": "application/json" } });
      if (!response.ok) throw new Error("config unavailable");
      const config = await response.json();
      pilotOpen = Boolean(config.accepting_submissions);
      const privacyContact = document.querySelector("#privacy-contact");
      const privacyContactPending = document.querySelector("#privacy-contact-pending");
      if (privacyContact && config.privacy_contact && config.privacy_contact !== "not_confirmed" && config.privacy_contact_url !== "not_confirmed") {
        privacyContact.href = config.privacy_contact_url;
        privacyContact.textContent = config.privacy_contact;
        privacyContact.hidden = false;
        if (privacyContactPending) privacyContactPending.hidden = true;
      }
      if (pilotOpen) {
        document.querySelector("#privacy-launch-pending").hidden = true;
        document.querySelector("#privacy-launch-ready").hidden = false;
        document.querySelector("#controller-name").textContent = config.controller_name;
        document.querySelector("#hosting-region").textContent = config.hosting_region;
        document.querySelector("#retention-summary").textContent = config.retention_summary;
        document.querySelector("#processor-summary").textContent = config.processor_summary;
      }
      renderBanner(externalIntake ? "external" : pilotOpen ? "open" : "closed");
    } catch (_) {
      pilotOpen = false;
      renderBanner(externalIntake ? "external" : "closed");
    }
    document.querySelectorAll("[data-submit]").forEach((button) => {
      button.disabled = !pilotOpen;
      if (!pilotOpen) button.dataset.originalLabel = button.textContent;
      if (!pilotOpen) button.textContent = text[locale()].closedSubmit;
    });
  }

  function currentStepFields(form, step) {
    return Array.from(form.querySelectorAll(`.form-step[data-step="${step}"] input, .form-step[data-step="${step}"] select, .form-step[data-step="${step}"] textarea`));
  }

  function validateStep(form, step, errorBox) {
    const invalid = currentStepFields(form, step).find((field) => !field.checkValidity());
    if (!invalid) {
      errorBox.hidden = true;
      return true;
    }
    errorBox.textContent = text[locale()].fix;
    errorBox.hidden = false;
    errorBox.focus();
    invalid.reportValidity();
    return false;
  }

  function setupStepper(form, eventName) {
    let step = 0;
    const steps = Array.from(form.querySelectorAll(".form-step"));
    const markers = Array.from(document.querySelector(`[data-stepper="${form.id === "requester" ? "request" : "provider"}"]`).children);
    const next = form.querySelector("[data-next]");
    const back = form.querySelector("[data-back]");
    const submit = form.querySelector("[data-submit]");
    const errorBox = document.querySelector(`#${form.id === "requester" ? "request" : "provider"}-errors`);
    let started = false;

    function show(index) {
      step = index;
      steps.forEach((item, i) => { item.hidden = i !== step; });
      markers.forEach((item, i) => {
        item.classList.toggle("active", i === step);
        item.classList.toggle("done", i < step);
      });
      back.hidden = step === 0;
      next.hidden = step === steps.length - 1;
      submit.hidden = step !== steps.length - 1;
      errorBox.hidden = true;
      const legend = steps[step].querySelector("legend:not([style*='display: none'])") || steps[step].querySelector("legend");
      if (legend) legend.focus?.();
    }

    next.addEventListener("click", () => {
      if (!validateStep(form, step, errorBox)) return;
      if (!started) { recordEvent(eventName); started = true; }
      if (form.id === "requester" && step === 0) {
        const original = form.elements.original_text.value.trim();
        if (!form.elements.desired_result.value.trim()) form.elements.desired_result.value = original;
        form.elements.preferred_contact.value = form.elements.contact_kind.value;
      }
      show(Math.min(step + 1, steps.length - 1));
    });
    back.addEventListener("click", () => show(Math.max(0, step - 1)));
    show(0);
  }

  function serialise(form) {
    const output = {};
    Array.from(form.elements).forEach((field) => {
      if (!field.name || field.disabled || ["button", "submit"].includes(field.type)) return;
      output[field.name] = field.type === "checkbox" ? field.checked : field.value.trim();
    });
    return output;
  }

  function errorMessage(payload) {
    const detail = payload && payload.detail;
    if (detail && typeof detail.message === "string") return detail.message;
    if (Array.isArray(detail) && detail[0] && detail[0].msg) return detail[0].msg;
    return text[locale()].unavailable;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
  }

  function renderResult(target, data) {
    const blocked = data.status === "blocked";
    const key = data.status_key
      ? `<div class="key-box"><span>${escapeHtml(text[locale()].save)}</span><strong>Reference</strong><code>${escapeHtml(data.reference)}</code><strong>Status key</strong><code>${escapeHtml(data.status_key)}</code></div>`
      : "";
    target.innerHTML = `<div class="result${blocked ? " blocked" : ""}"><span class="status-pill">${escapeHtml(data.status)}</span><h3>${escapeHtml(data.reference)}</h3><p>${escapeHtml(data.message)}</p>${key}<p><a class="button quiet" href="/fieldwork/status">${locale() === "id" ? "Buka halaman status" : "Open status page"}</a></p></div>`;
    if (data.status_key) {
      sessionStorage.setItem("fieldworkStatus", JSON.stringify({ reference: data.reference, status_key: data.status_key }));
    }
    target.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function setupSubmission(form, endpoint, resultSelector) {
    const result = document.querySelector(resultSelector);
    const errorBox = document.querySelector(`#${form.id === "requester" ? "request" : "provider"}-errors`);
    form.elements.idempotency_key.value = makeIdempotencyKey();
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!pilotOpen) {
        errorBox.textContent = text[locale()].closed;
        errorBox.hidden = false;
        errorBox.focus();
        return;
      }
      if (!validateStep(form, 2, errorBox)) return;
      const button = form.querySelector("[data-submit]");
      button.disabled = true;
      const prior = button.textContent;
      button.textContent = text[locale()].submitting;
      errorBox.hidden = true;
      try {
        const response = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Accept": "application/json" },
          body: JSON.stringify(serialise(form))
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(errorMessage(payload));
        renderResult(result, payload);
        form.hidden = true;
      } catch (error) {
        errorBox.textContent = error.message || text[locale()].unavailable;
        errorBox.hidden = false;
        errorBox.focus();
      } finally {
        button.disabled = !pilotOpen;
        button.textContent = prior;
      }
    });
  }

  const requester = document.querySelector("#requester");
  const provider = document.querySelector("#provider");
  setupStepper(requester, "request_form_start");
  setupStepper(provider, "provider_form_start");
  setupSubmission(requester, "/api/fieldwork/requests", "#request-result");
  setupSubmission(provider, "/api/fieldwork/providers", "#provider-result");
  setLanguage("en");
  loadConfig();
  recordEvent("visit");
})();
