// Renders chosen moments of a composition as stills, so a review can happen before
// the full render. The bundle is the render's own, so what it shows is what ships.
//
// node scripts/preview-frames.mjs --entry <index.tsx> --composition <id> --out-dir <dir>
//   --times 1,3.5,12 [--props <file.json>] [--public-dir <dir>] [--scale 0.5]

import { mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

import { bundle } from "@remotion/bundler";
import { openBrowser, renderStill, selectComposition } from "@remotion/renderer";

const composerDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const { values: args } = parseArgs({
  options: {
    entry: { type: "string" },
    composition: { type: "string" },
    "out-dir": { type: "string" },
    times: { type: "string" },
    props: { type: "string" },
    "public-dir": { type: "string" },
    scale: { type: "string", default: "0.5" },
  },
});
if (!args.entry || !args.composition || !args["out-dir"] || !args.times) {
  console.error("--entry, --composition, --out-dir and --times are required");
  process.exit(2);
}

const inputProps = args.props ? JSON.parse(readFileSync(args.props, "utf-8")) : {};
const outDir = resolve(args["out-dir"]);
mkdirSync(outDir, { recursive: true });
mkdirSync(join(composerDir, "out"), { recursive: true });
const workDir = mkdtempSync(join(composerDir, "out", "preview-frames-"));

const browser = await openBrowser("chrome");
try {
  const serveUrl = await bundle({
    entryPoint: resolve(args.entry),
    outDir: join(workDir, "bundle"),
    publicDir: args["public-dir"] ? resolve(args["public-dir"]) : join(composerDir, "public"),
  });
  const composition = await selectComposition({ serveUrl, id: args.composition, inputProps, puppeteerInstance: browser });
  for (const time of args.times.split(",").map(Number)) {
    await renderStill({
      serveUrl,
      composition,
      inputProps,
      frame: Math.min(Math.round(time * composition.fps), composition.durationInFrames - 1),
      imageFormat: "jpeg",
      jpegQuality: 80,
      scale: Number(args.scale),
      output: join(outDir, `frame_${time.toFixed(2).padStart(8, "0")}.jpg`),
      puppeteerInstance: browser,
    });
  }
} finally {
  await browser.close({ silent: true });
  rmSync(workDir, { recursive: true, force: true });
}
