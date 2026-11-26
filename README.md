# AI Documentary Video Maker (FFmpeg + Pillow v4)

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
