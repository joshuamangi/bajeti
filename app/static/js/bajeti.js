document.addEventListener("DOMContentLoaded", function () {
    const toggleBtn = document.getElementById("toggleVisibility");

    if (toggleBtn) {
        const icon = toggleBtn.querySelector("i");
        const sensitiveValues = document.querySelectorAll(".sensitive");
        let hidden = false;

        toggleBtn.addEventListener("click", function () {
            hidden = !hidden;

            sensitiveValues.forEach(el => {
                el.classList.toggle("blurred", hidden);
            });

            if (icon) {
                icon.classList.toggle("bi-eye-fill", !hidden);
                icon.classList.toggle("bi-eye-slash-fill", hidden);
            }
        });
    }

    const resetForm = document.getElementById("resetForm");

    if (resetForm) {
        resetForm.addEventListener("submit", function (event) {
            const email = document.getElementById("email");
            const securityAnswer = document.getElementById("security_answer");
            const newPassword = document.getElementById("new_password");
            const confirmPassword = document.getElementById("confirm_password");

            if (!email || !securityAnswer || !newPassword || !confirmPassword) return;

            // Remove previous validation states
            email.classList.remove("is-invalid");
            securityAnswer.classList.remove("is-invalid");
            newPassword.classList.remove("is-invalid");
            confirmPassword.classList.remove("is-invalid");

            let valid = true;

            // Validate email
            if (!email.value.trim()) {
                email.classList.add("is-invalid");
                valid = false;
            }

            // Validate security answer
            if (!securityAnswer.value.trim()) {
                securityAnswer.classList.add("is-invalid");
                valid = false;
            }

            // Validate new password
            if (!newPassword.value.trim()) {
                newPassword.classList.add("is-invalid");
                valid = false;
            }

            // Validate confirm password
            if (!confirmPassword.value.trim() || confirmPassword.value !== newPassword.value) {
                confirmPassword.classList.add("is-invalid");
                valid = false;
            }

            // Prevent form submission if validation fails
            if (!valid) {
                event.preventDefault();
                event.stopPropagation();
            }
        });
    }
});