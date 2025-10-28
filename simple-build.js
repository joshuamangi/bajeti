// simple-build.js
import fs from 'fs';
import path from 'path';

const files = [
    "app/static/js/main.js",
    "app/static/js/home.js",
    "app/static/js/bajeti.js",
    "app/static/js/forgot_password.js",
    "app/static/js/login.js",
    "app/static/js/profile.js",
    "app/static/js/register.js"
];

let output = '// Bajeti Application Bundle\n';
output += '(function() {\n\n';  // Start IIFE

files.forEach(file => {
    if (fs.existsSync(file)) {
        const content = fs.readFileSync(file, 'utf8');
        // Remove any existing DOMContentLoaded listeners to avoid conflicts
        const cleanedContent = content.replace(/document\.addEventListener\s*\(\s*["']DOMContentLoaded["'].*?{/g, '// DOMContentLoaded removed for bundling');
        output += cleanedContent + '\n\n';
    }
});

// Make all functions global
output += `
// Make functions globally available
window.launchNav = typeof launchNav !== 'undefined' ? launchNav : function() { console.warn('launchNav not found') };
window.closeNav = typeof closeNav !== 'undefined' ? closeNav : function() { console.warn('closeNav not found') };
window.generateModal = typeof generateModal !== 'undefined' ? generateModal : function() { console.warn('generateModal not found') };
window.showAlert = typeof showAlert !== 'undefined' ? showAlert : function() { console.warn('showAlert not found') };
window.showConfirm = typeof showConfirm !== 'undefined' ? showConfirm : function() { console.warn('showConfirm not found') };

console.log('Bajeti bundle loaded - functions attached to window');
})(); // End IIFE
`;

// Ensure output directory exists
fs.mkdirSync('app/static/dist', { recursive: true });

// Write concatenated file
fs.writeFileSync('app/static/dist/index.js', output);
console.log('✅ Simple concatenation complete');

// CSS handling remains the same
const cssFiles = [
    "app/static/css/font.css",
    "app/static/css/alert.css",
    "app/static/css/analytics.css",
    "app/static/css/forgot_password.css",
    "app/static/css/home.css",
    "app/static/css/login.css",
    "app/static/css/main.css",
    "app/static/css/modal.css",
    "app/static/css/palette.css",
    "app/static/css/profile.css",
    "app/static/css/register.css"
];

let cssOutput = '';
cssFiles.forEach(file => {
    if (fs.existsSync(file)) {
        cssOutput += fs.readFileSync(file, 'utf8') + '\n\n';
    }
});

fs.writeFileSync('app/static/dist/index.css', cssOutput);
console.log('✅ CSS concatenation complete');