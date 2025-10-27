(() => {
  // app/static/js/home.js
  document.addEventListener("DOMContentLoaded", function() {
    const toggleCompactBtn = document.getElementById("toggleCompact");
    const compactIcon = document.getElementById("toggleCompactIcon");
    const tableView = document.getElementById("tableView");
    const pDetailCards = document.getElementById("pDetailCards");
    toggleCompactBtn && toggleCompactBtn.addEventListener("click", function() {
      document.body.classList.toggle("compact-mode");
      if (compactIcon) {
        compactIcon.classList.toggle("fa-list");
        compactIcon.classList.toggle("fa-th-large");
      }
      toggleCompactBtn.classList.toggle("active");
    });
    const toggleVisibility = document.getElementById("toggleVisibility");
    const eyeIcon = document.getElementById("eyeIcon");
    let hidden = false;
    function maskAllSensitive(show) {
      document.querySelectorAll(".sensitive").forEach((el) => {
        const val = el.getAttribute("data-value");
        if (val !== null) {
          el.textContent = show ? val : "\u2022\u2022\u2022\u2022";
        } else {
          if (!el.dataset.orig) el.dataset.orig = el.textContent;
          el.textContent = show ? el.dataset.orig : "\u2022\u2022\u2022\u2022";
        }
      });
    }
    maskAllSensitive(true);
    toggleVisibility && toggleVisibility.addEventListener("click", () => {
      hidden = !hidden;
      maskAllSensitive(!hidden);
      eyeIcon.classList.toggle("fa-eye");
      eyeIcon.classList.toggle("fa-eye-slash");
    });
    const securityWarning = document.getElementById("securityWarning");
    if (securityWarning) {
      let dismissWarning = function() {
        securityWarning.style.display = "none";
      };
      const closeBtn = document.getElementById("closeSecurityWarning");
      closeBtn && closeBtn.addEventListener("click", dismissWarning);
      setTimeout(dismissWarning, 2e4);
    }
    document.querySelectorAll(".p-close").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const modal = btn.closest(".p-modal");
        if (modal) modal.style.display = "none";
      });
    });
  });
})();
//# sourceMappingURL=home.js.map
