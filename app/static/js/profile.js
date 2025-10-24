document.getElementById("toggleSecurityAnswer").addEventListener("click", function () {
    const input = document.getElementById("security_answer");

    if (!input) return; // Safety check in case element is missing

    if (input.type === "password") {
        input.type = "text";
        this.classList.replace("fa-eye", "fa-eye-slash");
    } else {
        input.type = "password";
        this.classList.replace("fa-eye-slash", "fa-eye");
    }
});
