# Viral Rapper Content Pipeline

**Product Name:** Viral Rapper Pipeline (or "Rapper Vibe Generator")

**Created by:** Ivan (@pricolniy)  
**Goal:** Automatically create short, viral videos for TikTok, Instagram Reels, or YouTube Shorts. Feature Russian SoundCloud rappers (plus yourself) in funny/unexpected roles to promote your own music among popular artists.

**Version:** 1.0  
**Last Updated:** 2026-02-26

### What It Produces
Short 20–40 second videos in vertical format (1080x1920) for TikTok/Reels:
- 4-second intro: All rappers together in the theme
- 4 seconds per rapper: Animated photo + their track playing
- Single voiceover for entire video: Short phrase describing the theme (e.g. "Кем бы работали СК рэперы в средние века?")
- Promoted rapper appears at position 2 or 3 for maximum visibility

Example themes:
- Which rapper would be president of which country
- What job they would have at a factory
- What car they would drive in medieval times
- Any other fun or absurd scenarios

### Telegram Bot User Flow

**Main Menu:**
- User presses "Создать видео" button → Start video creation flow
- User presses "Настройки" button → Open settings menu

**Settings Menu:**
1. Системный промпт Gemini — Edit custom prompt for image generation
2. API ключи — Manage personal API keys (Gemini, ElevenLabs, Grok Video)
3. Голос озвучки — Select voice model from ElevenLabs
4. Качество видео — Choose bitrate (high/medium)
5. Длительность клипов — Adjust intro and rapper clip duration (3-5 sec)

**Settings Features:**
- All settings stored per user in SQLite database
- API keys encrypted in database
- Fallback to default settings if user hasn't customized
- "Сбросить на дефолт" button to restore defaults
- Settings persist across sessions

---

**Step 1: Start Creation**
- User presses "Создать видео" button
- Bot displays all rappers from CSV as inline keyboard buttons (grid layout)

**Step 2: Select Rappers (up to 6)**
- User clicks buttons to add rappers (max 6)
- Selected rappers show checkmark ✅
- Current selection displayed above buttons: "Выбрано: Ivan, Oxxxy, Pharaoh (3/6)"
- Buttons: [Подтвердить список] [Сбросить]

**Step 3: Enter Theme**
- Bot asks: "Введите тему для видео"
- Bot suggests examples as buttons:
  - "Президентами каких стран будут СК рэперы"
  - "Кем СК рэперы работали бы в средние века"
  - "Какие машины водили бы СК рэперы в будущем"
  - [Своя тема] — user types custom theme
- Buttons: [Сбросить]

**Step 4: Confirmation**
- Bot shows summary:
  ```
  Рэперы: Ivan, Oxxxy, Pharaoh, Скриптонит, Morgenshtern, Элджей
  Тема: "Президентами каких стран будут СК рэперы"
  ```
- Buttons: [Создать видео] [Сбросить]

**Step 5: Generation Process**
- Bot edits last message with live status updates:
  ```
  ⏳ Генерация изображений... 2/6
  ⏳ Генерация видео... 4/6
  ⏳ Сборка финального видео...
  ```
- On error: Bot sends error message with details

**Step 6: Delivery**
- Bot sends completed video: `viral_vibe.mp4`
- Caption: "✅ Видео готово! Тема: [theme]"
- User can immediately start new generation (parallel processing supported)

**Reset Button:**
- Available on every step
- Returns to Step 1 (rapper selection)
- Clears current session state

---

### Backend Pipeline

1. **Generate Content**  
   - Assign random roles based on theme (e.g. "USA President", "Russia President")
   - Generate images using **Google Gemini** (gemini-pro-vision or imagen-3)
   - Generate single Russian voiceover for entire video via **ElevenLabs** (e.g. "Кем бы работали СК рэперы в средние века?")
   - Animate photos into talking videos using **Grok Imagine Video** (~$0.05/sec)
   - Place promoted rapper at position 2 or 3

2. **Assemble Video**  
   **MoviePy** stitches everything:  
   - Vertical format 1080x1920, 30 FPS
   - Intro (4 sec) with theme text overlay + voiceover
   - Rapper clips (4 sec each)
   - Each rapper's track plays during their segment (no voiceover per rapper)
   - Audio mixing: intro has voiceover + music, rapper clips have only their tracks

3. **Deliver**  
   Send `viral_vibe.mp4` to Telegram chat

### Key Platforms Used

- **SoundCloud** — Find and download tracks (curate manually for safety/legal reasons)
- **Google Gemini** — Image generation (primary: gemini-pro-vision or imagen-3, free tier available)
- **Grok Imagine Video** — Cheapest video animation (~$0.20 for a 4-second clip with audio)
- **ElevenLabs** — High-quality Russian voiceovers
- **MoviePy** (free Python library) — Local video editing and stitching

### Why It's Great
- Endless content: One theme = one video in 10–30 minutes (after setup)
- You appear alongside popular rappers → natural audience growth
- Low cost: ~$0.50–2 per video for 10–15 rappers
- Fully customizable format

### Technical Stack

**Backend:**
- Python 3.11+ (asyncio for async operations)
- python-telegram-bot (Telegram bot framework)
- MoviePy (video editing and assembly)
- Pillow (image processing)
- pydub (audio manipulation)
- pandas (CSV/data handling)

**APIs:**
- Google Gemini API (image generation)
- Grok Imagine Video API (talking-head animation)
- Grok Imagine API (backup image generation)
- ElevenLabs API (Russian voiceover)
- SoundCloud (manual track downloads via yt-dlp or soundcloud-lib)

**Storage:**
- Local filesystem for temp files
- Google Sheets (manual CSV export) for rapper database
- .env file for API keys

**Infrastructure:**
- Single Python script with modular functions
- Celery/RQ optional for queue (start with sync processing)
- SQLite optional for generation history (start without DB)

### Data Schema (Google Sheets → CSV)

| Name | Photo URL | Track Path | Is Promoted |
|------|-----------|------------|-------------|
| Ivan (@pricolniy) | https://... | tracks/ivan.mp3 | yes |
| Oxxxymiron | https://... | tracks/oxxxy.mp3 | no |
| Pharaoh | https://... | tracks/pharaoh.mp3 | no |

### Video Specifications
- Format: MP4 (H.264 codec)
- Resolution: 1080x1920 (vertical)
- FPS: 30
- Bitrate: 5000k (high quality for social media)
- Audio: AAC, 192kbps, stereo

### Cost Estimation (per video, 6 rappers)
- Google Gemini: Free tier (1500 requests/day) or ~$0.01 per image × 6 = $0.06
- Grok Imagine Video: ~$0.05/sec × 4 sec × 6 rappers = $1.20
- ElevenLabs: ~$0.10 per voiceover × 1 (single voiceover for entire video) = $0.10
- Total: ~$1.36 per video (6 rappers)
- With free Gemini tier: ~$1.30 per video

### Next Steps
- Build Google Sheets with 15–20 top Russian rappers
- Get API keys:
  - Telegram Bot Token (via @BotFather)
  - Google Gemini API Key (for image generation)
  - Grok Imagine Video API Key (for talking-head animation)
  - ElevenLabs API Key (for Russian voiceovers)
- Setup Render.com account and create new web service
- Deploy to Render.com with PostgreSQL database
- Set Telegram webhook to Render.com URL
- Upload rappers.csv and MP3 tracks to persistent disk
- Test end-to-end pipeline with 3-6 rappers

Ready to scale — just drop in new themes via Telegram! 🚀

### Deployment Notes (Render.com)
- Free tier limitations: Service sleeps after 15 min inactivity (webhook wakes it up)
- 512MB RAM: Sufficient for basic video generation, process sequentially if needed
- 1GB persistent disk: Store tracks, temp files, output videos (clean up old videos)
- PostgreSQL free for 90 days: Migrate to external DB or upgrade to paid plan after trial