// esbuild.config.js
import { context, build } from "esbuild";
import dotenv from "dotenv";
import fs from "fs";
import copy from "esbuild-plugin-copy";

dotenv.config();

const env = process.env.ENVIRONMENT || "development";
const isWatch = env === "development";

// Ensure output dir exists
fs.mkdirSync("app/static/dist", { recursive: true });

const commonOptions = {
    entryPoints: [
        "app/static/js/index.js", //your main JS entry
        "app/static/css/index.css", //your main CSS entry
    ],
    outdir: "app/static/dist",
    bundle: true,
    sourcemap: isWatch,
    minify: !isWatch,
    loader: {
        ".css": "css",
        ".woff2": "file",
        ".woff": "file",
        ".ttf": "file",
        ".eot": "file",
    },
    logLevel: "info",
    plugins: [
        copy({
            assets: [
                {
                    from: ["app/static/fonts/**/*"],
                    to: ["app/static/dist/fonts"], //copy all fonts
                },
                {
                    from: [
                        "app/static/vendor/fontawesome/fontawesome-free-6.4.0-web/webfonts/*",
                    ],
                    to: ["app/static/dist/webfonts"], //copy Font Awesome webfonts
                },
            ],
        }),
    ],
};
// Build or watch
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
