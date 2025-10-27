document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("form");
    const loginBtn = document.getElementById("loginBtn");
    const btnText = loginBtn.querySelector(".p-btn-text");
    const btnSpinner = loginBtn.querySelector(".p-btn-spinner");

    form.addEventListener("submit", (e) => {
        btnText.style.display = "none";
        btnSpinner.style.display = "inline-block";
        loginBtn.disabled = true;
    });
});