/* PocketSmart AI — login & register forms */
(function () {
  "use strict";

  const qs = (id) => document.getElementById(id);

  function showError(el, message) {
    el.textContent = message;
    el.hidden = false;
  }
  function clearError(el) {
    el.hidden = true;
    el.textContent = "";
  }

  function setBusy(button, busy, busyLabel) {
    if (busy) {
      button.dataset.label = button.textContent;
      button.textContent = busyLabel;
      button.disabled = true;
    } else {
      button.textContent = button.dataset.label || button.textContent;
      button.disabled = false;
    }
  }

  // Password visibility toggles
  document.querySelectorAll(".password-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = qs(btn.dataset.target);
      if (!input) return;
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.textContent = show ? "🙈" : "👁";
      btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
  });

  /* ------------------------------ login ------------------------------ */
  const loginForm = qs("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const errEl = qs("login-error");
      clearError(errEl);

      const email = qs("login-email").value.trim();
      const password = qs("login-password").value;
      if (!email || !password) {
        showError(errEl, "Please enter both your email and password.");
        return;
      }

      const submit = qs("login-submit");
      setBusy(submit, true, "Logging in…");
      try {
        await PS.postJSON("/login", { email, password });
        window.location.href = "/dashboard";
      } catch (err) {
        setBusy(submit, false);
        showError(errEl, err.message);
      }
    });
  }

  /* ------------------------------ register ------------------------------ */
  const registerForm = qs("register-form");
  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const errEl = qs("register-error");
      clearError(errEl);

      const full_name = qs("reg-name").value.trim();
      const email = qs("reg-email").value.trim();
      const password = qs("reg-password").value;

      if (full_name.length < 2) {
        showError(errEl, "Please enter your full name.");
        return;
      }
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        showError(errEl, "Please enter a valid email address.");
        return;
      }
      if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) {
        showError(errEl, "Password must be at least 8 characters and include a letter and a number.");
        return;
      }

      const submit = qs("register-submit");
      setBusy(submit, true, "Creating account…");
      try {
        await PS.postJSON("/register", { full_name, email, password });
        PS.toastSuccess("Account created — welcome to PocketSmart AI!");
        window.location.href = "/dashboard";
      } catch (err) {
        setBusy(submit, false);
        showError(errEl, err.message);
      }
    });
  }
})();
