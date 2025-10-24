const password = document.getElementById("password");
const confirmPassword = document.getElementById("confirm_password");
const message = document.getElementById("message");

function validatePassword() {
    if (confirmPassword.value === "") {
        message.textContent = "";
        return;
    }

    if (password.value === confirmPassword.value) {
        message.style.color = "green";
        message.textContent = "✅ Passwords match";
    } else {
        message.style.color = "red";
        message.textContent = "❌ Passwords do not match";
    }
}

password.addEventListener("input", validatePassword);
confirmPassword.addEventListener("input", validatePassword);

const togglePassword = document.getElementById("togglePassword");
const toggleConfirm = document.getElementById("toggleConfirm");

togglePassword.addEventListener("click", () => {
    const type = password.getAttribute("type") === "password" ? "text" : "password";
    password.setAttribute("type", type);
    togglePassword.classList.toggle("fa-eye-slash");
});

toggleConfirm.addEventListener("click", () => {
    const type = confirmPassword.getAttribute("type") === "password" ? "text" : "password";
    confirmPassword.setAttribute("type", type);
    toggleConfirm.classList.toggle("fa-eye-slash");
});

const registerBtn = document.getElementById("registerBtn");
const btnText = registerBtn.querySelector(".p-btn-text");
const btnSpinner = registerBtn.querySelector(".p-btn-spinner");
const registerForm = document.querySelector("form");

registerForm.addEventListener("submit", () => {
    btnText.style.display = "none";
    btnSpinner.style.display = "inline-block";
    registerBtn.disabled = true;
});