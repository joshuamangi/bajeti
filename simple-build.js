// simple-build.js - Alternative to esbuild
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

let output = '';
files.forEach(file => {
    if (fs.existsSync(file)) {
        output += fs.readFileSync(file, 'utf8') + '\n\n';
    }
});

// Ensure output directory exists
fs.mkdirSync('app/static/dist', { recursive: true });

// Write concatenated file
fs.writeFileSync('app/static/dist/index.js', output);
console.log('✅ Simple concatenation complete');

// Also handle CSS
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