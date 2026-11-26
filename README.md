# AI Documentary Video Maker (FFmpeg + Pillow v2)

## প্রধান আপডেটসমূহ
- **Remotion সম্পূর্ণ বাদ:** পুরো ভিডিও রেন্ডারিং ও ইনফোগ্রাফিক্স এখন **FFmpeg + Pillow** দিয়ে তৈরি হয়।
- **অধ্যায় ট্যাগ অপসারণ ও বড় পিল:** ভিডিওতে কোনো "অধ্যায়" লেখা আসবে না এবং ইনফো পিল ও ব্যাজগুলো ওভারল্যাপ ছাড়াই বড় ও স্পষ্টভাবে দেখাবে।
- **কাস্টম SRT ফাইল / টেক্সট ও বাংলা Whisper:** কাস্টম `.srt` ফাইল আপলোড বা সরাসরি টেক্সট পেস্ট করলে Whisper স্কিপ হবে; না দিলে `AUDIO_LANGUAGE=bn` লক করে Whisper চলবে এবং হিন্দি/দেবনাগরী শব্দ ফিল্টার হবে।
- **ক্রেডিট-মুক্ত মিডিয়া ফিল্টার:** শর্তহীন ফ্রি / CC0 / Public Domain এবং অনুমোদিত স্টক মিডিয়াই সংগ্রহ করা হয়।

## Android ফোন থেকে GitHub ও Render-এ ডিপ্লয় গাইড
1. এই ZIP ফাইলটি ফোনের ফাইল ম্যানেজারে আনজিপ করুন।
2. GitHub-এ আপনার রিপোজিটরিতে সব ফাইল আপলোড বা কমিট করুন (খেয়াল রাখবেন `.github/workflows/documentary-maker.yml` যেন সঠিক ফোল্ডারে থাকে)।
3. GitHub Repository **Settings > Secrets and variables > Actions**-এ `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `PEXELS_API_KEY`, `PIXABAY_API_KEY` যুক্ত করুন।
4. Render Web Service-এ Environment Variables হিসেবে `APP_ACCESS_PIN`, `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`, `GITHUB_WORKFLOW_FILE=documentary-maker.yml`, `GITHUB_BRANCH=main` সেট করে ডিপ্লয় করুন।
