document.addEventListener("DOMContentLoaded", function () {
    const btn = document.getElementById("toggleVisibility");
    const icon = btn.querySelector("i");
    const sensitiveValues = document.querySelectorAll(".sensitive");
    let hidden = false;

    btn.addEventListener("click", function () {
        hidden = !hidden;
        sensitiveValues.forEach(el => {
            if (hidden) {
                el.classList.add("blurred");
            } else {
                el.classList.remove("blurred");
            }
        });
        // Toggle Bootstrap Icon
        icon.classList.toggle("bi-eye-fill", !hidden);
        icon.classList.toggle("bi-eye-slash-fill", hidden);
    });
});

