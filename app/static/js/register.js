(function () {
    const password = document.getElementById("password");
    const confirmPassword = document.getElementById("confirm_password");
    const message = document.getElementById("message");

    // Only run if registration form exists
    if (password && confirmPassword) {
        function validatePassword() {
            if (confirmPassword.value === "") {
                if (message) message.textContent = "";
                return;
            }

            if (password.value === confirmPassword.value) {
                if (message) {
                    message.style.color = "green";
                    message.textContent = "✅ Passwords match";
                }
            } else {
                if (message) {
                    message.style.color = "red";
                    message.textContent = "❌ Passwords do not match";
                }
            }
        }

        password.addEventListener("input", validatePassword);
        confirmPassword.addEventListener("input", validatePassword);

        const togglePassword = document.getElementById("togglePassword");
        const toggleConfirm = document.getElementById("toggleConfirm");

        if (togglePassword) {
            togglePassword.addEventListener("click", () => {
                const type = password.getAttribute("type") === "password" ? "text" : "password";
                password.setAttribute("type", type);
                togglePassword.classList.toggle("fa-eye-slash");
            });
        }

        if (toggleConfirm) {
            toggleConfirm.addEventListener("click", () => {
                const type = confirmPassword.getAttribute("type") === "password" ? "text" : "password";
                confirmPassword.setAttribute("type", type);
                toggleConfirm.classList.toggle("fa-eye-slash");
            });
        }

        const registerBtn = document.getElementById("registerBtn");
        const registerForm = document.querySelector("form");

        if (registerBtn && registerForm) {
            const btnText = registerBtn.querySelector(".p-btn-text");
            const btnSpinner = registerBtn.querySelector(".p-btn-spinner");

            registerForm.addEventListener("submit", () => {
                if (btnText && btnSpinner) {
                    btnText.style.display = "none";
                    btnSpinner.style.display = "inline-block";
                    registerBtn.disabled = true;
                }
            });
        }
    }
})();