function launchNav() {
    const sidenav = document.getElementById("pSideNav");
    const overlay = document.getElementById("pOverlay");

    if (sidenav && overlay) {
        sidenav.style.width = "250px";
        overlay.classList.add("show");
        document.body.style.overflow = "hidden";
    }
}

function closeNav() {
    const sidenav = document.getElementById("pSideNav");
    const overlay = document.getElementById("pOverlay");

    if (sidenav && overlay) {
        sidenav.style.width = "0";
        overlay.classList.remove("show");
        document.body.style.overflow = "";
    }
}

function generateModal(modalName, closeModal, modalBtn) {
    const modal = document.getElementById(modalName);
    if (!modal) {
        console.warn('Modal not found:', modalName);
        return;
    }

    modal.style.display = "flex";

    const closeBtn = document.getElementById(closeModal);
    const closeModalBtn = document.getElementById(modalBtn);

    const closeHandler = () => {
        modal.style.display = "none";
    };

    if (closeBtn) closeBtn.onclick = closeHandler;
    if (closeModalBtn) closeModalBtn.onclick = closeHandler;

    // Store original onclick handler to avoid conflicts
    const originalOnClick = window.onclick;
    window.onclick = (event) => {
        // Call original handler if it exists
        if (originalOnClick) originalOnClick(event);

        if (event.target === modal) {
            modal.style.display = "none";
            // Restore original handler after closing
            window.onclick = originalOnClick;
        }
    };
}

function showAlert(title, message, onOk) {
    const modal = document.getElementById("pAlert");
    if (!modal) {
        // Fallback to native alert
        alert(`${title}: ${message}`);
        if (onOk) onOk();
        return;
    }

    const titleEl = document.getElementById("pAlertTitle");
    const messageEl = document.getElementById("pAlertMessage");

    if (titleEl) titleEl.textContent = title;
    if (messageEl) messageEl.textContent = message;

    modal.classList.add("show");

    const okBtn = document.getElementById("pAlertOk");
    if (okBtn) {
        okBtn.onclick = () => {
            modal.classList.remove("show");
            if (onOk) onOk();
        };
    }

    // Store original onclick handler
    const originalOnClick = window.onclick;
    window.onclick = (e) => {
        if (originalOnClick) originalOnClick(e);

        if (e.target === modal) {
            modal.classList.remove("show");
            window.onclick = originalOnClick;
            if (onOk) onOk();
        }
    };
}

function showConfirm(title, message, onConfirm) {
    const modal = document.getElementById("pConfirm");
    if (!modal) {
        // Fallback to native confirm
        const result = confirm(`${title}: ${message}`);
        if (onConfirm) onConfirm(result);
        return;
    }

    const titleEl = document.getElementById("pConfirmTitle");
    const messageEl = document.getElementById("pConfirmMessage");

    if (titleEl) titleEl.textContent = title;
    if (messageEl) messageEl.textContent = message;

    modal.classList.add("show");

    const okBtn = document.getElementById("pConfirmOk");
    const cancelBtn = document.getElementById("pConfirmCancel");

    if (okBtn) {
        okBtn.onclick = () => {
            modal.classList.remove("show");
            if (onConfirm) onConfirm(true);
        };
    }

    if (cancelBtn) {
        cancelBtn.onclick = () => {
            modal.classList.remove("show");
            if (onConfirm) onConfirm(false);
        };
    }

    // Store original onclick handler
    const originalOnClick = window.onclick;
    window.onclick = (e) => {
        if (originalOnClick) originalOnClick(e);

        if (e.target === modal) {
            modal.classList.remove("show");
            window.onclick = originalOnClick;
            if (onConfirm) onConfirm(false);
        }
    };
}

function displayToastNotification() {
    const toast = document.getElementById('pSnackBar');
    toast.className = "show";
    setTimeout(function () {
        toast.className = toast.className.replace("show", "");
    }, 3000);
}

// Make functions globally available with safety checks
if (typeof window !== 'undefined') {
    window.launchNav = launchNav;
    window.closeNav = closeNav;
    window.generateModal = generateModal;
    window.showAlert = showAlert;
    window.showConfirm = showConfirm;
}