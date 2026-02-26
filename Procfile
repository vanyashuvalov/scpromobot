# Procfile for Render.com Deployment
# Purpose: Define how to run the Telegram bot web service

# Web process: Run Flask/FastAPI app with gunicorn
# - bot:app = bot.py file, app variable (Flask/FastAPI instance)
# - --bind 0.0.0.0:$PORT = Listen on Render's assigned port
# - --workers 2 = 2 worker processes (adjust based on RAM usage)
# - --timeout 600 = 10 minute timeout for long video generation
# - --worker-class uvicorn.workers.UvicornWorker = Use if using FastAPI instead of Flask
web: gunicorn bot:app --bind 0.0.0.0:$PORT --workers 2 --timeout 600

# Alternative for FastAPI:
# web: uvicorn bot:app --host 0.0.0.0 --port $PORT --workers 2

# Note: Render automatically sets $PORT environment variable
