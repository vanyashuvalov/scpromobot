# Development Plan: Viral Rapper Pipeline

**Project:** Viral Rapper Content Generator  
**Version:** 1.0  
**Created:** 2026-02-26  
**Status:** Planning Phase

---

## ANCHOR POINTS
- ENTRY: Telegram bot handler (`bot.py`)
- MAIN: Video generation pipeline (`pipeline.py`)
- EXPORTS: Final MP4 video to Telegram chat
- DEPS: python-telegram-bot, MoviePy, ElevenLabs, Grok API, pandas
- TODOs: See task list below

---

## Project Overview

Automated pipeline for creating viral short-form videos (TikTok/Reels format) featuring Russian rappers in themed scenarios. User interacts via Telegram bot to specify theme, select rappers, and choose which artist to promote. System generates images, voiceovers, animated videos, and assembles final MP4.

**Key Features:**
- Telegram bot interface for easy generation
- Google Sheets → CSV for rapper database
- AI-generated images (Grok Imagine / Gemini)
- Talking-head animation (Grok Imagine Video)
- Russian voiceovers (ElevenLabs)
- Vertical video format (1080x1920, 30 FPS)
- Promoted rapper placement at position 2-3
- Error handling with Telegram notifications

---

## Architecture (Render.com Deployment)

```
telegram_bot/
├── bot.py                 # Telegram bot webhook handler (Flask/FastAPI)
├── pipeline.py            # Main video generation orchestrator
├── modules/
│   ├── data_loader.py     # CSV parser for rapper data
│   ├── image_gen.py       # Google Gemini integration
│   ├── video_gen.py       # Grok Imagine Video / talking-head animation
│   ├── voice_gen.py       # ElevenLabs voiceover generation
│   ├── audio_mixer.py     # Audio ducking & background music
│   ├── video_assembler.py # MoviePy final video stitching
│   ├── keyboards.py       # Inline keyboard builder
│   ├── settings_manager.py # User settings CRUD operations
│   └── utils.py           # Helper functions (retry, logging, etc.)
├── data/
│   ├── rappers.csv        # Exported from Google Sheets
│   └── tracks/            # MP3 files for each rapper (in persistent disk)
├── database/
│   └── user_settings.db   # SQLite database (or PostgreSQL on Render)
├── temp/                  # Temporary files during generation (persistent disk)
├── output/                # Final videos (persistent disk)
├── .env                   # Default API keys (Telegram, Gemini, ElevenLabs, Grok)
├── requirements.txt       # Python dependencies
├── render.yaml            # Render.com deployment config
├── Procfile               # Process definition for Render
└── README.md              # Setup & usage instructions
```

**Render.com Specific:**
- Telegram bot runs on webhook (not polling) to avoid cold starts
- Persistent disk mounted at `/opt/render/project/data` for tracks, temp files, output
- PostgreSQL database (free tier) for user settings (recommended over SQLite)
- Web service with health check endpoint to keep service alive
- Environment variables stored in Render dashboard

---

## Technology Stack

### Core
- **Python 3.11+** — Main language
- **Flask 3.x or FastAPI 0.1x** — Web framework for Telegram webhook
- **python-telegram-bot 20.x** — Telegram bot framework (webhook mode)
- **asyncio** — Async operations for API calls
- **gunicorn** — WSGI server for production (Render.com)

### Video/Audio Processing
- **MoviePy 1.0.3** — Video editing & assembly
- **Pillow 10.x** — Image manipulation
- **pydub 0.25.x** — Audio processing & mixing
- **ffmpeg** — Backend for MoviePy (system dependency)

### Data Handling
- **pandas 2.x** — CSV parsing
- **python-dotenv** — Environment variables
- **PostgreSQL** — User settings storage (Render.com free tier includes PostgreSQL)
- **psycopg2-binary** — PostgreSQL adapter for Python
- **cryptography** — API key encryption

**Note:** SQLite can be used for local development, but PostgreSQL is recommended for Render.com deployment due to persistent disk limitations.

### APIs
- **Google Gemini API** — Image generation (primary: gemini-pro-vision or imagen-3)
- **Grok Imagine Video API** — Talking-head animation
- **ElevenLabs API** — Russian voiceover synthesis
- **yt-dlp / soundcloud-lib** — SoundCloud track downloads (manual)

### Optional (Future)
- **Celery + Redis** — Task queue for parallel processing
- **Docker** — Containerization for local development

### Deployment (Render.com)
- **Render Web Service** — Hosts Telegram webhook + video generation
- **Render PostgreSQL** — Free tier database for user settings
- **Render Persistent Disk** — 1GB free storage for tracks, temp files, output
- **Render Environment Variables** — Secure storage for API keys

---

## Data Schema

### rappers.csv (Google Sheets Export)
```csv
name,photo_url,track_path,is_promoted
Ivan (@pricolniy),https://example.com/ivan.jpg,tracks/ivan.mp3,yes
Oxxxymiron,https://example.com/oxxxy.jpg,tracks/oxxxy.mp3,no
Pharaoh,https://example.com/pharaoh.jpg,tracks/pharaoh.mp3,no
Скриптонит,https://example.com/skript.jpg,tracks/skript.mp3,no
```

**Fields:**
- `name` — Rapper display name (shown in Telegram buttons)
- `photo_url` — URL or local path to photo
- `track_path` — Path to MP3 file (relative to project root)
- `is_promoted` — "yes" if this rapper can be promoted (placed at position 2-3)

**Note:** User selects up to 6 rappers per video. If promoted rapper is selected, they appear at position 2 or 3.

### Theme Suggestions (Hardcoded)
```python
THEME_SUGGESTIONS = [
    "Президентами каких стран будут СК рэперы",
    "Кем СК рэперы работали бы в средние века",
    "Какие машины водили бы СК рэперы в будущем",
    "Какими супергероями были бы СК рэперы",
    "В каких видеоиграх были бы персонажами СК рэперы",
]
```

### User Session State
```python
@dataclass
class UserSession:
    user_id: int
    state: str  # SELECT_RAPPERS, ENTER_THEME, CONFIRM, GENERATING, SETTINGS
    selected_rappers: List[str]  # max 6
    theme: str
    message_id: int  # for editing progress updates
    created_at: datetime
```

### User Settings Schema (PostgreSQL on Render.com)
```sql
-- Table: user_settings | Purpose: Store per-user customization settings
CREATE TABLE user_settings (
    user_id BIGINT PRIMARY KEY,
    gemini_api_key TEXT,  -- Encrypted, NULL = use default
    gemini_system_prompt TEXT DEFAULT 'Generate a high-quality, realistic image of a Russian rapper as [role] in [theme] style. Professional photography, cinematic lighting, detailed background.',
    elevenlabs_api_key TEXT,  -- Encrypted, NULL = use default
    elevenlabs_voice_id TEXT DEFAULT '21m00Tcm4TlvDq8ikWAM',  -- Default Russian voice
    grok_video_api_key TEXT,  -- Encrypted, NULL = use default
    video_quality TEXT DEFAULT 'high' CHECK(video_quality IN ('high', 'medium')),  -- high=5000k, medium=3000k
    intro_duration INTEGER DEFAULT 4 CHECK(intro_duration BETWEEN 3 AND 5),  -- seconds
    clip_duration INTEGER DEFAULT 4 CHECK(clip_duration BETWEEN 3 AND 5),  -- seconds per rapper
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_settings_user_id ON user_settings(user_id);
```

**Note:** PostgreSQL is recommended for Render.com deployment. SQLite can be used for local development.

**Default Settings:**
```python
DEFAULT_SETTINGS = {
    "gemini_system_prompt": "Generate a high-quality, realistic image of a Russian rapper as [role] in [theme] style. Professional photography, cinematic lighting, detailed background.",
    "elevenlabs_voice_id": "21m00Tcm4TlvDq8ikWAM",  # Default Russian voice
    "video_quality": "high",
    "intro_duration": 4,
    "clip_duration": 4,
}
```

---

## Video Specifications

- **Format:** MP4 (H.264 codec, AAC audio)
- **Resolution:** 1080x1920 (vertical, 9:16 aspect ratio)
- **FPS:** 30
- **Video Bitrate:** 5000k
- **Audio:** 192kbps stereo
- **Duration:** 20-40 seconds (4 sec intro + 4 sec per rapper)
- **Transitions:** Simple cuts (no fancy effects)
- **Watermark:** Optional (add in Phase 5)

---

## Telegram Bot User Flow (Detailed)

### Step 1: Start Creation
```
User: /start

Bot: "Добро пожаловать в Viral Rapper Pipeline! 🎬"
     
     [Создать видео] [Настройки]
```

**If user clicks [Настройки]:**
```
Bot: "Настройки бота:"
     
     [Системный промпт Gemini]
     [API ключи]
     [Голос озвучки]
     [Качество видео]
     [Длительность клипов]
     
     [Назад]
```

**Settings Menu Options:**

**1. Системный промпт Gemini:**
```
Bot: "Текущий промпт:
     'Generate a high-quality, realistic image of a Russian rapper as [role] in [theme] style...'
     
     Отправьте новый промпт или нажмите [Сбросить на дефолт]"

User: *sends custom prompt*

Bot: "✅ Промпт обновлён!"
```

**2. API ключи:**
```
Bot: "Управление API ключами:
     
     Gemini API: ••••••••abc123 [Изменить]
     ElevenLabs API: ••••••••xyz789 [Изменить]
     Grok Video API: ••••••••def456 [Изменить]
     
     [Использовать дефолтные ключи]
     [Назад]"

User: *clicks [Изменить] for Gemini*

Bot: "Отправьте новый Gemini API ключ:"

User: *sends API key*

Bot: "✅ Gemini API ключ обновлён!"
```

**3. Голос озвучки:**
```
Bot: "Выберите голос для озвучки:
     
     [Мужской голос 1 (дефолт)]
     [Мужской голос 2]
     [Женский голос 1]
     [Женский голос 2]
     [Прослушать примеры]
     
     [Назад]"

User: *clicks voice option*

Bot: "✅ Голос обновлён!"
```

**4. Качество видео:**
```
Bot: "Качество видео:
     
     [Высокое (5000k bitrate)] ✅
     [Среднее (3000k bitrate)]
     
     [Назад]"
```

**5. Длительность клипов:**
```
Bot: "Настройка длительности:
     
     Intro: [3 сек] [4 сек] ✅ [5 сек]
     Клип рэпера: [3 сек] [4 сек] ✅ [5 сек]
     
     [Назад]"
```

---

### Step 2: Select Rappers (after clicking [Создать видео])
```
User: *clicks [Создать видео]*

Bot: "Выберите рэперов для видео (до 6):"
     [Ivan] [Oxxxy] [Pharaoh]
     [Скриптонит] [Morgenshtern] [Элджей]
     [Feduk] [Gone.Fludd] [Markul]
     ...
     
     Выбрано: 0/6
     [Подтвердить список] [Сбросить]
```

### Step 2: Select Rappers
```
User: *clicks [Ivan], [Oxxxy], [Pharaoh]*

Bot: *updates message*
     "Выберите рэперов для видео (до 6):"
     [Ivan ✅] [Oxxxy ✅] [Pharaoh ✅]
     [Скриптонит] [Morgenshtern] [Элджей]
     ...
     
     Выбрано: Ivan, Oxxxy, Pharaoh (3/6)
     [Подтвердить список] [Сбросить]

User: *clicks [Подтвердить список]*
```

### Step 3: Enter Theme
```
Bot: "Введите тему для видео или выберите из предложенных:"
     
     [Президентами каких стран будут СК рэперы]
     [Кем СК рэперы работали бы в средние века]
     [Какие машины водили бы СК рэперы в будущем]
     [Своя тема ✏️]
     
     [Сбросить]

User: *clicks [Президентами каких стран будут СК рэперы]*
```

### Step 4: Confirmation
```
Bot: "Проверьте данные перед созданием:
     
     Рэперы: Ivan, Oxxxy, Pharaoh
     Тема: Президентами каких стран будут СК рэперы
     
     [Создать видео 🎬] [Сбросить]"

User: *clicks [Создать видео 🎬]*
```

### Step 5: Generation (Live Updates)
```
Bot: *edits message every 5-10 seconds*
     "⏳ Генерация озвучки..."
     
     "⏳ Генерация изображений... 1/3"
     
     "⏳ Генерация изображений... 3/3"
     
     "⏳ Генерация видео... 1/3"
     
     "⏳ Генерация видео... 3/3"
     
     "⏳ Сборка финального видео..."
```

### Step 6: Delivery
```
Bot: "✅ Видео готово!"
     *sends viral_vibe.mp4*
     
     Caption: "Тема: Президентами каких стран будут СК рэперы
              Рэперы: Ivan, Oxxxy, Pharaoh
              Длительность: 16 сек"
     
     [Создать ещё одно видео]
```

### Error Handling
```
Bot: "❌ Ошибка при генерации видео:
     
     Grok API rate limit exceeded. Попробуйте через 5 минут.
     
     [Попробовать снова] [Сбросить]"
```

### Parallel Processing
```
User A: *starts generation at 10:00*
User B: *starts generation at 10:01*
User A: *receives video at 10:08*
User B: *receives video at 10:09*

// Each user has independent session state
// Multiple generations can run simultaneously
```

---

## Task Breakdown

### Phase 1: Project Setup & Data Layer (Week 1)
**Status:** 🔴 Not Started

#### Tasks:
- [ ] **T1.1** — Initialize Python project structure
  - Create folders: `modules/`, `data/`, `temp/`, `output/`
  - Setup `requirements.txt` with core dependencies (Flask/FastAPI, python-telegram-bot, MoviePy, psycopg2-binary)
  - Create `.env.example` template
  - Create `render.yaml` for Render.com deployment config
  - Create `Procfile` for process definition
  - **SCALED FOR:** 100k users (modular architecture, easy to add queue later)
  - // UPDATED COMMENTS: Document Render.com specific configuration

- [ ] **T1.2** — Implement CSV data loader (`data_loader.py`)
  - Parse `rappers.csv` with pandas
  - Validate required fields (name, photo_url, track_path)
  - Filter by `is_promoted` flag
  - Return list of Rapper objects (dataclass)
  - **REUSABLE LOGIC:** Can be used for other CSV-based projects

- [ ] **T1.3** — Setup environment & API key management
  - Load `.env` with python-dotenv
  - Validate required keys: `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `GROK_VIDEO_API_KEY`, `ELEVENLABS_API_KEY`
  - Add error handling for missing keys
  - **FSD:** shared/lib/config.py
  - // UPDATED COMMENTS: Document which API key is for which service

- [ ] **T1.4** — Create sample `rappers.csv` with 5 test entries
  - Include Ivan (@pricolniy) as promoted
  - Add placeholder photo URLs
  - Add sample MP3 paths (can be dummy files for now)

- [ ] **T1.5** — Initialize PostgreSQL database for user settings (Render.com)
  - Create table: `user_settings` (user_id BIGINT, gemini_api_key, gemini_system_prompt, elevenlabs_api_key, elevenlabs_voice_id, grok_video_api_key, video_quality, intro_duration, clip_duration, created_at, updated_at)
  - Add indexes on user_id for fast lookups
  - Create migration script for schema updates (use Alembic or raw SQL)
  - Support both PostgreSQL (production) and SQLite (local dev)
  - **FSD:** shared/lib/database/schema.sql
  - // UPDATED COMMENTS: Document table schema & indexes for PostgreSQL

- [ ] **T1.6** — Setup Render.com deployment files
  - Create `render.yaml` with web service, PostgreSQL, persistent disk config
  - Create `Procfile` with gunicorn command
  - Configure environment variables (TELEGRAM_BOT_TOKEN, DATABASE_URL, etc.)
  - Setup persistent disk mount at `/opt/render/project/data`
  - Add health check endpoint `/health` for Render monitoring
  - **SCALED FOR:** 100k users (auto-scaling ready)
  - // UPDATED COMMENTS: Document Render.com deployment process

**Deliverable:** Working data layer that loads rapper info from CSV + user settings from PostgreSQL + Render.com deployment ready

---

### Phase 2: API Integrations (Week 2)
**Status:** 🔴 Not Started

#### Tasks:
- [ ] **T2.1** — Google Gemini image generation (`image_gen.py`)
  - SEARCH: Research Google Gemini image generation (gemini-pro-vision vs imagen-3)
  - Implement `generate_image(prompt: str, style: str, api_key: str, system_prompt: str) -> bytes`
  - Use user's custom system_prompt if provided, otherwise use default
  - Use user's API key if provided, otherwise use default from .env
  - Add retry logic (3 attempts with exponential backoff)
  - Handle rate limits & errors (free tier: 1500 requests/day)
  - **REUSED:** Retry logic from shared/lib/api_utils.py
  - **FSD:** features/image-generation/model/gemini_api.py
  - // UPDATED COMMENTS: Full docstrings with param types & error cases

- [ ] **T2.2** — ElevenLabs voiceover client (`voice_gen.py`)
  - SEARCH: Find best Russian voice model in ElevenLabs
  - Implement `generate_voiceover(text: str, voice_id: str, api_key: str) -> bytes`
  - Generate single voiceover for intro (e.g. "Кем бы работали СК рэперы в средние века?")
  - Use user's voice_id if provided, otherwise use default
  - Use user's API key if provided, otherwise use default from .env
  - Support SSML for intonation control
  - Cache voiceovers by theme text hash (reuse for same themes)
  - **SCALED FOR:** 100k users (caching reduces API costs by 80%)
  - **FSD:** features/voiceover/model/elevenlabs_api.py
  - // UPDATED COMMENTS: Document voice_id selection & caching strategy

- [ ] **T2.3** — Grok Imagine Video client (`video_gen.py`)
  - Implement `animate_photo(image_bytes: bytes, audio_bytes: bytes, api_key: str) -> bytes`
  - 4-second clips with audio sync
  - Use user's API key if provided, otherwise use default from .env
  - Handle video generation queue (Grok may take 30-60 sec per clip)
  - Progress callback for Telegram bot updates
  - **FSD:** features/video-animation/model/grok_video_api.py
  - // UPDATED COMMENTS: Explain async polling mechanism & timeout handling

- [ ] **T2.4** — Error handling & logging
  - Centralized error handler with Telegram notifications
  - Log all API calls to `logs/api.log`
  - Track costs per generation (estimate based on API usage)
  - **REUSABLE LOGIC:** shared/lib/logger.py
  - **FSD:** shared/lib/error_handler.py
  - // UPDATED COMMENTS: Document error types & notification strategy

**Deliverable:** All API integrations working with test scripts

---

### Phase 3: Video Generation Pipeline (Week 3)
**Status:** 🔴 Not Started

#### Tasks:
- [ ] **T3.1** — Role assignment logic (`pipeline.py`)
  - Generate roles based on theme (e.g. "medieval knights" → ["King Arthur", "Lancelot", ...])
  - Use simple templates or LLM (Gemini) for creative roles
  - Ensure promoted rapper gets position 2 or 3
  - Shuffle other rappers randomly
  - // UPDATED COMMENTS: Explain role generation algorithm

- [ ] **T3.2** — Image generation orchestrator
  - For each rapper: generate prompt "Russian rapper [name] as [role] in [theme] style"
  - Call Google Gemini API for image generation
  - Save images to `temp/images/`
  - Parallel processing (asyncio.gather) for 6 rappers
  - Handle Gemini free tier limits (1500 requests/day)
  - **SCALED FOR:** 100k users (parallel API calls reduce generation time by 70%)
  - // UPDATED COMMENTS: Document prompt engineering strategy for best results

- [ ] **T3.3** — Voiceover generation (intro only)
  - Generate single voiceover script for intro: theme as question (e.g. "Кем бы работали СК рэперы в средние века?")
  - Call ElevenLabs API once per video
  - Save audio to `temp/voiceover_intro.mp3`
  - Normalize audio levels (pydub)
  - **FSD:** features/voiceover/model/generator.py
  - // UPDATED COMMENTS: Document script generation logic & audio normalization

- [ ] **T3.4** — Talking-head animation
  - For each rapper: combine image + silent placeholder → 4-sec video
  - Call Grok Imagine Video API (or use static image if animation not needed)
  - Poll for completion (async with timeout)
  - Save clips to `temp/clips/`
  - Progress updates to Telegram bot
  - **NOTE:** No voiceover per rapper, only visual animation
  - // UPDATED COMMENTS: Document polling intervals & timeout strategy

- [ ] **T3.5** — Audio mixing (`audio_mixer.py`)
  - **Intro audio:** Mix voiceover + background music (optional)
  - **Rapper clips:** Load each rapper's track (MP3), trim to 4 seconds
  - No voiceover mixing for rapper clips (only their music)
  - Normalize volume levels across all clips
  - Export mixed audio for intro + individual tracks for rapper clips
  - **REUSABLE LOGIC:** Can be used for podcast editing, etc.
  - // UPDATED COMMENTS: Document audio mixing strategy & volume normalization

**Deliverable:** End-to-end pipeline that generates all assets for one video

---

### Phase 4: Video Assembly & Telegram Bot (Week 4)
**Status:** 🔴 Not Started

#### Tasks:
- [ ] **T4.1** — Intro generation (`video_assembler.py`)
  - Create 4-second intro with theme text overlay
  - Add single voiceover audio (generated by ElevenLabs)
  - Option 1: Static background with text animation
  - Option 2: Collage of all rapper photos
  - **FSD:** features/video-assembly/ui/intro.py
  - // UPDATED COMMENTS: Document text overlay positioning & animation

- [ ] **T4.2** — Final video assembly (`video_assembler.py`)
  - Use MoviePy to concatenate: intro (with voiceover) + rapper clips (with their tracks)
  - Vertical format 1080x1920, 30 FPS
  - Use user's video_quality setting (high: 5000k, medium: 3000k bitrate)
  - Use user's intro_duration and clip_duration settings
  - Add subtle transitions (0.2 sec fade)
  - Audio: intro has voiceover, each rapper clip has their own track
  - Render to `output/viral_vibe_[timestamp].mp4`
  - Optimize encoding (H.264, CRF 23)
  - // UPDATED COMMENTS: Explain MoviePy clip composition & audio layering

- [ ] **T4.3** — Telegram bot webhook handler (`bot.py`)
  - Setup Flask/FastAPI web server for webhook endpoint
  - `/webhook` — Receive Telegram updates via POST
  - `/health` — Health check endpoint for Render.com
  - `/set_webhook` — Helper endpoint to register webhook with Telegram
  - Inline keyboard handlers for rapper selection
  - Callback query handlers for buttons (confirm, reset, theme selection, settings)
  - Message handler for custom theme input
  - Settings menu handlers (system prompt, API keys, voice, quality, duration)
  - ConversationHandler for multi-step flow (using in-memory or Redis for state)
  - **FSD:** features/telegram-bot/model/handlers.py
  - **SCALED FOR:** 100k users (webhook mode handles high traffic better than polling)
  - // UPDATED COMMENTS: Document webhook setup & callback_data format

- [ ] **T4.4** — Conversation state management
  - Store user state: selected_rappers (list, max 6), theme (str), message_id (int)
  - Use ConversationHandler states: SELECT_RAPPERS, ENTER_THEME, CONFIRM, GENERATING, SETTINGS, EDIT_PROMPT, EDIT_API_KEY, etc.
  - Support parallel sessions (multiple users generating simultaneously)
  - State storage: in-memory dict for free tier, Redis for production scaling
  - No timeout (user can take their time selecting)
  - **SCALED FOR:** 100k users (use Redis for state in production, in-memory for free tier)
  - // UPDATED COMMENTS: Explain session isolation per user_id & state persistence strategy

- [ ] **T4.4.1** — Inline keyboard builder (`modules/keyboards.py`)
  - Build rapper selection grid (3-4 columns)
  - Toggle checkmarks ✅ on selected rappers
  - Disable buttons when 6 rappers selected
  - Theme suggestion buttons with callback_data
  - Settings menu keyboard with nested options
  - Reset button on every keyboard
  - **REUSABLE LOGIC:** Generic keyboard builder for other bots
  - // UPDATED COMMENTS: Document button layout algorithm

- [ ] **T4.4.2** — User settings manager (`modules/settings_manager.py`)
  - Load/save user settings from PostgreSQL database (or SQLite for local dev)
  - Validate API keys (test with simple API call)
  - Merge user settings with default settings
  - Encrypt API keys in database (use cryptography library)
  - Connection pooling for PostgreSQL (use psycopg2 pool)
  - **FSD:** features/settings/model/settings_db.py
  - **SCALED FOR:** 100k users (indexed by user_id, connection pooling)
  - // UPDATED COMMENTS: Document encryption strategy, validation logic & PostgreSQL connection handling

- [ ] **T4.5** — Progress notifications
  - Edit last message with status updates every 5-10 seconds
  - "⏳ Генерация изображений... 2/6"
  - "⏳ Генерация видео... 4/6"
  - "⏳ Сборка финального видео..."
  - Use Telegram edit_message_text with message_id from state
  - Handle Telegram rate limits (max 1 edit per 3 seconds)
  - **SCALED FOR:** 100k users (queue updates to avoid rate limits)
  - // UPDATED COMMENTS: Document message update rate limits & retry logic

- [ ] **T4.6** — Video delivery
  - Send final MP4 to user via `bot.send_video()`
  - Caption: "✅ Видео готово! Тема: [theme] | Рэперы: [list] | Длительность: [duration]"
  - Add [Создать ещё одно видео] button below video
  - Clean up temp files after delivery (images, audio, clips)
  - Log generation metadata (user_id, theme, rappers, duration, cost, timestamp)
  - **FSD:** features/video-delivery/model/sender.py
  - // UPDATED COMMENTS: Document cleanup strategy & error recovery

**Deliverable:** Fully functional Telegram bot that generates & delivers videos

---

### Phase 5: Testing, Optimization & Polish (Week 5)
**Status:** 🔴 Not Started

#### Tasks:
- [ ] **T5.1** — End-to-end testing
  - Test with 3 different themes
  - Test random vs manual rapper selection
  - Test promoted rapper placement
  - Verify video quality on mobile devices
  - **REUSE CHECK:** Use existing test frameworks (pytest)

- [ ] **T5.2** — Error handling improvements
  - Test API failures (rate limits, timeouts)
  - Test invalid CSV data
  - Test missing MP3 files
  - Ensure graceful degradation
  - Send detailed error messages to Telegram

- [ ] **T5.3** — Cost optimization
  - Implement voiceover caching (save by theme text hash)
  - Reuse images for same rapper+theme combo
  - Batch API calls where possible
  - Track actual costs per video
  - **SCALED FOR:** 100k users (caching reduces costs by 50%)
  - // UPDATED COMMENTS: Document caching strategy & cost tracking

- [ ] **T5.4** — Performance tuning
  - Profile bottlenecks (cProfile)
  - Optimize MoviePy rendering (use threads)
  - Reduce temp file I/O
  - Target: <10 minutes per video generation
  - // UPDATED COMMENTS: Document performance benchmarks

- [ ] **T5.5** — Documentation
  - README.md with setup instructions
  - API key setup guide
  - Google Sheets template
  - Troubleshooting common errors
  - **REUSABLE LOGIC:** Template for other bot projects

- [ ] **T5.6** — Optional features
  - Add watermark with user's logo
  - Support custom intro music
  - Export generation history to CSV
  - Add /stats command (total videos, costs)

**Deliverable:** Production-ready bot with documentation

---

## Current Status

### Completed Tasks
- ✅ Product documentation (`docs/product.md`)
- ✅ Development plan (`docs/development_plan.md`)

### In Progress
- 🟡 None

### Blocked
- 🔴 None

### Backlog
- All Phase 1-5 tasks (see above)

---

## Next Steps

1. **Immediate (Today):**
   - Create Google Sheets with 15-20 Russian rappers
   - Get API keys: Telegram Bot Token, Gemini, ElevenLabs, Grok Video
   - Download sample MP3 tracks for testing
   - Create Render.com account

2. **This Week:**
   - Start Phase 1: Project setup & data layer
   - Setup Render.com deployment files (render.yaml, Procfile)
   - Test CSV parsing with sample data
   - Validate API keys with simple test scripts
   - Test Gemini image generation with sample prompts

3. **Next Week:**
   - Begin Phase 2: API integrations
   - Deploy to Render.com with PostgreSQL
   - Setup Telegram webhook
   - Test Google Gemini with Russian rapper prompts
   - Test ElevenLabs with Russian text
   - Test Grok Imagine Video with sample image+audio

---

## Risk Assessment

### High Risk
- **Render.com free tier sleep** — Service sleeps after 15 min inactivity
  - Mitigation: Telegram webhook automatically wakes service on user message
- **512MB RAM limitation** — May not be enough for 6 rappers with MoviePy
  - Mitigation: Process videos sequentially, optimize memory usage, upgrade to Starter plan if needed
- **Grok Imagine Video API availability** — May have rate limits or high latency
  - Mitigation: Implement queue system, add timeout handling
- **ElevenLabs Russian voice quality** — May sound robotic
  - Mitigation: Test multiple voice models, adjust SSML

### Medium Risk
- **Video rendering time** — MoviePy may be slow for 1080x1920 on 512MB RAM
  - Mitigation: Use GPU acceleration (ffmpeg), optimize encoding params, process sequentially
- **API costs** — May exceed $2/video if not optimized
  - Mitigation: Use Gemini free tier, implement voiceover caching
- **Gemini image quality** — May need prompt engineering for consistent style
  - Mitigation: Test multiple prompts, add style guidelines
- **Persistent disk space** — 1GB may fill up quickly with videos
  - Mitigation: Delete old videos after delivery, use external storage (S3) if needed

### Low Risk
- **CSV data management** — Manual export from Google Sheets
  - Mitigation: Document export process, consider Sheets API later
- **Telegram bot rate limits** — May hit limits with progress updates
  - Mitigation: Throttle updates to 1 per 3 seconds
- **PostgreSQL free tier expiration** — Free for 90 days, then $7/month
  - Mitigation: Migrate to external PostgreSQL (ElephantSQL, Supabase) or use SQLite with persistent disk

---

## Cost Breakdown (Per Video, 6 Rappers)

| Service | Usage | Cost |
|---------|-------|------|
| Google Gemini | 6 images | $0.06 (or FREE with tier) |
| Grok Imagine Video | 6 × 4 sec clips | $1.20 |
| ElevenLabs | 1 voiceover (intro only) | $0.10 |
| **Total** | | **$1.36** |

**With Gemini free tier:** ~$1.30/video  
**Optimization potential:** With image caching, reduce to ~$0.80/video

---

## Success Metrics

- ✅ Video generation time: <10 minutes
- ✅ Success rate: >95% (no API failures)
- ✅ Video quality: 1080x1920, 30 FPS, no artifacts
- ✅ Cost per video: <$1.50 (with optimizations)
- ✅ User satisfaction: Easy Telegram bot flow, <5 steps

---

**Last Updated:** 2026-02-26  
**Next Review:** After Phase 1 completion
