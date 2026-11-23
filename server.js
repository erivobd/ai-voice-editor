'use strict';

const express = require('express');
const multer = require('multer');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { pipeline } = require('stream/promises');

const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '2mb' }));

const PORT = Number(process.env.PORT || 3000);
const OWNER = process.env.GITHUB_OWNER;
const REPO = process.env.GITHUB_REPO;
const TOKEN = process.env.GITHUB_TOKEN;
const WORKFLOW = process.env.GITHUB_WORKFLOW_FILE || 'voice-editor.yml';
const BRANCH = process.env.GITHUB_BRANCH || 'main';
const ACCESS_PIN = process.env.APP_ACCESS_PIN || '';
const MAX_UPLOAD_BYTES = 150 * 1024 * 1024;
const TMP_DIR = '/tmp/voice-editor-uploads';
const INDEX_FILE = path.join(__dirname, 'index.html');
const APP_JS_FILE = path.join(__dirname, 'app.js');
const STYLE_CSS_FILE = path.join(__dirname, 'style.css');
const SAFE_ASSETS = new Set([
  'status.json', 'report.json', 'nr_preview.wav', 'approved_plan.json',
  'editing_report.json', 'final_edited.mp3', 'final_edited.wav'
]);
fs.mkdirSync(TMP_DIR, { recursive: true });

const upload = multer({
  dest: TMP_DIR,
  limits: { fileSize: MAX_UPLOAD_BYTES, files: 2, fields: 2 },
  fileFilter(req, file, cb) {
    const ext = path.extname(file.originalname || '').toLowerCase();
    if (file.fieldname === 'audio' && ['.mp3','.wav','.m4a','.aac','.flac'].includes(ext)) return cb(null, true);
    if (file.fieldname === 'script' && ext === '.txt') return cb(null, true);
    cb(new Error('Unsupported file type. Audio: MP3/WAV/M4A/AAC/FLAC. Script: TXT.'));
  }
});

function sessionValue(exp) {
  const payload = String(exp);
  const sig = crypto.createHmac('sha256', ACCESS_PIN).update(payload).digest('hex');
  return `${payload}.${sig}`;
}
function validSession(req) {
  if (!ACCESS_PIN) return true;
  const raw = (req.headers.cookie || '').split(';').map(x => x.trim()).find(x => x.startsWith('voice_editor_session='));
  if (!raw) return false;
  const value = decodeURIComponent(raw.slice('voice_editor_session='.length));
  const [exp, sig] = value.split('.');
  if (!exp || !sig || !/^\d+$/.test(exp) || Number(exp) < Date.now()) return false;
  const expected = crypto.createHmac('sha256', ACCESS_PIN).update(exp).digest('hex');
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
function requireAuth(req, res, next) {
  if (validSession(req)) return next();
  return res.status(401).json({ error: 'Access PIN required.' });
}
function requireConfig() {
  if (!OWNER || !REPO || !TOKEN) throw new Error('Missing GitHub configuration. Set GITHUB_OWNER, GITHUB_REPO and GITHUB_TOKEN in Render.');
}
async function gh(pathname, options = {}) {
  requireConfig();
  const response = await fetch(`https://api.github.com${pathname}`, {
    ...options,
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${TOKEN}`,
      'X-GitHub-Api-Version': '2022-11-28',
      ...(options.headers || {})
    },
    signal: AbortSignal.timeout(60000)
  });
  const bodyText = await response.text();
  let body;
  try { body = bodyText ? JSON.parse(bodyText) : {}; } catch { body = { message: bodyText.slice(0, 500) }; }
  if (!response.ok) throw new Error(`GitHub API ${response.status}: ${body.message || 'request failed'}`);
  return body;
}
const repoPath = () => `/repos/${OWNER}/${REPO}`;
async function getRelease(tag) {
  return gh(`${repoPath()}/releases/tags/${encodeURIComponent(tag)}`);
}
async function createRelease(jobId, filename) {
  return gh(`${repoPath()}/releases`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tag_name: jobId, name: jobId, body: `Private voice editing job. Original file: ${filename}`,
      draft: false, prerelease: true, target_commitish: BRANCH
    })
  });
}
async function deleteAssetIfExists(release, name) {
  const found = (release.assets || []).find(a => a.name === name);
  if (found) await gh(`${repoPath()}/releases/assets/${found.id}`, { method: 'DELETE' });
}
async function uploadFileAsset(release, name, filePath, contentType) {
  const fresh = await gh(`${repoPath()}/releases/${release.id}`);
  await deleteAssetIfExists(fresh, name);
  const stat = fs.statSync(filePath);
  const stream = fs.createReadStream(filePath);
  const url = `https://uploads.github.com/repos/${OWNER}/${REPO}/releases/${release.id}/assets?name=${encodeURIComponent(name)}`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      Accept: 'application/vnd.github+json',
      'Content-Type': contentType,
      'Content-Length': String(stat.size)
    },
    body: stream,
    duplex: 'half',
    signal: AbortSignal.timeout(10 * 60 * 1000)
  });
  const txt = await response.text();
  if (!response.ok) throw new Error(`GitHub asset upload failed (${response.status}): ${txt.slice(0, 500)}`);
}
async function uploadJson(release, name, data) {
  const p = path.join(TMP_DIR, `${crypto.randomUUID()}.json`);
  fs.writeFileSync(p, JSON.stringify(data, null, 2));
  try { await uploadFileAsset(release, name, p, 'application/json'); }
  finally { fs.rmSync(p, { force: true }); }
}
async function dispatch(jobId, action) {
  await gh(`${repoPath()}/actions/workflows/${encodeURIComponent(WORKFLOW)}/dispatches`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ref: BRANCH, inputs: { job_id: jobId, action } })
  });
}
function validJobId(id) { return /^job-[a-f0-9-]{20,40}$/i.test(String(id || '')); }
function cleanTemp(files) {
  for (const f of Object.values(files || {}).flat()) {
    if (f && f.path) fs.rmSync(f.path, { force: true });
  }
}
function safeFilename(name) {
  return path.basename(String(name || 'audio')).replace(/[^a-zA-Z0-9._-]/g, '_').slice(0, 100) || 'audio';
}
function parseJsonAsset(asset) {
  return asset ? gh(`${repoPath()}/releases/assets/${asset.id}`, { headers: { Accept: 'application/octet-stream' } }) : null;
}

app.get('/api/health', (req, res) => res.json({ ok: true }));
app.get('/api/config', (req, res) => res.json({ pinRequired: Boolean(ACCESS_PIN) }));
app.post('/api/auth', (req, res) => {
  if (!ACCESS_PIN) return res.json({ ok: true });
  const supplied = String(req.body?.pin || '');
  const a = Buffer.from(supplied);
  const b = Buffer.from(ACCESS_PIN);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return res.status(401).json({ error: 'Incorrect PIN.' });
  const exp = Date.now() + 12 * 60 * 60 * 1000;
  res.setHeader('Set-Cookie', `voice_editor_session=${encodeURIComponent(sessionValue(exp))}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=43200`);
  res.json({ ok: true });
});
app.post('/api/logout', (req, res) => {
  res.setHeader('Set-Cookie', 'voice_editor_session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0');
  res.json({ ok: true });
});

app.use('/api', requireAuth);

app.post('/api/jobs', (req, res, next) => {
  upload.fields([{ name: 'audio', maxCount: 1 }, { name: 'script', maxCount: 1 }])(req, res, async err => {
    if (err) { cleanTemp(req.files); return res.status(400).json({ error: err.message }); }
    try {
      const audio = req.files?.audio?.[0];
      const script = req.files?.script?.[0];
      if (!audio) { cleanTemp(req.files); return res.status(400).json({ error: 'Please select an audio file.' }); }
      if (script && script.size > 2 * 1024 * 1024) { cleanTemp(req.files); return res.status(400).json({ error: 'Script file must be under 2 MB.' }); }
      requireConfig();
      const jobId = `job-${crypto.randomUUID()}`;
      let release;
      try {
        release = await createRelease(jobId, safeFilename(audio.originalname));
        const ext = path.extname(safeFilename(audio.originalname)).toLowerCase();
        await uploadFileAsset(release, `original_audio${ext}`, audio.path, 'application/octet-stream');
        if (script) await uploadFileAsset(release, 'script.txt', script.path, 'text/plain; charset=utf-8');
        await uploadJson(release, 'status.json', { status: 'running', stage: 'queued', message: 'Job queued for analysis.', updated_at: new Date().toISOString() });
        await dispatch(jobId, 'analyze');
        res.status(202).json({ job_id: jobId });
      } finally { cleanTemp(req.files); }
    } catch (e) {
      cleanTemp(req.files);
      next(e);
    }
  });
});

app.get('/api/jobs', async (req, res, next) => {
  try {
    requireConfig();
    const data = await gh(`${repoPath()}/releases?per_page=30`);
    const jobs = data.filter(r => r.tag_name.startsWith('job-')).map(r => ({
      job_id: r.tag_name, original_filename: r.body || r.name, created_at: r.created_at,
      stage: r.assets.some(a => a.name === 'final_edited.mp3') ? 'completed' :
        r.assets.some(a => a.name === 'report.json') ? 'review_ready' : 'processing'
    }));
    res.json({ jobs });
  } catch (e) { next(e); }
});

app.get('/api/jobs/:jobId', async (req, res, next) => {
  try {
    const id = req.params.jobId;
    if (!validJobId(id)) return res.status(400).json({ error: 'Invalid job ID.' });
    const release = await getRelease(id);
    const byName = Object.fromEntries(release.assets.map(a => [a.name, a]));
    async function readJson(name) {
      const asset = byName[name];
      if (!asset) return null;
      const response = await fetch(asset.url, { headers: { Authorization: `Bearer ${TOKEN}`, Accept: 'application/octet-stream' }, signal: AbortSignal.timeout(30000) });
      if (!response.ok) throw new Error(`Could not read ${name}`);
      return response.json();
    }
    const [status, report, editingReport] = await Promise.all([
      readJson('status.json'), readJson('report.json'), readJson('editing_report.json')
    ]);
    res.json({
      status: status || { status: 'running', stage: 'processing', message: 'Waiting for worker.' },
      report, editingReport,
      assets: release.assets.map(a => ({ name: a.name, size: a.size }))
    });
  } catch (e) { next(e); }
});

app.post('/api/jobs/:jobId/render', async (req, res, next) => {
  try {
    const id = req.params.jobId;
    if (!validJobId(id)) return res.status(400).json({ error: 'Invalid job ID.' });
    const cuts = req.body?.approved_cuts;
    const nr = req.body?.noise_reduction === 'gentle' ? 'gentle' : 'original';
    if (!Array.isArray(cuts) || cuts.length > 500) return res.status(400).json({ error: 'Invalid approved cut list.' });
    for (const cut of cuts) {
      const start = Number(cut.start), end = Number(cut.end);
      if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end <= start) {
        return res.status(400).json({ error: 'One or more approved cuts have invalid timestamps.' });
      }
    }
    const release = await getRelease(id);
    if (!release.assets.some(a => a.name === 'report.json')) return res.status(409).json({ error: 'Analysis is not ready yet.' });
    if (release.assets.some(a => a.name === 'final_edited.mp3')) return res.status(409).json({ error: 'This job has already been rendered. Start a new job to edit again.' });
    await uploadJson(release, 'approved_plan.json', { approved_cuts: cuts, noise_reduction: nr });
    await uploadJson(release, 'status.json', { status: 'running', stage: 'rendering', message: 'Rendering approved edits.', updated_at: new Date().toISOString() });
    await dispatch(id, 'render');
    res.status(202).json({ ok: true });
  } catch (e) { next(e); }
});

app.get('/api/jobs/:jobId/assets/:assetName', async (req, res, next) => {
  try {
    const id = req.params.jobId;
    const name = req.params.assetName;
    if (!validJobId(id) || (!SAFE_ASSETS.has(name) && !/^original_audio\.(mp3|wav|m4a|aac|flac)$/.test(name))) {
      return res.status(400).json({ error: 'Invalid asset request.' });
    }
    const release = await getRelease(id);
    const asset = release.assets.find(a => a.name === name);
    if (!asset) return res.status(404).json({ error: 'Asset not found.' });
    const headers = { Authorization: `Bearer ${TOKEN}`, Accept: 'application/octet-stream' };
    const range = req.headers.range;
    if (range) headers.Range = range;
    const upstream = await fetch(asset.url, { headers, redirect: 'follow', signal: AbortSignal.timeout(10 * 60 * 1000) });
    if (!upstream.ok && upstream.status !== 206) return res.status(upstream.status).json({ error: 'Could not stream asset.' });
    res.status(upstream.status);
    res.setHeader('Content-Type', name.endsWith('.wav') ? 'audio/wav' : name.endsWith('.mp3') ? 'audio/mpeg' : 'application/octet-stream');
    res.setHeader('Accept-Ranges', 'bytes');
    if (upstream.headers.get('content-length')) res.setHeader('Content-Length', upstream.headers.get('content-length'));
    if (upstream.headers.get('content-range')) res.setHeader('Content-Range', upstream.headers.get('content-range'));
    if (req.query.download === '1') res.setHeader('Content-Disposition', `attachment; filename="${name}"`);
    if (!upstream.body) return res.end();
    const { Readable } = require('stream');
    await pipeline(Readable.fromWeb(upstream.body), res);
  } catch (e) { if (!res.headersSent) next(e); else res.destroy(e); }
});

app.get('/', (req, res, next) => {
  res.sendFile(INDEX_FILE, err => {
    if (err) next(err);
  });
});

app.get('/index.html', (req, res, next) => {
  res.sendFile(INDEX_FILE, err => {
    if (err) next(err);
  });
});

app.get('/app.js', (req, res, next) => {
  res.sendFile(APP_JS_FILE, err => {
    if (err) next(err);
  });
});

app.get('/style.css', (req, res, next) => {
  res.sendFile(STYLE_CSS_FILE, err => {
    if (err) next(err);
  });
});

app.use(express.static(__dirname));

app.use((err, req, res, next) => {
  console.error(err);
  if (res.headersSent) return next(err);
  res.status(500).json({ error: err.message || 'Internal server error.' });
});
app.listen(PORT, () => console.log(`AI Voice Editor listening on ${PORT}`));