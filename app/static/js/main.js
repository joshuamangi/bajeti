function launchNav() {
    const sidenav = document.getElementById("pSideNav");
    const overlay = document.getElementById("pOverlay");
    sidenav.style.width = "250px";
    overlay.classList.add("show");
    document.body.style.overflow = "hidden";
}

function closeNav() {
    const sidenav = document.getElementById("pSideNav");
    const overlay = document.getElementById("pOverlay");
    sidenav.style.width = "0";
    overlay.classList.remove("show");
    document.body.style.overflow = "";
}

function generateModal(modalName, closeModal, modalBtn) {
    const modal = document.getElementById(modalName);
    modal.style.display = "flex";

    const closeBtn = document.getElementById(closeModal);
    const closeModalBtn = document.getElementById(modalBtn);

    closeBtn.onclick = closeModalBtn.onclick = () => {
        modal.style.display = "none";
    };

    window.onclick = (event) => {
        if (event.target === modal) {
            modal.style.display = "none";
        }
    };
}

function showAlert(title, message, onOk) {
    const modal = document.getElementById("pAlert");
    document.getElementById("pAlertTitle").textContent = title;
    document.getElementById("pAlertMessage").textContent = message;
    modal.classList.add("show");

    const okBtn = document.getElementById("pAlertOk");
    okBtn.onclick = () => {
        modal.classList.remove("show");
        if (onOk) onOk();
    };

    window.onclick = (e) => {
        if (e.target === modal) modal.classList.remove("show");
    };
}

function showConfirm(title, message, onConfirm) {
    const modal = document.getElementById("pConfirm");
    document.getElementById("pConfirmTitle").textContent = title;
    document.getElementById("pConfirmMessage").textContent = message;
    modal.classList.add("show");

    const okBtn = document.getElementById("pConfirmOk");
    const cancelBtn = document.getElementById("pConfirmCancel");

    okBtn.onclick = () => {
        modal.classList.remove("show");
        if (onConfirm) onConfirm(true);
    };

    cancelBtn.onclick = () => {
        modal.classList.remove("show");
        if (onConfirm) onConfirm(false);
    };

    window.onclick = (e) => {
        if (e.target === modal) modal.classList.remove("show");
    };
}