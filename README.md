# Viral Rapper Pipeline

Automated Telegram bot for creating viral short-form videos featuring Russian rappers.

## Features

- 🎬 Generate viral videos (TikTok/Reels format)
- 🎤 Russian rapper themes with AI-generated images
- 🗣️ ElevenLabs voiceover
- 🎥 Grok Imagine Video animation
- ⚙️ Customizable settings per user
- 📊 Google Sheets integration for rapper data

## Tech Stack

- **Backend:** Python 3.11, Flask
- **Bot:** python-telegram-bot (webhook mode)
- **Database:** PostgreSQL (Render.com)
- **Video:** MoviePy, ffmpeg
- **APIs:** Google Gemini, ElevenLabs, Grok Imagine Video
- **Deployment:** Render.com

## Setup

### 1. Prerequisites

- Python 3.11+
- PostgreSQL (or use Render.com free tier)
- Google Sheets with rapper data
- API keys: Telegram, Gemini, ElevenLabs, Grok Video

### 2. Google Sheets Setup

1. Create a Google Sheets with columns:
   - `name` - Rapper display name
   - `photo_url` - URL to photo
   - `track_path` - Path to MP3 file
   - `is_promoted` - "yes" or "no"

2. Share sheet with service account email (from credentials JSON)

3. Get Sheet ID from URL:
   ```
   https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit
   ```

### 3. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project
3. Enable Google Sheets API
4. Create Service Account:
   - IAM & Admin → Service Accounts → Create
   - Grant "Editor" role
   - Create JSON key
5. Download JSON key → Save as `credentials/google-sheets-key.json`

### 4. Local Development

```bash
# Clone repository
git clone <repo-url>
cd viral-rapper-pipeline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env

# Test Google Sheets connection
python -m modules.data_loader

# Run bot locally
python bot.py
```

### 5. Render.com Deployment

1. Create account on [Render.com](https://render.com)

2. Create PostgreSQL database:
   - New → PostgreSQL
   - Name: `viral-rapper-db`
   - Plan: Free

3. Create Web Service:
   - New → Web Service
   - Connect GitHub repo
   - Name: `viral-rapper-bot`
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn bot:app --bind 0.0.0.0:$PORT --workers 2 --timeout 600`

4. Add Environment Variables in Render dashboard:
   ```
   TELEGRAM_BOT_TOKEN=<your_token>
   GEMINI_API_KEY=<your_key>
   ELEVENLABS_API_KEY=<your_key>
   GROK_VIDEO_API_KEY=<your_key>
   GOOGLE_SHEETS_ID=1NguIwl1SYsPPwx7gKZZgBsF_QNjQfIY6gbkTS6qJKZM
   GOOGLE_SHEETS_CREDENTIALS_JSON=<paste_json_content>
   DATABASE_URL=<auto_populated_by_render>
   ENCRYPTION_KEY=<auto_generated>
   WEBHOOK_URL=https://your-app.onrender.com/webhook
   ```

5. Deploy and set webhook:
   ```bash
   curl https://your-app.onrender.com/set_webhook
   ```

## Environment Variables

See `.env.example` for full list of required variables.

### Required:
- `TELEGRAM_BOT_TOKEN` - From @BotFather
- `GOOGLE_SHEETS_ID` - From Google Sheets URL
- `GOOGLE_SHEETS_CREDENTIALS_JSON` - Service account JSON
- `GEMINI_API_KEY` - Google Gemini API
- `ELEVENLABS_API_KEY` - ElevenLabs API
- `GROK_VIDEO_API_KEY` - Grok Imagine Video API

### Optional:
- `DATABASE_URL` - PostgreSQL connection (auto-set by Render)
- `ENCRYPTION_KEY` - For encrypting API keys in DB
- `WEBHOOK_URL` - Your Render.com URL

## Usage

1. Start bot: `/start`
2. Click "Создать видео"
3. Select up to 6 rappers
4. Choose theme
5. Confirm and wait for generation
6. Receive video in Telegram

## Project Structure

```
viral-rapper-pipeline/
├── bot.py                 # Main bot webhook handler
├── modules/
│   ├── data_loader.py     # Google Sheets integration
│   ├── keyboards.py       # Inline keyboard builder
│   ├── settings_manager.py # User settings (PostgreSQL)
│   └── pipeline.py        # Video generation pipeline
├── credentials/
│   └── google-sheets-key.json  # Service account key (gitignored)
├── data/
│   └── tracks/            # MP3 files
├── temp/                  # Temporary files
├── output/                # Generated videos
├── requirements.txt       # Python dependencies
├── render.yaml            # Render.com config
├── Procfile               # Process definition
└── .env                   # Environment variables (gitignored)
```

## Troubleshooting

### Google Sheets Error
- Check service account has access to sheet
- Verify GOOGLE_SHEETS_ID is correct
- Test with: `python -m modules.data_loader`

### Webhook Not Working
- Check WEBHOOK_URL is correct
- Run: `curl https://your-app.onrender.com/set_webhook`
- Check Render logs for errors

### Database Connection Error
- Verify DATABASE_URL is set
- Check PostgreSQL is running
- Run migrations: `psql $DATABASE_URL < docs/init_db.sql`

## License

MIT

## Author

Ivan (@pricolniy)
