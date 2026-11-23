# AI Voice Editor

A review-first editor for spoken narration. It compares an audio recording with an optional Bengali script, suggests possible cuts, and only applies cuts that the user explicitly approves.

## Important voice-preservation behavior

- No voice cloning, voice generation, pitch shifting, time stretching, or automatic speech rewriting.
- Original audio is retained.
- Noise reduction is optional and defaults to `original`.
- Suggested edits are never auto-approved.
- Review every suggested cut before rendering. A false-positive cut can remove valid narration.

## Architecture

- Render hosts the Node/Express app.
- A private GitHub repository stores each job as a private GitHub Release.
- GitHub Actions runs Python, Faster-Whisper and FFmpeg.
- The browser reviews the report and submits an approved cut plan.

## GitHub setup

1. Create a **private** repository.
2. Upload all project files while preserving the folder structure.
3. In repository Settings → Actions → General, allow GitHub Actions.
4. Create a fine-grained Personal Access Token for this repository with:
   - Contents: Read and write
   - Actions: Read and write
5. Add the token to Render as `GITHUB_TOKEN`.

The workflow uses the repository's `GITHUB_TOKEN` with `contents: write` to upload release assets.

## Render environment variables

- `GITHUB_TOKEN`: fine-grained token described above
- `GITHUB_OWNER`: GitHub username or organization
- `GITHUB_REPO`: repository name
- `GITHUB_WORKFLOW_FILE`: `voice-editor.yml`
- `GITHUB_BRANCH`: `main`
- `APP_ACCESS_PIN`: optional access PIN. Set a long PIN if the site is public.

Deploy as a Node web service. Node 20 or newer is required.

## Use

1. Open the Render URL.
2. Enter the access PIN if configured.
3. Upload an audio file. Uploading a `.txt` Bengali script is recommended.
4. Wait for analysis.
5. Listen to each suggested section. Keep or approve cuts manually.
6. Select Original audio or Gentle noise reduction.
7. Render and download MP3/WAV.

## Limits and caveats

- Default upload limit is 150 MB. Change `MAX_UPLOAD_BYTES` in `server.js` only if Render memory/disk limits can support it.
- GitHub Actions job time is limited to 60 minutes.
- Faster-Whisper's `medium` model can be slow on CPU. Set `WHISPER_MODEL=small` in the workflow if needed.
- This is a conservative first release, not a substitute for listening. ASR may mishear Bengali words, names, accents, or code-switching.
- Keep the GitHub repository private. GitHub Release assets in a private repository are private to authorized repository users.
- This project has not been deployed or tested against your Render/GitHub accounts. Verify with a short test recording first.
