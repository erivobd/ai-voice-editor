# AI Documentary Video Maker

নিজের রেকর্ড ও এডিট করা রেডি ভয়েসওভার আপলোড করলেই AI স্বয়ংক্রিয়ভাবে ভয়েস বুঝে, দৃশ্য পরিকল্পনা করে, বাস্তব HD স্টক ফুটেজ, Ken Burns ছবি ও মোশন গ্রাফিক্স যুক্ত করে সম্পূর্ণ **1080p সিনেমাটিক ডকুমেন্টারি ভিডিও (MP4)** তৈরি করে দেয়।

## মূল বৈশিষ্ট্য
- **মূল ভয়েস ১০০% অক্ষত:** কোনো পিচ, স্পিড বা টোন পরিবর্তন করা হয় না।
- **Hybrid AI ইঞ্জিন:** `faster-whisper` দিয়ে নিখুঁত টাইমস্ট্যাম্প + **Gemini AI** দিয়ে ডকুমেন্টারি ডিরেকশন ও স্টোরিবোর্ড।
- **৫-স্তরের মিডিয়া ও গ্রাফিক্স ইঞ্জিন (Pexels ছাড়াই চলে):**
  1. **Pixabay HD Video** (প্রাথমিক ভিডিও সোর্স)
  2. **Pixabay High-Res Photos** (সিনেম্যাটিক Ken Burns জুম অ্যানিমেশনসহ)
  3. **Wikimedia Commons** (ইতিহাস, প্রকৃতি ও বিজ্ঞানের ছবি — কোনো API Key লাগে না)
  4. **NASA Image Library** (মহাকাশ ও বিজ্ঞানের ছবি — কোনো API Key লাগে না)
  5. **কাস্টম বাংলা মোশন গ্রাফিক্স** (`librsvg` + `Noto Sans Bengali`) — কোনো ক্লিপ কখনো রিপিট হয় না।
- **নিরাপদ মিউজিক:** ১০০% কপিরাইট-মুক্ত ব্যাকগ্রাউন্ড অ্যাম্বিয়েন্ট মিউজিক।
- **মোবাইল-ফ্রেন্ডলি UI:** PIN লগইন, ৯-ধাপের লাইভ প্রগ্রেস বার, এরর রিপোর্টিং, ইন-ব্রাউজার ভিডিও প্রিভিউ এবং MP4 ডাউনলোড।

## GitHub Secrets সেটআপ (Settings → Secrets and variables → Actions)
1. `GEMINI_API_KEY` *(ইতিমধ্যেই যুক্ত আছে)*
2. `PIXABAY_API_KEY` *(ফ্রি অ্যাকাউন্ট থেকে নিন: pixabay.com/api/docs)*
3. `PEXELS_API_KEY` *(সম্পূর্ণ ঐচ্ছিক — না দিলেও কোনো সমস্যা নেই)*

## Render Environment Variables
- `GITHUB_TOKEN`: Fine-grained Personal Access Token (Contents: Read & Write, Actions: Read & Write)
- `GITHUB_OWNER`: আপনার GitHub ইউজারনেম
- `GITHUB_REPO`: প্রাইভেট রিপোজিটরির নাম
- `GITHUB_WORKFLOW_FILE`: `documentary-maker.yml`
- `GITHUB_BRANCH`: `main`
- `APP_ACCESS_PIN`: আপনার পছন্দের সিকিউরিটি PIN
