# AI Documentary Production Studio (Remotion + FFmpeg v5.1)

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

## v5.1 In-app Remotion Editing Engine (new architecture)
- **Rendering moved into the app's own worker:** the pipeline now builds a Remotion scene composition and renders the final MP4 in the same GitHub Actions worker. No external Remotion website or user-uploaded ZIP step is required.
- **Reference-aligned architecture:** adds a Remotion 4.0.517 / React 19.2.3 renderer, dynamic `scene.json`, `Video.tsx`, and reusable Bengali-safe `kit.tsx`, aligned with the supplied Gemini sample's technical stack.
- **Scene-based composition:** absolute AI director timestamps are converted to a 30 FPS timeline; Pexels/Pixabay clips are copied into Remotion's public assets and composed with animated graphic scenes, Bengali typography, and optional timed subtitles.
- **Narration synchronization:** the source voice is decoded to 24 kHz mono PCM WAV for the composition; final voice and optional background music are muxed in the same pipeline.
- **Local Bengali typography:** Hind Siliguri font files are bundled in the project; no external font fetch is needed during render.
- **No external ZIP rendering handoff:** the Remotion project exists only as an internal worker build artifact. The user receives the final MP4 through the existing app workflow.

### v5.1 validation scope
Python syntax/tests and JavaScript syntax checks validate source-level behavior. A real 1080p render must still be exercised in GitHub Actions with the user's configured free-tier provider/media secrets and available worker minutes. The included renderer is a first integrated Remotion pass; visual quality must be assessed on a rendered sample before calling the editing upgrade complete.


## Remotion video themes (v5.2 update)

The six dashboard themes are passed into the in-app Remotion scene JSON as `videoTheme` and applied to Remotion graphic backgrounds, title/tag accents, charts, timelines, map markers, subtitle panels and decorative elements. Stock footage, narration, timing and story content are not changed by the theme. Keys: `crimson_noir`, `cinematic_dark`, `vox_colorful`, `editorial_paper`, `vibrant_gradient`, `minimal_light`. Default/fallback: `crimson_noir`.


## v5.3 Landscape Documentary Motion, Karaoke & Storyboard Upgrade
- **16:9 Landscape Preset Library (`processor/director.py`):** Upgrades the free-tier AI director prompt (Gemini / Groq / OpenRouter) with story beats (`hook`, `setup`, `rising`, `climax`, `consequence`, `lesson`, `cta`), camera presets (`CAM-PUSH`, `CAM-PULL`, `CAM-PAN-L`, `CAM-PAN-R`, `CAM-DRIFT`, `CAM-PUNCH`, `CAM-SHAKE`), text presets (`HDR-DROP`, `TAG-WIPE`, `NUM-ROLL`, `QUOTE-STAGGER`, `BIG-STAMP`, `CTA-STAGGER`), transitions (`TR-CUT`, `TR-DISSOLVE`, `TR-FADEBLACK`, `TR-WHIP`, `TR-WIPE`, `TR-ZOOMTHRU`, `TR-FLASH`), Bengali highlight keywords, and `music_mode` (`normal`, `duck`, `mute`) with safe automatic fallbacks and a 3-use cap on `CAM-SHAKE` + `TR-FLASH`.
- **Word-Level `SUB-KARAOKE` & Animated Presets (`remotion/src/kit.tsx`, `Video.tsx`, `remotion_render.py`):** Passes Whisper word timestamps (or Bengali-safe space-split fallback timings for custom SRT) and scene keywords into `scene.json`, rendering word-by-word karaoke highlights, Bengali numeral rolling (`NUM-ROLL`), all camera/text/transition presets, 5% 16:9 safe zones, and subtle vignette + 3% film grain across all 6 themes.
- **YouTube `-14 LUFS` Mastering & Music Mute (`remotion_render.py`):** Normalizes voiceover to `-14 LUFS` (`TP=-1.0`) and dynamically ducks or mutes background music on dramatic scenes.
- **Visual Storyboard QC (`quality_control.py`, `pipeline.py`):** Extracts mid-scene thumbnails and uploads a self-contained Bengali `storyboard.html` to GitHub Releases alongside `final_documentary.mp4`.
- **HyperFrames Motion Reference Docs (`docs/hyperframes-references/`):** Bundles the HyperFrames motion, captions, overlays, sound, and review reference guides for future motion-design iteration.


## v5.4 Footage + Picture Mix & Scene-Aware Visual Effects
- **First-Class Video + Photo Mixing (`director.py`, `footage.py`):** Adds Pexels Photos API alongside Pixabay Photos, Wikimedia CC0, and NASA images. The AI director actively mixes ~55-65% HD stock videos (`media_preference: "video"`) and ~20-25% Ken Burns animated photos (`media_preference: "photo"`) plus explainer graphics, automatically falling back between photo and video when needed.
- **Context-Aware Documentary Visual Effects (`director.py`, `kit.tsx`, `Video.tsx`):** Supports 7 deterministic Remotion visual effects chosen only when the story calls for them: `old_footage` (sepia, animated film scratches, dust & flicker), `archival_photo` (museum border & warm grain), `vhs_retro` (scanlines, tracking bar & PLAY timestamp), `noir_bw` (high-contrast monochrome), `cctv_cam` (surveillance tint, scanlines & corner brackets), `dream_glow` (warm light leak), and `glitch_pulse` (brief RGB glitch entry), plus `none` for clean modern shots.


## v5.5 Custom Scene Plan Upload & Dashboard Storyboard
- **Optional Custom `scene_plan.json` Upload (`public/index.html`, `app.js`, `server.js`, `pipeline.py`, `director.py`):** Upload or paste a `scene_plan.json` created in the Gemini app (listening directly to your audio) to bypass GitHub Actions LLM API calls completely while still validating and normalizing all presets, effects, and timestamps.
- **Dashboard Storyboard Download (`server.js`, `index.html`, `app.js`):** Adds `storyboard.html` directly to the result card's download bar.
- **Ready-to-Use Prompt (`docs/GEMINI_SCENE_PLAN_PROMPT.txt`):** Bundled prompt to generate both `subtitles.srt` and `scene_plan.json` from any Bengali voiceover in the Gemini app.


## v5.6 Clean Bright Footage, Animated Intro & Kinetic Motion Graphics
- **Removed black shadow overlay (`remotion/src/Video.tsx`, `kit.tsx`):** Removes the 50% dark gradient shadow, heavy global vignette, and `brightness(.84)` dimming so HD stock footage stays crisp and bright. Text overlays over video use a compact glass card behind the text only.
- **Animated Documentary Intro (`kit.tsx`):** Scene 1 now renders `CinematicIntroCard` with spring-animated tag shine, word-by-word kinetic title reveal, expanding accent bar, and smooth exit fade.
- **Fully Animated Motion Graphics (`kit.tsx`):** Replaces static SVGs with `AnimatedMotionGraphic` (line-drawing timeline with spring-popping pulsing milestones, spring-rising bar charts, route-drawing radar-pulsing map markers, and rotating orbital rings).
- **Word-Safe Bengali Headings (`director.py`):** Fixes mid-word truncation so Bengali headings never cut off a word halfway.


## v5.7 Reference Documentary Style (Clean Typography, Rich Motion Infographics & Reliable Photos)
- **Light Scrim & Clean Floating Text (`Video.tsx`, `kit.tsx`):** Removes bulky/pink card boxes behind headlines and uses only a subtle `rgba(0,0,0,0.22)` readability scrim when text floats over footage. Headlines render large, crisp, and bold word-by-word with a sharp accent tag bar and compact glowing callout pills.
- **Reference-Style Animated Infographics (`kit.tsx`):** Adds animated dual-ring percentage donut charts (`stat_chart`), hub-and-spoke curved network maps (`map_marker`), numbered step cards with rotating shield emblem (`timeline`), and a 3-pill animated ending CTA (`CTA-STAGGER`).
- **Guaranteed Photo + Video Mix (`footage.py`, `director.py`):** Increases default photo ratio to ~33% of stock scenes and adds simplified-keyword fallback retries in `_find_photo_asset()` so real HD Ken Burns photos load reliably instead of dropping back to graphics.
- **Custom Scene Plan in Web App (`public/`, `server.js`, `pipeline.py`):** Full support for uploading/pasting `scene_plan.json` directly in the web dashboard to skip GitHub Actions LLM calls.
