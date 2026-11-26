# AI Documentary Production Studio (FFmpeg + Pillow v5.0)

## v4 আপডেটসমূহ (৪ সেকেন্ডে ভিডিও থেমে যাওয়ার সমাধান)
- **সম্পূর্ণ অডিও দৈর্ঘ্য লক (`director.py`):** Whisper সেগমেন্ট ছোট হলেও অডিও ফাইলের আসল সম্পূর্ণ দৈর্ঘ্য (`duration`) অনুযায়ী শেষ পর্যন্ত দৃশ্য ও গ্রাফিক্স তৈরি হয়।
- **Whisper VAD অটো-রিকভারি (`transcribe.py`):** মৃদু কণ্ঠ বা বিরতির কারণে VAD মাঝপথে থেমে গেলে স্বয়ংক্রিয়ভাবে পুরো অডিও ট্রান্সক্রাইব হয়।
- **Uniform SAR 1:1 ও Timescale (`video_render.py` ও `footage.py`):** প্রতিটি ক্লিপে `setsar=1` এবং `video_track_timescale=15360` যুক্ত করায় প্রথম দৃশ্যের পর মোবাইল বা ওয়েব প্লেয়ারে ভিডিও আর থেমে যাবে না।


## v4.1 উন্নয়ন (Documentary Editing)
- **Custom SRT অগ্রাধিকার:** SRT ফাইল বা Transcript দেওয়া থাকলে সেটি সরাসরি ব্যবহার হবে। দেওয়া ইনপুট ভুল/খালি হলে কাজটি স্পষ্ট error দিয়ে থামবে; নীরবে Whisper-এ fallback করবে না। SRT/Transcript না থাকলেই কেবল Whisper চালু হবে।
- **Scene-based Color Grading:** প্রতিটি দৃশ্যের বক্তব্য/বিষয় অনুযায়ী warm history, cool science, cinematic teal বা neutral documentary grade নির্বাচন করা হয়; AI scene override-ও গ্রহণ করা হয়।
- **Subtle Camera Movement:** স্টক ফুটেজে scene plan অনুযায়ী slow zoom ও pan প্রয়োগ করা হয়, যাতে স্থির ফুটেজও documentary-style motion পায়।
- **Existing Providers Preserved:** Gemini, Groq ও OpenRouter-এর বিদ্যমান integration অপরিবর্তিত রাখা হয়েছে।
- **Existing Media Sources Preserved:** Pexels/Pixabay এবং বর্তমান fallback media search flow অপরিবর্তিত রাখা হয়েছে।

## গুরুত্বপূর্ণ
এই সংস্করণে নতুন Image Generation API যোগ করা হয়নি। Motion graphics বিদ্যমান Pillow/FFmpeg graphics pipeline দিয়েই তৈরি হয়। YouTube monetization নিশ্চিত করা যায় না; প্রতিটি ভিডিওতে মৌলিক স্ক্রিপ্ট, যথাযথ গবেষণা, প্রাসঙ্গিক ভিজ্যুয়াল এবং প্রয়োজনীয় stock-media license/attribution যাচাই করতে হবে।


## v4.2 Editing & Rendering Refinements
- **Editorial hard cuts:** individual stock shots no longer fade to black at both ends; this removes unintended black flashes between documentary shots.
- **Per-scene visual treatment:** scene-level grades remain supported, with restrained contrast, saturation, vignette and sharpening tuned per grade.
- **Consistent output:** final mux explicitly encodes 1920x1080, 30 FPS H.264/AAC output for consistent playback.
- **Narration-first audio mix:** voice is loudness-normalized and background music is mixed substantially lower with a limiter to reduce clipping.
- **Regression checks:** `python -m unittest discover -s tests` covers Bengali SRT parsing, plain transcript timing, camera modes, grade presets and SRT time formatting.

### Validation notes
The source-level tests and syntax checks can run locally. A complete live render still depends on the user's GitHub repository secrets, API quotas, remote stock availability and a successful GitHub Actions run; those external services cannot be certified from this package alone.


## v4.3 Modern YouTube Documentary Direction
- **Footage-first pacing:** the director no longer forces a full-screen infographic after every two stock shots. It prefers relevant Pexels/Pixabay footage and uses a full-screen explainer only when the AI scene plan explicitly calls for one.
- **Purposeful overlays:** editorial Bengali lower-third/label overlays are now enabled selectively (about one in four scenes by default), rather than repeating badges and pills on every shot.
- **More natural grades:** reduced excessive teal/warm tint and vignette so stock footage retains more natural color while keeping a restrained documentary finish.
- **Prompt direction:** asks the existing Gemini/Groq/OpenRouter director for modern YouTube documentary pacing, varied shot types, concise factual graphics, and no invented statistics.
- **Preserved workflow:** custom SRT/transcript still bypasses Whisper; Whisper is used only when no transcript input is supplied. Existing Pexels/Pixabay sources, provider integrations, and GitHub Actions workflow remain in place.

### v4.3 validation
Run `python -m py_compile processor/*.py` and `python -m unittest discover -s tests -v`. A complete render still requires the user's configured GitHub Secrets, API quotas, and a successful GitHub Actions execution.


## v4.4 Narration / Visual Synchronization Fix
- **Absolute scene timestamps preserved:** scene durations are no longer forcibly clamped and appended into a new timeline; the director's absolute scene end times are retained so footage changes stay aligned with timestamped narration.
- **Chronological scene ordering:** provider scene plans are sorted by start timestamp before rendering.
- **CFR concat render:** scene clips are concatenated and re-encoded at 30 FPS instead of stream-copying per-clip timestamps, reducing cumulative cut-boundary timing drift.
- **Timestamp normalization:** final video and narration audio timestamps are reset to zero before muxing; background music is aligned to the same timeline.
- **Regression test:** verifies scene boundaries such as 2.4s and 8.1s are not shifted by duration clamping.

Run `python -m py_compile processor/*.py` and `python -m unittest discover -s tests -v`. A complete live GitHub Actions render is still required to validate the configured API/media providers and the final generated video.


## v5.0 Full Automatic Quality Upgrade
- **Automatic-only workflow:** no manual review/approval stage is included. The worker creates the documentary from upload through final export.
- **10–20 minute target:** this is the recommended documentary length, not a forced trim. The uploaded narration remains the authoritative duration. Longer narrations are planned in timestamped 120-second AI chunks to reduce oversized prompts and partial scene plans.
- **Free-tier AI model routing:** Gemini uses free-tier Flash models, Groq uses Free-plan GPT-OSS/Qwen models, and OpenRouter uses the dynamic `openrouter/free` router. Keep provider accounts on their Free plans; upgrading an account to a paid tier can change its billing behavior.
- **No paid image generation:** graphics remain programmatic through Pillow/FFmpeg. Whisper runs locally on the GitHub Actions worker when no custom SRT/transcript is provided.
- **Quality-first encoding:** medium x264 preset with CRF 19 for scene clips and CRF 18 for final export, at 1920x1080 / 30 FPS.
- **Automated final QC:** verifies audio/video streams, duration tolerance, resolution and frame rate; scans for possible long black/frozen intervals and records warnings in `quality_report.json`.
- **Safer Wikimedia fallback:** only explicitly identified CC0/Public Domain items are accepted; unknown/ambiguous license labels are rejected.
- **Timeline correction:** absolute scene starts and ends are respected; timestamp gaps no longer pull later visuals earlier. A short-audio fallback bug is also fixed.

### Free usage and capacity notes
Free API plans have changing model availability and rate limits. The app does not intentionally call paid model IDs, but API keys must remain on their providers' Free plans. OpenRouter's free router and all providers may temporarily refuse requests when their free quotas are exhausted. GitHub Actions minutes and repository storage also have plan limits. A 10–20 minute 1080p render can take substantial worker time; no free-tier service can guarantee unlimited daily renders.

### v5.0 validation
Run `python -m py_compile processor/*.py`, `python -m unittest discover -s tests -v`, and `node --check server.js && node --check public/app.js`. A complete live render still requires the user's own free-tier API keys, stock-provider keys, GitHub configuration and remaining GitHub Actions allowance.
