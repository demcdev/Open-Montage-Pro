// Samples a Remotion composition and writes what layout-probe.js saw at each frame.
// The probe joins the bundle through a wrapper entry, so hand-authored projects are
// measured without touching their code.
//
// node scripts/layout-audit.mjs --entry <index.tsx> --composition <id> --out <file.json>
//   [--props <file.json>] [--public-dir <dir>] [--every-seconds 0.5] [--width <px> --height <px>]

import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

import { bundle } from "@remotion/bundler";
import { renderFrames, selectComposition } from "@remotion/renderer";

const LOG_PREFIX = "__OM_LAYOUT__";
const composerDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const { values: args } = parseArgs({
  options: {
    entry: { type: "string" },
    composition: { type: "string" },
    out: { type: "string" },
    props: { type: "string" },
    "public-dir": { type: "string" },
    "every-seconds": { type: "string", default: "0.5" },
    width: { type: "string" },
    height: { type: "string" },
  },
});
if (!args.entry || !args.composition || !args.out) {
  console.error("--entry, --composition and --out are required");
  process.exit(2);
}

const importPath = (path) => JSON.stringify(resolve(path).replaceAll("\\", "/"));
const inputProps = args.props ? JSON.parse(readFileSync(args.props, "utf-8")) : {};

// Lives under out/ because the bundler resolves node_modules by walking up from it.
mkdirSync(join(composerDir, "out"), { recursive: true });
const workDir = mkdtempSync(join(composerDir, "out", "layout-audit-"));
const wrapper = join(workDir, "entry.tsx");
writeFileSync(
  wrapper,
  `import ${importPath(args.entry)};\nimport ${importPath(join(composerDir, "scripts", "layout-probe.js"))};\n`,
);

try {
  const serveUrl = await bundle({
    entryPoint: wrapper,
    ignoreRegisterRootWarning: true,
    outDir: join(workDir, "bundle"),
    publicDir: args["public-dir"] ? resolve(args["public-dir"]) : join(composerDir, "public"),
  });
  const selected = await selectComposition({ serveUrl, id: args.composition, inputProps });
  const composition = args.width && args.height ? { ...selected, width: Number(args.width), height: Number(args.height) } : selected;
  const everyNthFrame = Math.max(1, Math.round(Number(args["every-seconds"]) * composition.fps));

  const samples = new Map();
  await renderFrames({
    serveUrl,
    composition,
    inputProps,
    everyNthFrame,
    imageFormat: "none",
    outputDir: join(workDir, "frames"),
    onStart: () => undefined,
    onFrameUpdate: () => undefined,
    onBrowserLog: (log) => {
      const start = log.text.indexOf(LOG_PREFIX);
      if (start === -1) return;
      const sample = JSON.parse(log.text.slice(start + LOG_PREFIX.length));
      samples.set(sample.frame, sample);
    },
  });

  writeFileSync(
    resolve(args.out),
    JSON.stringify({
      engine: "remotion",
      composition: args.composition,
      fps: composition.fps,
      width: composition.width,
      height: composition.height,
      duration_seconds: composition.durationInFrames / composition.fps,
      expected_samples: Math.ceil(composition.durationInFrames / everyNthFrame),
      samples: [...samples.values()].sort((a, b) => a.frame - b.frame),
    }),
  );
} finally {
  rmSync(workDir, { recursive: true, force: true });
}
