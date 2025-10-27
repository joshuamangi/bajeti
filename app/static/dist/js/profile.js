(() => {
  // app/static/js/profile.js
  document.getElementById("toggleSecurityAnswer").addEventListener("click", function() {
    const input = document.getElementById("security_answer");
    if (!input) return;
    if (input.type === "password") {
      input.type = "text";
      this.classList.replace("fa-eye", "fa-eye-slash");
    } else {
      input.type = "password";
      this.classList.replace("fa-eye-slash", "fa-eye");
    }
  });
})();
//# sourceMappingURL=profile.js.map
