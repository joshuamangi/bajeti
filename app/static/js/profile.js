// Only run if the security answer toggle exists
const toggleSecurityAnswer = document.getElementById("toggleSecurityAnswer");
if (toggleSecurityAnswer) {
    toggleSecurityAnswer.addEventListener("click", function () {
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
}