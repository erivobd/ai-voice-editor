const express = require("express");
const multer = require("multer");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const os = require("os");

const app = express();
const PORT = Number(process.env.PORT || 3000);
const MAX_UPLOAD_MB = Number(process.env.MAX_UPLOAD_MB || 150);
const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;

const GITHUB_TOKEN = (process.env.GITHUB_TOKEN || "").trim();
const GITHUB_OWNER = (process.env.GITHUB_OWNER || "").trim();
const GITHUB_REPO = (process.env.GITHUB_REPO || "").trim();
const GITHUB_WORKFLOW_FILE = (process.env.GITHUB_WORKFLOW_FILE || "documentary-maker.yml").trim();
const GITHUB_BRANCH = (process.env.GITHUB_BRANCH || "main").trim();
const APP_ACCESS_PIN = (process.env.APP_ACCESS_PIN || "").trim();

const ALLOWED_EXTS = new Set([".mp3", ".wav", ".m4a", ".aac", ".flac"]);
const VALID_THEMES = new Set([
  "cinematic_dark",
  "crimson_noir",
  "vox_colorful",
  "editorial_paper",
  "vibrant_gradient",
  "minimal_light"
]);
const UPLOAD_TMP_DIR = path.join(os.tmpdir(), "doc_uploads");
fs.mkdirSync(UPLOAD_TMP_DIR, { recursive: true });

app.use(express.json({ limit: "2mb" }));
app.use(express.static(path.join(__dirname, "public")));

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOAD_TMP_DIR),
  filename: (_req, file, cb) => {
    const ext = path.extname(file.originalname || "").toLowerCase();
    cb(null, `upload_${Date.now()}_${crypto.randomBytes(4).toString("hex")}${ext}`);
  }
});

const upload = multer({
  storage,
  limits: { fileSize: MAX_UPLOAD_BYTES },
  fileFilter: (_req, file, cb) => {
    const ext = path.extname(file.originalname || "").toLowerCase();
    if (!ALLOWED_EXTS.has(ext)) {
      return cb(new Error("Unsupported audio format. Use MP3, WAV, M4A, AAC, or FLAC."));
    }
    cb(null, true);
  }
});

function timingSafeMatch(a, b) {
  const bufA = Buffer.from(String(a || ""), "utf8");
  const bufB = Buffer.from(String(b || ""), "utf8");
  if (bufA.length !== bufB.length) return false;
  return crypto.timingSafeEqual(bufA, bufB);
}

function requirePin(req, res, next) {
  if (!APP_ACCESS_PIN) return next();
  const pin = req.headers["x-access-pin"] || req.query.pin || "";
  if (!timingSafeMatch(pin, APP_ACCESS_PIN)) {
    return res.status(401).json({ error: "Invalid or missing Access PIN." });
  }
  next();
}

function ensureGithubConfig() {
  if (!GITHUB_TOKEN || !GITHUB_OWNER || !GITHUB_REPO) {
    throw new Error("Server missing GitHub configuration (GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO).");
  }
}

async function ghRequest(apiPath, options = {}) {
  ensureGithubConfig();
  const url = apiPath.startsWith("http")
    ? apiPath
    : `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}${apiPath}`;

  const headers = {
    Authorization: `Bearer ${GITHUB_TOKEN}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "ai-documentary-video-maker",
    ...(options.headers || {})
  };

  return fetch(url, { ...options, headers });
}

async function uploadReleaseAsset(release, assetName, contentType, bodyBufferOrStream, contentLength) {
  const uploadBase = release.upload_url.replace(/\{.*$/, "");
  const uploadUrl = `${uploadBase}?name=${encodeURIComponent(assetName)}`;
  const headers = {
    Authorization: `Bearer ${GITHUB_TOKEN}`,
    Accept: "application/vnd.github+json",
    "Content-Type": contentType,
    "User-Agent": "ai-documentary-video-maker"
  };
  if (typeof contentLength === "number") {
    headers["Content-Length"] = String(contentLength);
  }
  const fetchOpts = {
    method: "POST",
    headers,
    body: bodyBufferOrStream
  };
  if (typeof bodyBufferOrStream?.pipe === "function") {
    fetchOpts.duplex = "half";
  }
  const res = await fetch(uploadUrl, fetchOpts);
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Failed uploading asset ${assetName}: ${res.status} ${txt.slice(0, 400)}`);
  }
  return res.json();
}

app.get("/api/health", (_req, res) => {
  res.json({
    ok: true,
    pinRequired: Boolean(APP_ACCESS_PIN),
    maxUploadMb: MAX_UPLOAD_MB
  });
});

app.post("/api/auth/verify", (req, res) => {
  if (!APP_ACCESS_PIN) return res.json({ ok: true, pinRequired: false });
  const pin = req.body?.pin || req.headers["x-access-pin"] || "";
  if (!timingSafeMatch(pin, APP_ACCESS_PIN)) {
    return res.status(401).json({ ok: false, error: "PIN সঠিক নয়।" });
  }
  res.json({ ok: true, pinRequired: true });
});

app.post("/api/jobs", requirePin, upload.single("audio"), async (req, res) => {
  const tempFile = req.file?.path;
  try {
    if (!req.file) {
      return res.status(400).json({ error: "অডিও ফাইল নির্বাচন করুন।" });
    }
    ensureGithubConfig();

    const ext = path.extname(req.file.originalname || ".mp3").toLowerCase();
    const jobId = `doc-${Date.now()}-${crypto.randomBytes(3).toString("hex")}`;
    const docTitle = String(req.body?.title || "").trim().slice(0, 120);
    const subtitles = String(req.body?.subtitles || "true") === "false" ? "false" : "true";
    const bgMusic = String(req.body?.bg_music || "true") === "false" ? "false" : "true";
    const rawTheme = String(req.body?.video_theme || "cinematic_dark").trim();
    const videoTheme = VALID_THEMES.has(rawTheme) ? rawTheme : "cinematic_dark";

    const relRes = await ghRequest("/releases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tag_name: jobId,
        target_commitish: GITHUB_BRANCH,
        name: docTitle ? `${docTitle} (${jobId})` : jobId,
        body: JSON.stringify({
          job_id: jobId,
          title: docTitle,
          video_theme: videoTheme,
          created_at: new Date().toISOString()
        }),
        draft: false,
        prerelease: false
      })
    });

    if (!relRes.ok) {
      const errTxt = await relRes.text();
      throw new Error(`Could not create job release: ${relRes.status} ${errTxt.slice(0, 400)}`);
    }
    const release = await relRes.json();

    const stat = fs.statSync(tempFile);
    const audioStream = fs.createReadStream(tempFile);
    await uploadReleaseAsset(
      release,
      `original_audio${ext}`,
      req.file.mimetype || "application/octet-stream",
      audioStream,
      stat.size
    );

    const initialStatus = {
      job_id: jobId,
      title: docTitle,
      video_theme: videoTheme,
      stage_key: "uploading_audio",
      stage: "Uploading Audio",
      percent: 5,
      message: "অডিও আপলোড সম্পন্ন হয়েছে। AI ওয়ার্কার চালু হচ্ছে...",
      error: null,
      updated_at: new Date().toISOString()
    };
    const statusBuf = Buffer.from(JSON.stringify(initialStatus, null, 2), "utf8");
    await uploadReleaseAsset(release, "status.json", "application/json", statusBuf, statusBuf.length);

    const wfRes = await ghRequest(`/actions/workflows/${encodeURIComponent(GITHUB_WORKFLOW_FILE)}/dispatches`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ref: GITHUB_BRANCH,
        inputs: {
          job_id: jobId,
          title: docTitle,
          subtitles,
          bg_music: bgMusic,
          video_theme: videoTheme
        }
      })
    });

    if (!wfRes.ok) {
      const errTxt = await wfRes.text();
      throw new Error(`Workflow dispatch failed: ${wfRes.status} ${errTxt.slice(0, 400)}`);
    }

    res.status(201).json({
      ok: true,
      job_id: jobId,
      status: initialStatus
    });
  } catch (err) {
    console.error("Create job error:", err);
    res.status(500).json({ error: err.message || "জব শুরু করতে সমস্যা হয়েছে।" });
  } finally {
    if (tempFile && fs.existsSync(tempFile)) {
      fs.unlink(tempFile, () => {});
    }
  }
});

app.get("/api/jobs", requirePin, async (_req, res) => {
  try {
    const relRes = await ghRequest("/releases?per_page=20");
    if (!relRes.ok) {
      return res.status(relRes.status).json({ error: "আগের কাজগুলো লোড করা যায়নি।" });
    }
    const releases = await relRes.json();
    const jobs = releases
      .filter((r) => String(r.tag_name || "").startsWith("doc-"))
      .map((r) => {
        const assetNames = (r.assets || []).map((a) => a.name);
        return {
          job_id: r.tag_name,
          name: r.name,
          created_at: r.created_at,
          has_video: assetNames.includes("final_documentary.mp4"),
          assets: assetNames
        };
      });
    res.json({ jobs });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get("/api/jobs/:jobId/status", requirePin, async (req, res) => {
  try {
    const { jobId } = req.params;
    const relRes = await ghRequest(`/releases/tags/${encodeURIComponent(jobId)}`);
    if (!relRes.ok) {
      return res.status(404).json({ error: "জবটি খুঁজে পাওয়া যায়নি।" });
    }
    const release = await relRes.json();
    const assets = release.assets || [];
    const statusAsset = assets.find((a) => a.name === "status.json");

    let statusData = {
      job_id: jobId,
      stage_key: "uploading_audio",
      stage: "Uploading Audio",
      percent: 5,
      message: "ওয়ার্কার শুরু হওয়ার অপেক্ষায় আছে...",
      error: null
    };

    if (statusAsset) {
      const sRes = await fetch(statusAsset.url, {
        headers: {
          Authorization: `Bearer ${GITHUB_TOKEN}`,
          Accept: "application/octet-stream",
          "User-Agent": "ai-documentary-video-maker",
          "Cache-Control": "no-cache"
        }
      });
      if (sRes.ok) {
        try {
          statusData = await sRes.json();
        } catch (_e) {}
      }
    }

    const availableAssets = {};
    for (const a of assets) {
      availableAssets[a.name] = { size: a.size, updated_at: a.updated_at };
    }

    res.setHeader("Cache-Control", "no-store");
    res.json({
      ...statusData,
      has_video: Boolean(availableAssets["final_documentary.mp4"]),
      assets: availableAssets
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get("/api/jobs/:jobId/asset/:assetName", requirePin, async (req, res) => {
  try {
    const { jobId, assetName } = req.params;
    const allowed = new Set([
      "final_documentary.mp4",
      "scene_plan.json",
      "transcript.json",
      "subtitles.srt",
      "status.json"
    ]);
    if (!allowed.has(assetName)) {
      return res.status(400).json({ error: "Asset not allowed." });
    }

    const relRes = await ghRequest(`/releases/tags/${encodeURIComponent(jobId)}`);
    if (!relRes.ok) return res.status(404).json({ error: "Job not found." });
    const release = await relRes.json();
    const asset = (release.assets || []).find((a) => a.name === assetName);
    if (!asset) return res.status(404).json({ error: "Asset not ready yet." });

    const redirectRes = await fetch(asset.url, {
      method: "GET",
      redirect: "manual",
      headers: {
        Authorization: `Bearer ${GITHUB_TOKEN}`,
        Accept: "application/octet-stream",
        "User-Agent": "ai-documentary-video-maker"
      }
    });

    const downloadUrl = redirectRes.headers.get("location") || asset.url;
    const upstreamHeaders = { "User-Agent": "ai-documentary-video-maker" };
    if (req.headers.range) {
      upstreamHeaders.Range = req.headers.range;
    }
    if (downloadUrl === asset.url) {
      upstreamHeaders.Authorization = `Bearer ${GITHUB_TOKEN}`;
      upstreamHeaders.Accept = "application/octet-stream";
    }

    const fileRes = await fetch(downloadUrl, { headers: upstreamHeaders });
    res.status(fileRes.status);

    const contentType = assetName.endsWith(".mp4")
      ? "video/mp4"
      : assetName.endsWith(".json")
      ? "application/json; charset=utf-8"
      : "text/plain; charset=utf-8";
    res.setHeader("Content-Type", contentType);

    if (fileRes.headers.get("content-length")) {
      res.setHeader("Content-Length", fileRes.headers.get("content-length"));
    }
    if (fileRes.headers.get("content-range")) {
      res.setHeader("Content-Range", fileRes.headers.get("content-range"));
    }
    res.setHeader("Accept-Ranges", "bytes");

    if (req.query.download === "1") {
      res.setHeader("Content-Disposition", `attachment; filename="${jobId}_${assetName}"`);
    }

    const { Readable } = require("stream");
    Readable.fromWeb(fileRes.body).pipe(res);
  } catch (err) {
    console.error("Asset stream error:", err);
    if (!res.headersSent) {
      res.status(500).json({ error: "ফাইল স্ট্রিম করতে সমস্যা হয়েছে।" });
    }
  }
});

app.use((err, _req, res, _next) => {
  if (err instanceof multer.MulterError) {
    if (err.code === "LIMIT_FILE_SIZE") {
      return res.status(413).json({ error: `ফাইল সাইজ সর্বোচ্চ ${MAX_UPLOAD_MB} MB হতে হবে।` });
    }
    return res.status(400).json({ error: err.message });
  }
  res.status(400).json({ error: err.message || "Request error" });
});

app.listen(PORT, () => {
  console.log(`AI Documentary Video Maker running on port ${PORT}`);
});
