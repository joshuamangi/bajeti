function showToast(message, type = "success", duration = 3000) {
    const snack = document.getElementById("pSnackBar");
    snack.textContent = message;
    snack.className = `${type} show`;
    setTimeout(() => {
        snack.classList.remove("show");
    }, duration);
}

// ✅ Detect query parameters
const params = new URLSearchParams(window.location.search);
const toastType = params.get("toast");
const toastMessage = params.get("message");

if (toastMessage) {
    showToast(decodeURIComponent(toastMessage), toastType || "info");
    // Remove query params after showing toast
    window.history.replaceState({}, document.title, window.location.pathname);
}