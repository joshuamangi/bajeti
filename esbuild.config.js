// esbuild.config.js
import { context, build } from "esbuild";
import dotenv from "dotenv";
import fs from "fs";

dotenv.config();
const env = process.env.ENVIRONMENT || "development";
const isWatch = env === "development";

// Input lists
const jsFiles = [
    "app/static/js/main.js",
    "app/static/js/home.js",
    "app/static/js/profile.js",
    "app/static/js/forgot_password.js",
];

const cssFiles = [
    "app/static/css/palette.css",
    "app/static/css/main.css",
    "app/static/css/home.css",
    "app/static/css/login.css",
    "app/static/css/register.css",
    "app/static/css/profile.css",
    "app/static/css/forgot_password.css",
    "app/static/css/analytics.css",
    "app/static/css/modal.css",
    "app/static/css/alert.css",
];

// Ensure output dir exists
fs.mkdirSync("app/static/dist", { recursive: true });

const commonOptions = {
    entryPoints: [...jsFiles, ...cssFiles],
    outdir: "app/static/dist", // ✅ MUST use outdir when multiple input files
    bundle: true,
    sourcemap: isWatch,
    minify: !isWatch,
    loader: { ".css": "css" },
    logLevel: "info",
};

async function run() {
    if (isWatch) {
        const ctx = await context(commonOptions);
        console.log("👀 Watching for changes...");
        await ctx.watch();
    } else {
        await build(commonOptions);
        console.log("✅ Production build complete");
    }
}

run().catch((e) => {
    console.error(e);
    process.exit(1);
});
