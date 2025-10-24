const resetForm = document.getElementById("resetForm");
const newPassword = document.getElementById("new_password");
const confirmPassword = document.getElementById("confirm_password");
const message = document.getElementById("message");
const toggleNewPassword = document.getElementById("toggleNewPassword");
const toggleConfirm = document.getElementById("toggleConfirm");
const resetBtn = document.getElementById("resetBtn");
const btnText = resetBtn.querySelector(".p-btn-text");
const btnSpinner = resetBtn.querySelector(".p-btn-spinner");

function validatePassword() {
    if (confirmPassword.value === "") {
        message.textContent = "";
        return;
    }

    if (newPassword.value === confirmPassword.value) {
        message.style.color = "green";
        message.textContent = "✅ Passwords match";
    } else {
        message.style.color = "red";
        message.textContent = "❌ Passwords do not match";
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
        message.textContent = "❌ Passwords do not match";
        return;
    }

    btnText.style.display = "none";
    btnSpinner.style.display = "inline-block";
    resetBtn.disabled = true;
});