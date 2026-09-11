(() => {
  "use strict";

  const status = document.querySelector("#checkout-status");
  const acknowledgement = document.querySelector("#scope-acknowledgement");
  const message = document.querySelector("#checkout-message");
  const buttons = [...document.querySelectorAll(".checkout-button")];
  let catalogue = null;

  function setMessage(text, isError = false) {
    message.textContent = text;
    message.classList.toggle("error", isError);
  }

  function offerFor(button) {
    return catalogue?.offers?.find((offer) => offer.offer_id === button.dataset.offerId);
  }

  function refreshButtons() {
    buttons.forEach((button) => {
      const offer = offerFor(button);
      const ready = Boolean(offer && offer.checkout_availability !== "closed");
      button.disabled = !ready || !acknowledgement.checked;
      button.textContent = !ready
        ? "Checkout setup pending"
        : catalogue.checkout_mode === "test"
          ? "Open Stripe test checkout"
          : "Continue to secure checkout";
    });
  }

  async function loadCatalogue() {
    try {
      const response = await fetch("/api/commercial/catalog", { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("catalogue unavailable");
      catalogue = await response.json();
      const readyCount = catalogue.offers.filter((offer) => offer.checkout_availability !== "closed").length;
      status.dataset.state = readyCount ? "open" : "closed";
      status.textContent = readyCount
        ? catalogue.checkout_mode === "test"
          ? "Stripe test checkout is connected. Test transactions do not move money."
          : "Stripe-hosted checkout is available for the fixed-scope offers below."
        : "Secure checkout is being configured. The service scope and prices are ready; no payment can be taken from this page yet.";
      refreshButtons();
    } catch (_error) {
      status.dataset.state = "closed";
      status.textContent = "Checkout status is temporarily unavailable. No payment can be taken from this page.";
      setMessage("Please contact info@180climate.net for a written quotation.", true);
    }
  }

  acknowledgement.addEventListener("change", refreshButtons);

  buttons.forEach((button) => {
    button.addEventListener("click", async () => {
      const offer = offerFor(button);
      if (!offer || !acknowledgement.checked) return;
      button.disabled = true;
      setMessage("Preparing Stripe-hosted checkout…");
      try {
        const response = await fetch(offer.checkout_action, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ customer_approved: true, scope_acknowledged: true, currency: "SGD" }),
        });
        const data = await response.json();
        if (!response.ok || !data.checkout_url) throw new Error(data?.detail?.code || "checkout unavailable");
        window.location.assign(data.checkout_url);
      } catch (_error) {
        setMessage("Checkout is not available yet. No payment was made. Please contact info@180climate.net.", true);
        refreshButtons();
      }
    });
  });

  loadCatalogue();
})();
