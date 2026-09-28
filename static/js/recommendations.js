/* PocketSmart AI — recommendation results renderer.
   Uses the plan just generated (sessionStorage) or fetches from
   /recommendations-details (latest or ?plan_id=…). */
(function () {
  "use strict";

  const qs = (id) => document.getElementById(id);
  const root = qs("rec-root");
  if (!root) return;

  const PLANNER_LABEL = { home: "Home Interior", party: "Party", jewelry: "Jewelry" };
  const CATEGORY_ORDER_HINT = [
    "Furniture", "Lighting", "Fans & Cooling", "Dining", "Decor", "Contingency",
    "Food & Catering", "Venue", "Decoration", "Entertainment", "Accommodation",
    "Primary Piece", "Matching Accessories", "Finishing Touches",
  ];

  const CATEGORY_CHIPS = {
    "Furniture": "chip-indigo", "Lighting": "chip-amber", "Fans & Cooling": "chip-sky",
    "Dining": "chip-indigo", "Decor": "chip-amber", "Contingency": "chip-green",
    "Food & Catering": "chip-amber", "Venue": "chip-indigo", "Decoration": "chip-amber",
    "Entertainment": "chip-indigo", "Accommodation": "chip-sky",
    "Primary Piece": "chip-amber", "Matching Accessories": "chip-indigo", "Finishing Touches": "chip-green",
  };
  const chipClass = (category) => CATEGORY_CHIPS[category] || "chip-indigo";

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));

  /* ------------------------------ render ------------------------------ */
  function render(plan) {
    const result = plan.result || {};
    qs("rec-loading").hidden = true;
    qs("rec-title").textContent = plan.title || "Your plan";

    const badges = qs("rec-badges");
    badges.innerHTML = `
      <span class="chip ${plan.source === "fallback" ? "chip-amber" : "chip-green"}">
        ${plan.source === "fallback" ? "Demo plan" : "AI-generated (Gemini)"}
      </span>
      <span class="chip chip-indigo">${esc(PLANNER_LABEL[plan.planner_type] || plan.planner_type)}</span>
      ${result.currency ? `<span class="chip chip-sky">INR ₹</span>` : ""}
    `;

    // Demo banner
    const banner = qs("rec-demo-banner");
    if (plan.source === "fallback") {
      qs("rec-demo-text").textContent =
        "The AI service is currently unavailable, so this plan was built from PocketSmart's " +
        "simulated demo catalog. It is NOT live Gemini output or live platform data.";
      banner.hidden = false;
    } else {
      banner.hidden = true;
    }

    // Stats
    qs("rec-budget").textContent = PS.formatINR(result.budget || 0);
    qs("rec-total").textContent = PS.formatINR(result.total_estimated_cost || 0);
    const remaining = result.remaining_budget ?? 0;
    const remainingEl = qs("rec-remaining");
    remainingEl.textContent = (remaining < 0 ? "−" : "") + PS.formatINR(Math.abs(remaining));
    remainingEl.style.color = remaining < 0 ? "var(--red)" : "";

    const util = Math.max(0, Math.min(100, result.utilization_percent || 0));
    const bar = qs("rec-util-bar");
    bar.style.width = `${util}%`;
    bar.classList.toggle("over", util > 100);
    qs("rec-util-pct").textContent = `${util}% used`;
    const status = qs("rec-util-status");
    const statusText = util > 100 ? "Over budget" : util >= 95 ? "Fully allocated" : "Within budget";
    status.textContent = statusText;
    status.className = `util-status ${util > 100 ? "over" : "ok"}`;

    // Summary
    qs("rec-summary-chip").textContent = plan.source === "fallback" ? "Demo plan summary" : "AI plan summary";
    qs("rec-summary").textContent = result.summary || "";

    // Allocation
    const allocation = result.allocation || [];
    qs("rec-allocation-section").hidden = allocation.length === 0;
    const allocGrid = qs("rec-allocation");
    allocGrid.innerHTML = "";
    allocation
      .slice()
      .sort((a, b) => b.amount - a.amount)
      .forEach((a) => {
        const pct = a.percentage || (result.budget ? (a.amount / result.budget) * 100 : 0);
        const card = document.createElement("div");
        card.className = "allocation-card";
        card.innerHTML = `
          <div class="alloc-top"><strong>${esc(a.category)}</strong>
            <span class="alloc-amount">${PS.formatINR(a.amount)}</span></div>
          <div class="alloc-bar"><span style="width:${Math.min(100, pct)}%"></span></div>
          <small>${pct.toFixed(1)}% of budget${a.note ? ` · ${esc(a.note)}` : ""}</small>
        `;
        allocGrid.appendChild(card);
      });

    // Recommendations grouped by category
    const recs = result.recommendations || [];
    const recWrap = qs("rec-recommendations");
    recWrap.innerHTML = "";
    const categories = [...new Set(recs.map((r) => r.category))]
      .sort((a, b) => {
        const ia = CATEGORY_ORDER_HINT.indexOf(a), ib = CATEGORY_ORDER_HINT.indexOf(b);
        return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
      });
    categories.forEach((category) => {
      const items = recs.filter((r) => r.category === category);
      const block = document.createElement("div");
      block.className = "rec-category-block";
      block.innerHTML = `
        <div class="rec-category-head">
          <h3>${esc(category)}</h3>
          <span class="rec-category-count">${items.length} item${items.length > 1 ? "s" : ""}</span>
        </div>
        <div class="rec-cards"></div>
      `;
      const cards = block.querySelector(".rec-cards");
      items.forEach((r) => cards.appendChild(renderCard(r)));
      recWrap.appendChild(block);
    });
    if (!recs.length) {
      recWrap.innerHTML = `<div class="rec-error"><div class="empty-icon">🧐</div>
        <h3>No recommendations</h3><p>The plan came back empty — please try generating again.</p></div>`;
    }

    // Tips
    const tips = result.tips || [];
    qs("rec-tips-section").hidden = tips.length === 0;
    const tipsList = qs("rec-tips");
    tipsList.innerHTML = "";
    tips.forEach((tip) => {
      const li = document.createElement("li");
      li.textContent = tip;
      tipsList.appendChild(li);
    });

    qs("rec-content").hidden = false;
  }

  function renderCard(r) {
    const card = document.createElement("article");
    card.className = "rec-card";
    const linkHtml = r.link
      ? `<a class="rec-link" href="${esc(r.link)}" target="_blank" rel="noopener noreferrer">Visit platform ↗</a>`
      : "";
    const fallbackTag = r.source === "fallback"
      ? '<span class="rec-fallback-tag">Demo item</span>' : "";
    card.innerHTML = `
      <div class="rec-card-top">
        <span class="chip ${chipClass(r.category)}">${esc(r.category)}</span>
        ${fallbackTag}
      </div>
      <h4>${esc(r.name)}</h4>
      <div class="rec-price">${PS.formatINR(r.estimated_price)}
        <small>/ unit</small></div>
      <div class="rec-qty">Quantity: ${r.quantity} · Total ${PS.formatINR(r.total_price)}</div>
      ${r.reason ? `<div class="rec-reason"><strong>Why this fits</strong>${esc(r.reason)}</div>` : ""}
      <div class="rec-card-foot">
        <span class="rec-platform">${esc(r.platform || "Local Vendor")}</span>
        <span class="rec-budget-impact">Budget impact <b>${PS.formatINR(r.total_price)}</b></span>
        ${linkHtml}
      </div>
    `;
    return card;
  }

  /* ------------------------------ load ------------------------------ */
  function showErrorState(message) {
    qs("rec-loading").hidden = true;
    qs("rec-error-text").textContent = message;
    qs("rec-error").hidden = false;
  }

  async function load() {
    // 1) Freshly generated plan (from the planner submit).
    const raw = sessionStorage.getItem("ps_last_plan");
    const urlPlanId = new URLSearchParams(window.location.search).get("plan_id");

    if (raw && !urlPlanId) {
      try {
        const plan = JSON.parse(raw);
        sessionStorage.removeItem("ps_last_plan");
        render(plan);
        return;
      } catch (_) { /* fall through to fetch */ }
    }

    // 2) Fetch from API (specific plan or latest).
    try {
      const url = urlPlanId
        ? `/recommendations-details?plan_id=${encodeURIComponent(urlPlanId)}`
        : `/recommendations-details?planner_type=${encodeURIComponent(root.dataset.planner)}`;
      const plan = await PS.getJSON(url);
      render(plan);
    } catch (err) {
      if (err.message.includes("session has expired")) {
        window.location.href = "/login";
        return;
      }
      showErrorState(err.message);
    }
  }

  document.addEventListener("DOMContentLoaded", load);
})();
