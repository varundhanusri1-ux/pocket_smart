/* PocketSmart AI — planner forms: validation, dynamic fields, submissions */
(function () {
  "use strict";

  const qs = (id) => document.getElementById(id);

  const MIN_BUDGET = 2000;
  const OVERLAY_TITLES = {
    home: "Designing your interior plan…",
    party: "Planning your event…",
    jewelry: "Curating your jewelry picks…",
  };

  function showError(el, message) {
    el.textContent = message;
    el.hidden = false;
  }
  function clearError(el) {
    el.hidden = true;
    el.textContent = "";
  }
  function setBusy(button, busy, label) {
    if (busy) {
      button.dataset.label = button.textContent;
      button.textContent = label;
      button.disabled = true;
    } else {
      button.textContent = button.dataset.label || button.textContent;
      button.disabled = false;
    }
  }

  /* attach steppers inside a container */
  function wireSteppers(container) {
    container.querySelectorAll(".stepper").forEach((stepper) => {
      if (stepper.dataset.wired) return;
      stepper.dataset.wired = "1";
      const input = stepper.querySelector("input");
      stepper.querySelectorAll(".stepper-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          const step = parseInt(btn.dataset.step, 10);
          const next = Math.min(parseInt(input.max, 10), Math.max(parseInt(input.min, 10), (parseInt(input.value, 10) || 0) + step));
          input.value = next;
          input.dispatchEvent(new Event("input", { bubbles: true }));
        });
      });
    });
  }

  /* ==========================================================================
     HOME PLANNER
     ========================================================================== */
  const homeForm = qs("home-form");
  if (homeForm) {
    const budgetDigits = PS.attachBudgetField(qs("home-budget"));
    const roomRows = qs("room-rows");
    const addRoomBtn = qs("add-room");
    wireSteppers(homeForm);

    const roomCount = () => roomRows.querySelectorAll(".room-row").length;
    const totalRooms = () => Array.from(roomRows.querySelectorAll(".room-row"))
      .reduce((sum, row) => sum + (parseInt(row.querySelector(".room-qty").value, 10) || 0), 0);
    const activeNeeds = () => Array.from(homeForm.querySelectorAll(".toggle-card input:checked"))
      .map((i) => i.closest(".toggle-card").querySelector("strong").textContent);
    const fanCount = () => parseInt(qs("home-fans").value, 10) || 0;

    const refreshSummary = () => {
      qs("sum-budget").textContent = PS.formatINR(budgetDigits());
      qs("sum-rooms").textContent = String(totalRooms());
      const chips = qs("sum-needs");
      const labels = [...activeNeeds()];
      if (fanCount()) labels.push(`${fanCount()} fans`);
      chips.innerHTML = "";
      labels.forEach((label) => {
        const chip = document.createElement("span");
        chip.className = "chip chip-indigo";
        chip.textContent = label;
        chips.appendChild(chip);
      });
      if (!labels.length) {
        chips.innerHTML = '<span class="chip chip-amber">Select at least one requirement</span>';
      }
    };

    // room rows
    const wireRemove = (row) => {
      const btn = row.querySelector(".row-remove");
      btn.addEventListener("click", () => {
        row.remove();
        if (roomCount() === 1) {
          roomRows.querySelector(".room-row .row-remove").hidden = true;
        }
        refreshSummary();
      });
      btn.hidden = false;
    };

    addRoomBtn.addEventListener("click", () => {
      const first = roomRows.querySelector(".room-row");
      const clone = first.cloneNode(true);
      clone.querySelector("select").value = "Living Room";
      clone.querySelector(".room-qty").value = 1;
      wireRemove(clone);
      roomRows.appendChild(clone);
      if (roomCount() > 1) {
        roomRows.querySelectorAll(".row-remove").forEach((b) => { b.hidden = false; });
      }
      refreshSummary();
    });

    homeForm.addEventListener("input", refreshSummary);
    refreshSummary();

    homeForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const errEl = qs("home-error");
      const budgetErr = qs("home-budget-error");
      clearError(errEl); clearError(budgetErr);

      const budget = budgetDigits();
      if (!budget || budget < MIN_BUDGET) {
        showError(budgetErr, `Please enter a budget of at least ₹${MIN_BUDGET.toLocaleString("en-IN")}.`);
        qs("home-budget").focus();
        return;
      }
      if (!activeNeeds().length && !fanCount()) {
        showError(errEl, "Select at least one requirement (furniture, lighting, dining, decor or fans).");
        return;
      }

      const payload = {
        total_budget: budget,
        rooms: Array.from(roomRows.querySelectorAll(".room-row")).map((row) => ({
          room_type: row.querySelector(".room-type").value,
          quantity: parseInt(row.querySelector(".room-qty").value, 10) || 1,
        })),
        furniture: homeForm.elements.furniture.checked,
        lighting: homeForm.elements.lighting.checked,
        ceiling_fans: fanCount(),
        dining_table: homeForm.elements.dining_table.checked,
        decor: homeForm.elements.decor.checked,
        style: homeForm.elements.style.value || null,
        additional_requirements: homeForm.elements.additional_requirements.value.trim() || null,
      };

      const submit = qs("home-submit");
      setBusy(submit, true, "Generating…");
      PS.overlay.show(OVERLAY_TITLES.home);
      try {
        const plan = await PS.postJSON("/generate-home", payload);
        if (plan.source === "fallback") {
          PS.toast("AI is unavailable — showing a clearly-labelled demo plan.", "info", 6000);
        } else {
          PS.toastSuccess("Your interior plan is ready!");
        }
        sessionStorage.setItem("ps_last_plan", JSON.stringify(plan));
        window.location.href = "/planners/home/recommendations";
      } catch (err) {
        PS.overlay.hide();
        setBusy(submit, false);
        showError(errEl, err.message);
      }
    });
  }

  /* ==========================================================================
     PARTY PLANNER
     ========================================================================== */
  const partyForm = qs("party-form");
  if (partyForm) {
    const budgetDigits = PS.attachBudgetField(qs("party-budget"));
    wireSteppers(partyForm);

    const EVENT_HINTS = {
      birthday: "🎂 Birthdays lean toward decor, cake and entertainment; a venue is often optional.",
      wedding: "💍 Weddings prioritize catering and venue — food typically takes ~40-45% of the budget.",
      corporate: "💼 Corporate events favor a professional venue and catering over heavy decor.",
      other: "✨ Tell us more in the preferences box so the AI can tailor the split.",
    };
    const WEDDING_ONLY = ["accommodation-card"];

    const refresh = () => {
      const budget = budgetDigits();
      const guests = parseInt(qs("party-guests").value, 10) || 0;
      const perGuest = guests > 0 ? Math.floor(budget / guests) : 0;
      qs("per-guest-hint").textContent = guests > 0 ? `≈ ${PS.formatINR(perGuest)} per guest` : "";
      qs("psum-budget").textContent = PS.formatINR(budget);
      qs("psum-guests").textContent = String(guests || "—");
      qs("psum-per").textContent = guests > 0 ? PS.formatINR(perGuest) : "—";

      const eventType = qs("party-type").value;
      const hint = qs("event-hint");
      if (EVENT_HINTS[eventType]) {
        hint.textContent = EVENT_HINTS[eventType];
        hint.hidden = false;
      }
      // Accommodation is most relevant for weddings.
      const accCard = qs("accommodation-card");
      if (accCard) accCard.hidden = eventType !== "wedding" && eventType !== "other";

      const chips = qs("psum-needs");
      chips.innerHTML = "";
      partyForm.querySelectorAll(".toggle-card").forEach((card) => {
        const input = card.querySelector("input");
        if (card.hidden || !input.checked) return;
        const chip = document.createElement("span");
        chip.className = "chip chip-indigo";
        chip.textContent = card.querySelector("strong").textContent;
        chips.appendChild(chip);
      });
    };

    partyForm.addEventListener("input", refresh);
    refresh();

    partyForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const errEl = qs("party-error");
      const budgetErr = qs("party-budget-error");
      clearError(errEl); clearError(budgetErr);

      const budget = budgetDigits();
      if (!budget || budget < MIN_BUDGET) {
        showError(budgetErr, `Please enter a budget of at least ₹${MIN_BUDGET.toLocaleString("en-IN")}.`);
        qs("party-budget").focus();
        return;
      }
      const guests = parseInt(qs("party-guests").value, 10) || 0;
      if (!guests || guests < 1) {
        showError(errEl, "Please enter a guest count of at least 1.");
        qs("party-guests").focus();
        return;
      }
      const anyService = Array.from(partyForm.querySelectorAll(".toggle-card"))
        .some((card) => !card.hidden && card.querySelector("input").checked);
      if (!anyService) {
        showError(errEl, "Select at least one arrangement to plan.");
        return;
      }

      const payload = {
        total_budget: budget,
        guest_count: guests,
        event_type: qs("party-type").value,
        venue_required: partyForm.elements.venue_required.checked,
        food_catering: partyForm.elements.food_catering.checked,
        decoration: partyForm.elements.decoration.checked,
        entertainment: partyForm.elements.entertainment.checked,
        accommodation_required: partyForm.elements.accommodation_required
          ? partyForm.elements.accommodation_required.checked : false,
        additional_preferences: partyForm.elements.additional_preferences.value.trim() || null,
      };

      const submit = qs("party-submit");
      setBusy(submit, true, "Generating…");
      PS.overlay.show(OVERLAY_TITLES.party);
      try {
        const plan = await PS.postJSON("/generate-party", payload);
        if (plan.source === "fallback") {
          PS.toast("AI is unavailable — showing a clearly-labelled demo plan.", "info", 6000);
        } else {
          PS.toastSuccess("Your party plan is ready!");
        }
        sessionStorage.setItem("ps_last_plan", JSON.stringify(plan));
        window.location.href = "/planners/party/recommendations";
      } catch (err) {
        PS.overlay.hide();
        setBusy(submit, false);
        showError(errEl, err.message);
      }
    });
  }

  /* ==========================================================================
     JEWELRY PLANNER (with image upload)
     ========================================================================== */
  const jewelryForm = qs("jewelry-form");
  if (jewelryForm) {
    const budgetDigits = PS.attachBudgetField(qs("jewelry-budget"));
    wireSteppers(jewelryForm);
    const input = qs("jewelry-image");
    const zone = qs("upload-zone");
    let currentFile = null;

    const refresh = () => {
      qs("jsum-budget").textContent = PS.formatINR(budgetDigits());
      const occasion = qs("jewelry-occasion").value.trim();
      qs("jsum-occasion").textContent = occasion || "—";
      const chips = qs("jsum-needs");
      chips.innerHTML = "";
      const add = (text) => {
        const chip = document.createElement("span");
        chip.className = "chip chip-indigo";
        chip.textContent = text;
        chips.appendChild(chip);
      };
      const style = qs("jewelry-style").value;
      if (style) add(style);
      if (qs("jewelry-type").value.trim()) add(qs("jewelry-type").value.trim());
      add(currentFile ? "Outfit photo attached" : "No photo");
    };

    const setPreview = (file) => {
      currentFile = file;
      const preview = qs("upload-preview");
      const empty = qs("upload-empty");
      if (file) {
        qs("preview-img").src = URL.createObjectURL(file);
        qs("preview-name").textContent = file.name;
        qs("preview-size").textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
        preview.hidden = false;
        empty.hidden = true;
      } else {
        preview.hidden = true;
        empty.hidden = false;
        input.value = "";
      }
      refresh();
    };

    zone.addEventListener("click", (e) => {
      if (e.target.closest("#remove-image")) return;
      input.click();
    });
    zone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); }
    });
    input.addEventListener("change", () => {
      if (input.files.length) setPreview(input.files[0]);
    });
    qs("remove-image").addEventListener("click", (e) => {
      e.stopPropagation();
      setPreview(null);
    });
    ["dragover", "dragenter"].forEach((ev) =>
      zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("dragover"); }));
    ["dragleave", "drop"].forEach((ev) =>
      zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove("dragover"); }));
    zone.addEventListener("drop", (e) => {
      if (e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        setPreview(e.dataTransfer.files[0]);
      }
    });

    jewelryForm.addEventListener("input", refresh);
    refresh();

    const MAX_MB = 5;
    const ALLOWED = ["image/png", "image/jpeg", "image/jpg", "image/webp"];

    jewelryForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const errEl = qs("jewelry-error");
      const budgetErr = qs("jewelry-budget-error");
      clearError(errEl); clearError(budgetErr);

      const budget = budgetDigits();
      if (!budget || budget < 500) {
        showError(budgetErr, "Please enter a budget of at least ₹500.");
        qs("jewelry-budget").focus();
        return;
      }
      const occasion = qs("jewelry-occasion").value.trim();
      if (occasion.length < 2) {
        showError(errEl, "Please tell us the occasion (e.g. Wedding reception).");
        qs("jewelry-occasion").focus();
        return;
      }
      if (currentFile) {
        if (!ALLOWED.includes(currentFile.type)) {
          showError(errEl, "Unsupported image format. Please upload a PNG, JPG or WebP image.");
          return;
        }
        if (currentFile.size > MAX_MB * 1024 * 1024) {
          showError(errEl, `That image is too large — maximum ${MAX_MB} MB.`);
          return;
        }
      }

      const fd = new FormData();
      fd.append("total_budget", String(budget));
      fd.append("occasion", occasion);
      fd.append("style_preference", qs("jewelry-style").value || "");
      fd.append("jewelry_type", qs("jewelry-type").value.trim() || "");
      fd.append("outfit_description", qs("jewelry-outfit").value.trim() || "");
      if (currentFile) fd.append("outfit_image", currentFile);

      const submit = qs("jewelry-submit");
      setBusy(submit, true, "Generating…");
      PS.overlay.show(OVERLAY_TITLES.jewelry);
      try {
        let response;
        try {
          response = await fetch("/generate-jewelry", {
            method: "POST", body: fd, credentials: "same-origin",
          });
        } catch (networkError) {
          throw new Error("Network error — please check your internet connection and try again.");
        }
        let body = {};
        try { body = await response.json(); } catch (_) { /* ignore */ }
        if (!response.ok) {
          if (response.status === 401) throw new Error("Your session has expired. Please log in again.");
          throw new Error(body.detail || "We couldn't generate your plan. Please try again.");
        }
        if (body.source === "fallback") {
          PS.toast("AI is unavailable — showing a clearly-labelled demo plan.", "info", 6000);
        } else {
          PS.toastSuccess("Your jewelry plan is ready!");
        }
        sessionStorage.setItem("ps_last_plan", JSON.stringify(body));
        window.location.href = "/planners/jewelry/recommendations";
      } catch (err) {
        PS.overlay.hide();
        setBusy(submit, false);
        showError(errEl, err.message);
      }
    });
  }
})();
