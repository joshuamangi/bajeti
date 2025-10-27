(() => {
  // app/static/js/forgot_password.js
  var resetForm = document.getElementById("resetForm");
  var newPassword = document.getElementById("new_password");
  var confirmPassword = document.getElementById("confirm_password");
  var message = document.getElementById("message");
  var toggleNewPassword = document.getElementById("toggleNewPassword");
  var toggleConfirm = document.getElementById("toggleConfirm");
  var resetBtn = document.getElementById("resetBtn");
  var btnText = resetBtn.querySelector(".p-btn-text");
  var btnSpinner = resetBtn.querySelector(".p-btn-spinner");
  function validatePassword() {
    if (confirmPassword.value === "") {
      message.textContent = "";
      return;
    }
    if (newPassword.value === confirmPassword.value) {
      message.style.color = "green";
      message.textContent = "\u2705 Passwords match";
    } else {
      message.style.color = "red";
      message.textContent = "\u274C Passwords do not match";
    }
  }
  newPassword.addEventListener("input", validatePassword);
  confirmPassword.addEventListener("input", validatePassword);
  toggleNewPassword.addEventListener("click", () => {
    const type = newPassword.type === "password" ? "text" : "password";
    newPassword.type = type;
    toggleNewPassword.classList.toggle("fa-eye-slash");
  });
  toggleConfirm.addEventListener("click", () => {
    const type = confirmPassword.type === "password" ? "text" : "password";
    confirmPassword.type = type;
    toggleConfirm.classList.toggle("fa-eye-slash");
  });
  resetForm.addEventListener("submit", (e) => {
    if (newPassword.value !== confirmPassword.value) {
      e.preventDefault();
      message.style.color = "red";
      message.textContent = "\u274C Passwords do not match";
      return;
    }
    btnText.style.display = "none";
    btnSpinner.style.display = "inline-block";
    resetBtn.disabled = true;
  });
})();
//# sourceMappingURL=forgot_password.js.map
