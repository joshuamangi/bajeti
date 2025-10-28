// app/static/js/globals.js
// This file must be imported AFTER main.js in index.js

// Explicitly attach all functions from main.js to window object
window.launchNav = launchNav;
window.closeNav = closeNav;
window.generateModal = generateModal;
window.showAlert = showAlert;
window.showConfirm = showConfirm;

console.log('Global functions attached to window');