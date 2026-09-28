/* PocketSmart AI — global helpers: toasts, loading overlay, fetch, formatting */
(function () {
  "use strict";

  window.PS = {};

  /* ------------------------------ formatting ------------------------------ */
  const inr = new Intl.NumberFormat("en-IN", {
    style: "currency", currency: "INR", maximumFractionDigits: 0,
  });
  PS.formatINR = (n) => inr.format(Math.round(Number(n) || 0));

  PS.formatCompact = (n) => {
    n = Number(n) || 0;
    if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`;
    if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`;
    if (n >= 1e3) return `₹${(n / 1e3).toFixed(1)}k`;
    return `₹${n}`;
  };

  /* ------------------------------ toasts ------------------------------ */
  PS.toast = (message, type = "info", timeout = 4200) => {
    const stack = document.getElementById("toast-stack");
    if (!stack) return;
    const el = document.createElement("div");
    el.className = `toast toast-${type}`;
    el.setAttribute("role", "status");
    el.textContent = message;
    stack.appendChild(el);
    setTimeout(() => {
      el.classList.add("out");
      setTimeout(() => el.remove(), 300);
    }, timeout);
  };
  PS.toastError = (msg) => PS.toast(msg, "error", 5200);
  PS.toastSuccess = (msg) => PS.toast(msg, "success");

  /* ------------------------------ loading overlay ------------------------------ */
  const OVERLAY_STEPS = [
    "Analyzing your requirements…",
    "Understanding your budget…",
    "Finding suitable recommendations…",
    "Balancing categories and prices…",
    "Preparing your personalized plan…",
  ];

  PS.overlay = (() => {
    let el, title, step, timer, idx;
    const init = () => {
      el = document.getElementById("loading-overlay");
      title = document.getElementById("overlay-title");
      step = document.getElementById("overlay-step");
    };
    return {
      show(planTitle) {
        if (!el) init();
        if (!el) return;
        title.textContent = planTitle || "Preparing your plan…";
        idx = 0;
        step.textContent = OVERLAY_STEPS[0];
        clearInterval(timer);
        timer = setInterval(() => {
          idx = (idx + 1) % OVERLAY_STEPS.length;
          step.style.opacity = "0";
          setTimeout(() => {
            step.textContent = OVERLAY_STEPS[idx];
            step.style.opacity = "1";
          }, 200);
        }, 1900);
        el.hidden = false;
        document.body.style.overflow = "hidden";
      },
      hide() {
        if (!el) return;
        clearInterval(timer);
        el.hidden = true;
        document.body.style.overflow = "";
      },
    };
  })();

  /* ------------------------------ fetch helper ------------------------------ */
  PS.postJSON = async (url, data) => {
    let response;
    try {
      response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(data),
      });
    } catch (networkError) {
      throw new Error("Network error — please check your internet connection and try again.");
    }

    let body = {};
    try { body = await response.json(); } catch (_) { /* non-JSON error body */ }

    if (response.status === 401) {
      throw new Error(body.detail || "Your session has expired. Please log in again.");
    }
    if (!response.ok) {
      throw new Error(body.detail || `Request failed (${response.status}). Please try again.`);
    }
    return body;
  };

  PS.getJSON = async (url) => {
    let response;
    try {
      response = await fetch(url, { credentials: "same-origin" });
    } catch (networkError) {
      throw new Error("Network error — please check your internet connection.");
    }
    let body = {};
    try { body = await response.json(); } catch (_) { /* ignore */ }
    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Your session has expired. Please log in again.");
      }
      throw new Error(body.detail || `Request failed (${response.status}).`);
    }
    return body;
  };

  /* ------------------------------ numeric inputs ------------------------------ */
  // Comma-grouped INR entry for budget fields.
  PS.attachBudgetField = (input, { min = 0, onChange } = {}) => {
    if (!input) return () => 0;
    const digits = () => parseInt(input.value.replace(/[^\d]/g, ""), 10) || 0;
    const render = () => {
      const v = digits();
      input.value = v ? v.toLocaleString("en-IN") : "";
    };
    input.addEventListener("input", render);
    input.addEventListener("blur", render);
    input.addEventListener("focus", () => {
      const v = digits();
      input.value = v ? String(v) : "";
    });
    return digits;
  };

  /* ------------------------------ navbar (mobile) ------------------------------ */
  document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("nav-toggle");
    const links = document.getElementById("nav-links");
    if (toggle && links) {
      toggle.addEventListener("click", () => {
        const open = links.classList.toggle("open");
        toggle.setAttribute("aria-expanded", String(open));
      });
    }
  });
})();
