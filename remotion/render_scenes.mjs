import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { bundle } from "@remotion/bundler";
import { openBrowser, renderMedia, selectComposition } from "@remotion/renderer";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  const jobsPath = process.argv[2];
  if (!jobsPath || !fs.existsSync(jobsPath)) {
    console.error("Usage: node render_scenes.mjs <jobs.json>");
    process.exit(1);
  }

  const jobs = JSON.parse(fs.readFileSync(jobsPath, "utf-8"));
  if (!Array.isArray(jobs) || jobs.length === 0) {
    console.log("[Remotion] No scenes to render.");
    return;
  }

  // Support both remotion/src/index.js and fallback remotion/index.js
  let entryPoint = path.resolve(__dirname, "src/index.js");
  if (!fs.existsSync(entryPoint)) {
    const altEntry = path.resolve(__dirname, "index.js");
    if (fs.existsSync(altEntry)) {
      entryPoint = altEntry;
    } else {
      console.error(`[Remotion] Entry point not found at ${entryPoint} or ${altEntry}`);
      process.exit(1);
    }
  }

  console.log(`[Remotion] Bundling composition from ${entryPoint} for ${jobs.length} animated scenes...`);
  const serveUrl = await bundle({
    entryPoint,
    webpackOverride: (config) => config,
  });

  const browser = await openBrowser("chrome");
  try {
    let done = 0;
    for (const job of jobs) {
      const inputProps = {
        kind: job.kind || "title_card",
        heading: job.heading || "ডকুমেন্টারি তথ্য",
        subheading: job.subheading || "",
        items: Array.isArray(job.items) ? job.items : [],
        accent: job.accent || "gold",
        colorGrade: job.color_grade || "cinematic_teal",
        videoTheme: job.video_theme || "cinematic_dark",
        duration: Number(job.duration || 5.0),
      };

      const composition = await selectComposition({
        serveUrl,
        id: "DocGraphic",
        inputProps,
        puppeteerInstance: browser,
      });

      await renderMedia({
        composition,
        serveUrl,
        codec: "h264",
        pixelFormat: "yuv420p",
        crf: 20,
        outputLocation: job.output_path,
        inputProps,
        puppeteerInstance: browser,
        concurrency: 2,
      });

      done += 1;
      console.log(`[Remotion] Rendered ${done}/${jobs.length}: ${path.basename(job.output_path)}`);
    }
  } finally {
    await browser.close({ silent: true });
  }
}

main().catch((err) => {
  console.error("[Remotion] Fatal render error:", err);
  process.exit(1);
});
