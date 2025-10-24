document.addEventListener('DOMContentLoaded', function () {
    const toggleCompactBtn = document.getElementById('toggleCompact');
    const compactIcon = document.getElementById('toggleCompactIcon');
    const tableView = document.getElementById('tableView');
    const pDetailCards = document.getElementById('pDetailCards');

    // Compact mode toggle functionality
    toggleCompactBtn && toggleCompactBtn.addEventListener('click', function () {
        document.body.classList.toggle('compact-mode');

        if (compactIcon) {
            compactIcon.classList.toggle('fa-list');
            compactIcon.classList.toggle('fa-th-large');
        }

        toggleCompactBtn.classList.toggle('active');
    });

    // Sensitive data visibility toggle
    const toggleVisibility = document.getElementById('toggleVisibility');
    const eyeIcon = document.getElementById('eyeIcon');
    let hidden = false;

    function maskAllSensitive(show) {
        document.querySelectorAll('.sensitive').forEach(el => {
            const val = el.getAttribute('data-value');

            if (val !== null) {
                el.textContent = show ? val : '••••';
            } else {
                if (!el.dataset.orig) el.dataset.orig = el.textContent;
                el.textContent = show ? el.dataset.orig : '••••';
            }
        });
    }

    // Initialize with sensitive data visible
    maskAllSensitive(true);

    toggleVisibility && toggleVisibility.addEventListener('click', () => {
        hidden = !hidden;
        maskAllSensitive(!hidden);
        eyeIcon.classList.toggle('fa-eye');
        eyeIcon.classList.toggle('fa-eye-slash');
    });

    // Security warning auto-dismiss
    const securityWarning = document.getElementById('securityWarning');

    if (securityWarning) {
        const closeBtn = document.getElementById('closeSecurityWarning');

        function dismissWarning() {
            securityWarning.style.display = 'none';
        }

        closeBtn && closeBtn.addEventListener('click', dismissWarning);
        setTimeout(dismissWarning, 20000); // Auto-dismiss after 20 seconds
    }

    // Modal close functionality
    document.querySelectorAll('.p-close').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const modal = btn.closest('.p-modal');
            if (modal) modal.style.display = 'none';
        });
    });
});

// Form confirmation dialog
function confirmSubmit(formOrEvt, message) {
    let form = formOrEvt;

    if (formOrEvt instanceof Event) {
        form = formOrEvt.target.closest('form');
        if (!form) return false;
    }

    showConfirm('Please confirm', message, function (confirmed) {
        if (confirmed) form.submit();
    });

    return false;
}