document.addEventListener('DOMContentLoaded', function () {
    // Compact mode toggle - only if elements exist
    const toggleCompactBtn = document.getElementById('toggleCompact');
    if (toggleCompactBtn) {
        const compactIcon = document.getElementById('toggleCompactIcon');

        toggleCompactBtn.addEventListener('click', function () {
            document.body.classList.toggle('compact-mode');

            if (compactIcon) {
                compactIcon.classList.toggle('fa-list');
                compactIcon.classList.toggle('fa-th-large');
            }

            toggleCompactBtn.classList.toggle('active');
        });
    }

    // Sensitive data visibility toggle - only if elements exist
    const toggleVisibility = document.getElementById('toggleVisibility');
    if (toggleVisibility) {
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

        toggleVisibility.addEventListener('click', () => {
            hidden = !hidden;
            maskAllSensitive(!hidden);
            if (eyeIcon) {
                eyeIcon.classList.toggle('fa-eye');
                eyeIcon.classList.toggle('fa-eye-slash');
            }
        });
    }

    // Security warning auto-dismiss - only if element exists
    const securityWarning = document.getElementById('securityWarning');
    if (securityWarning) {
        const closeBtn = document.getElementById('closeSecurityWarning');

        function dismissWarning() {
            securityWarning.style.display = 'none';
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', dismissWarning);
        }
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

    // Check if showConfirm function exists
    if (typeof showConfirm === 'function') {
        showConfirm('Please confirm', message, function (confirmed) {
            if (confirmed) form.submit();
        });
    } else {
        // Fallback to native confirm
        if (confirm(message)) {
            form.submit();
        }
    }

    return false;
}

// Make confirmSubmit globally available
if (typeof window !== 'undefined') {
    window.confirmSubmit = confirmSubmit;
}