"""
Viral Rapper Pipeline - Telegram Bot
Version: 1.0
Created: 2026-02-26

Purpose: Telegram bot webhook handler for viral video generation
Dependencies: Flask 3.0, python-telegram-bot 20.7, PostgreSQL
Architecture: Webhook-based bot for Render.com deployment

## ANCHOR POINTS
- ENTRY: Flask app with /webhook endpoint
- MAIN: Telegram bot handlers (start, settings, video generation)
- EXPORTS: Flask app instance for gunicorn
- DEPS: Flask, python-telegram-bot, modules/data_loader
- TODOs: Implement video generation pipeline, settings persistence
"""

import os
import logging
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv

# Import data loader
from modules.data_loader import load_rappers, Rapper

# Load environment variables
load_dotenv()

# ============================================
# Configuration
# ============================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 5000))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
MAX_RAPPERS_PER_VIDEO = int(os.getenv("MAX_RAPPERS_PER_VIDEO", 6))

# ============================================
# Logging Setup
# ============================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# Flask App Setup
# ============================================
app = Flask(__name__)

# ============================================
# Telegram Bot Setup
# ============================================
# Initialize bot application
bot_application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# ============================================
# Conversation States
# ============================================
# States for ConversationHandler
SELECT_RAPPERS = 1
ENTER_THEME = 2
CUSTOM_THEME = 3
CONFIRM = 4
GENERATING = 5
SETTINGS = 6
EDIT_PROMPT = 7
EDIT_API_KEY = 8
EDIT_VOICE = 9

# ============================================
# In-Memory State Storage (for free tier)
# TODO: Migrate to Redis for production scaling
# ============================================
user_sessions = {}  # {user_id: {state, selected_rappers, theme, message_id}}

# ============================================
# Theme Suggestions
# ============================================
THEME_SUGGESTIONS = [
    "Президентами каких стран будут СК рэперы",
    "Кем СК рэперы работали бы в средние века",
    "Какие машины водили бы СК рэперы в будущем",
    "Какими супергероями были бы СК рэперы",
    "В каких видеоиграх были бы персонажами СК рэперы",
]

# ============================================
# Helper Functions
# ============================================

def get_user_session(user_id: int) -> dict:
    """
    Get or create user session state
    
    Args:
        user_id: Telegram user ID
    
    Returns:
        dict: User session data
    
    // REUSABLE LOGIC: Session management pattern
    """
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "state": None,
            "selected_rappers": [],
            "theme": None,
            "message_id": None,
        }
    return user_sessions[user_id]


def clear_user_session(user_id: int):
    """
    Clear user session (reset to initial state)
    
    Args:
        user_id: Telegram user ID
    
    // Used when user clicks "Сбросить" button
    """
    if user_id in user_sessions:
        user_sessions[user_id] = {
            "state": None,
            "selected_rappers": [],
            "theme": None,
            "message_id": None,
        }


def build_rapper_keyboard(selected_rappers: list, all_rappers: list) -> InlineKeyboardMarkup:
    """
    Build inline keyboard for rapper selection
    
    Args:
        selected_rappers: List of selected rapper names
        all_rappers: List of all Rapper objects
    
    Returns:
        InlineKeyboardMarkup: Keyboard with rapper buttons
    
    // REUSABLE LOGIC: Keyboard builder pattern
    """
    keyboard = []
    row = []
    
    for i, rapper in enumerate(all_rappers):
        is_selected = rapper.name in selected_rappers
        button_text = f"{rapper.name} ✅" if is_selected else rapper.name
        
        row.append(InlineKeyboardButton(
            button_text,
            callback_data=f"rapper_{i}"
        ))
        
        # Create new row every 2 buttons (better for long names)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    # Add remaining buttons
    if row:
        keyboard.append(row)
    
    # Add control buttons
    selected_count = len(selected_rappers)
    keyboard.append([
        InlineKeyboardButton(
            f"Подтвердить список ({selected_count}/{MAX_RAPPERS_PER_VIDEO})",
            callback_data="confirm_rappers"
        )
    ])
    keyboard.append([
        InlineKeyboardButton("Сбросить", callback_data="reset")
    ])
    
    return InlineKeyboardMarkup(keyboard)


# ============================================
# Telegram Bot Handlers
# ============================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command - Show main menu
    
    Flow:
    1. Welcome message
    2. Show [Создать видео] [Настройки] buttons
    
    // UPDATED COMMENTS: Entry point for all users
    """
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started bot")
    
    # Create main menu keyboard
    keyboard = [
        [InlineKeyboardButton("Создать видео", callback_data="create_video")],
        [InlineKeyboardButton("Настройки", callback_data="settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Добро пожаловать в Viral Rapper Pipeline, {user.first_name}!\n\n"
        "Создавайте вирусные видео с русскими рэперами за несколько кликов.",
        reply_markup=reply_markup
    )


async def create_video_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle "Создать видео" button click
    
    Flow:
    1. Load rappers from Google Sheets
    2. Show rapper selection keyboard (up to 6)
    3. Transition to SELECT_RAPPERS state
    
    // FSD: features/video-creation/ui/rapper_selection.py
    """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    session = get_user_session(user_id)
    session["state"] = SELECT_RAPPERS
    session["selected_rappers"] = []
    
    try:
        # Load rappers from Google Sheets
        rappers = load_rappers()
        
        if not rappers:
            await query.edit_message_text(
                "Ошибка: список рэперов пуст. Обратитесь к администратору.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Назад", callback_data="back_to_main")
                ]])
            )
            return ConversationHandler.END
        
        # Store rappers in context for later use
        context.user_data['rappers'] = rappers
        
        # Build keyboard
        reply_markup = build_rapper_keyboard(session["selected_rappers"], rappers)
        
        await query.edit_message_text(
            f"Выберите рэперов для видео (до {MAX_RAPPERS_PER_VIDEO}):\n\n"
            f"Выбрано: 0/{MAX_RAPPERS_PER_VIDEO}",
            reply_markup=reply_markup
        )
        
        return SELECT_RAPPERS
        
    except Exception as e:
        logger.error(f"Error loading rappers: {e}")
        await query.edit_message_text(
            f"Ошибка при загрузке данных: {str(e)}\n\n"
            "Попробуйте позже или обратитесь к администратору.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Назад", callback_data="back_to_main")
            ]])
        )
        return ConversationHandler.END


async def rapper_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle rapper button clicks (toggle selection)
    
    Logic:
    1. Toggle rapper in/out of selected list
    2. Max 6 rappers
    3. Update keyboard with checkmarks
    
    // SCALED FOR: 100k users (in-memory state, migrate to Redis later)
    """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    session = get_user_session(user_id)
    
    # Get rappers from context
    rappers = context.user_data.get('rappers', [])
    if not rappers:
        await query.answer("Ошибка: данные рэперов не найдены", show_alert=True)
        return SELECT_RAPPERS
    
    # Extract rapper index from callback_data
    rapper_index = int(query.data.split("_")[1])
    
    if rapper_index >= len(rappers):
        await query.answer("Ошибка: неверный индекс рэпера", show_alert=True)
        return SELECT_RAPPERS
    
    rapper_name = rappers[rapper_index].name
    
    # Toggle selection
    if rapper_name in session["selected_rappers"]:
        session["selected_rappers"].remove(rapper_name)
    else:
        # Max rappers check
        if len(session["selected_rappers"]) < MAX_RAPPERS_PER_VIDEO:
            session["selected_rappers"].append(rapper_name)
        else:
            await query.answer(f"Максимум {MAX_RAPPERS_PER_VIDEO} рэперов!", show_alert=True)
            return SELECT_RAPPERS
    
    # Rebuild keyboard with updated selections
    reply_markup = build_rapper_keyboard(session["selected_rappers"], rappers)
    
    selected_count = len(session["selected_rappers"])
    selected_names = ", ".join(session["selected_rappers"]) if session["selected_rappers"] else "нет"
    
    await query.edit_message_text(
        f"Выберите рэперов для видео (до {MAX_RAPPERS_PER_VIDEO}):\n\n"
        f"Выбрано: {selected_names} ({selected_count}/{MAX_RAPPERS_PER_VIDEO})",
        reply_markup=reply_markup
    )
    
    return SELECT_RAPPERS


async def confirm_rappers_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle "Подтвердить список" button
    
    Flow:
    1. Validate at least 1 rapper selected
    2. Show theme selection
    3. Transition to ENTER_THEME state
    
    // FSD: features/video-creation/ui/theme_selection.py
    """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    session = get_user_session(user_id)
    
    # Validate selection
    if not session["selected_rappers"]:
        await query.answer("Выберите хотя бы одного рэпера!", show_alert=True)
        return SELECT_RAPPERS
    
    session["state"] = ENTER_THEME
    
    # Build theme selection keyboard
    keyboard = []
    for i, theme in enumerate(THEME_SUGGESTIONS):
        keyboard.append([InlineKeyboardButton(theme, callback_data=f"theme_{i}")])
    
    keyboard.append([InlineKeyboardButton("Своя тема ✏️", callback_data="custom_theme")])
    keyboard.append([InlineKeyboardButton("Сбросить", callback_data="reset")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Введите тему для видео или выберите из предложенных:",
        reply_markup=reply_markup
    )
    
    return ENTER_THEME


async def theme_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle theme button clicks
    
    Flow:
    1. Save selected theme
    2. Show confirmation screen
    3. Transition to CONFIRM state
    
    // FSD: features/video-creation/ui/confirmation.py
    """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    session = get_user_session(user_id)
    
    # Extract theme index from callback_data
    theme_index = int(query.data.split("_")[1])
    
    if theme_index >= len(THEME_SUGGESTIONS):
        await query.answer("Ошибка: неверный индекс темы", show_alert=True)
        return ENTER_THEME
    
    session["theme"] = THEME_SUGGESTIONS[theme_index]
    session["state"] = CONFIRM
    
    # Show confirmation
    selected_rappers_text = "\n".join([f"• {name}" for name in session["selected_rappers"]])
    
    keyboard = [
        [InlineKeyboardButton("Создать видео 🎬", callback_data="start_generation")],
        [InlineKeyboardButton("Сбросить", callback_data="reset")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Проверьте данные перед созданием:\n\n"
        f"Рэперы:\n{selected_rappers_text}\n\n"
        f"Тема: {session['theme']}",
        reply_markup=reply_markup
    )
    
    return CONFIRM


async def custom_theme_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle "Своя тема" button click
    
    Flow:
    1. Ask user to type custom theme
    2. Transition to CUSTOM_THEME state
    
    // Waits for text message from user
    """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    session = get_user_session(user_id)
    session["state"] = CUSTOM_THEME
    
    keyboard = [[InlineKeyboardButton("Сбросить", callback_data="reset")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Введите свою тему для видео:\n\n"
        "Например: 'Какими животными были бы СК рэперы'",
        reply_markup=reply_markup
    )
    
    return CUSTOM_THEME


async def custom_theme_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle custom theme text input
    
    Flow:
    1. Save custom theme
    2. Show confirmation screen
    3. Transition to CONFIRM state
    
    // Processes text message from user
    """
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    custom_theme = update.message.text.strip()
    
    if not custom_theme:
        await update.message.reply_text(
            "Тема не может быть пустой. Попробуйте ещё раз:"
        )
        return CUSTOM_THEME
    
    session["theme"] = custom_theme
    session["state"] = CONFIRM
    
    # Show confirmation
    selected_rappers_text = "\n".join([f"• {name}" for name in session["selected_rappers"]])
    
    keyboard = [
        [InlineKeyboardButton("Создать видео 🎬", callback_data="start_generation")],
        [InlineKeyboardButton("Сбросить", callback_data="reset")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Проверьте данные перед созданием:\n\n"
        f"Рэперы:\n{selected_rappers_text}\n\n"
        f"Тема: {session['theme']}",
        reply_markup=reply_markup
    )
    
    return CONFIRM


async def start_generation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle "Создать видео" button - Start video generation
    
    Flow:
    1. Show "Generating..." message
    2. TODO: Call video generation pipeline
    3. Send progress updates
    4. Send final video
    
    // FSD: features/video-generation/model/pipeline.py
    """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    session = get_user_session(user_id)
    session["state"] = GENERATING
    
    # Show generating message
    await query.edit_message_text(
        "⏳ Генерация видео началась...\n\n"
        "Это может занять 5-10 минут.\n"
        "Вы получите уведомление когда видео будет готово."
    )
    
    # TODO: Implement video generation pipeline
    # For now, just show a placeholder message
    await context.bot.send_message(
        chat_id=user_id,
        text="🚧 Генерация видео пока не реализована.\n\n"
        f"Ваш заказ:\n"
        f"• Рэперы: {', '.join(session['selected_rappers'])}\n"
        f"• Тема: {session['theme']}\n\n"
        "Функционал будет добавлен в следующей версии!"
    )
    
    # Clear session
    clear_user_session(user_id)
    
    # Show main menu
    keyboard = [
        [InlineKeyboardButton("Создать ещё одно видео", callback_data="create_video")],
        [InlineKeyboardButton("Настройки", callback_data="settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=user_id,
        text="Главное меню:",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle "Настройки" button click
    
    Flow:
    1. Show settings menu
    2. Options: System prompt, API keys, Voice, Quality, Duration
    
    // FSD: features/settings/ui/settings_menu.py
    // TODO: Implement settings persistence with PostgreSQL
    """
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Системный промпт Gemini", callback_data="edit_prompt")],
        [InlineKeyboardButton("API ключи", callback_data="edit_api_keys")],
        [InlineKeyboardButton("Голос озвучки", callback_data="edit_voice")],
        [InlineKeyboardButton("Качество видео", callback_data="edit_quality")],
        [InlineKeyboardButton("Длительность клипов", callback_data="edit_duration")],
        [InlineKeyboardButton("Назад", callback_data="back_to_main")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Настройки бота:\n\n"
        "🚧 Функционал настроек будет добавлен в следующей версии.",
        reply_markup=reply_markup
    )
    
    return SETTINGS


async def back_to_main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle "Назад" button - Return to main menu
    
    // Returns to main menu without clearing session
    """
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Создать видео", callback_data="create_video")],
        [InlineKeyboardButton("Настройки", callback_data="settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Главное меню:",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END


async def reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle "Сбросить" button - Clear session and return to main menu
    
    // Clears user session and shows main menu
    """
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    clear_user_session(user_id)
    
    keyboard = [
        [InlineKeyboardButton("Создать видео", callback_data="create_video")],
        [InlineKeyboardButton("Настройки", callback_data="settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Главное меню:",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END


# ============================================
# Flask Routes
# ============================================

@app.route("/")
def index():
    """
    Root endpoint - Basic info
    
    // Health check for Render.com
    """
    return jsonify({
        "status": "ok",
        "service": "Viral Rapper Pipeline Bot",
        "version": "1.0"
    })


@app.route("/health")
def health():
    """
    Health check endpoint for Render.com monitoring
    
    Returns:
        JSON with status
    
    // UPDATED COMMENTS: Required by Render.com for service health monitoring
    """
    return jsonify({"status": "healthy"}), 200


@app.route("/webhook", methods=["POST"])
async def webhook():
    """
    Telegram webhook endpoint
    
    Flow:
    1. Receive update from Telegram
    2. Process with bot application
    3. Return 200 OK
    
    // SCALED FOR: 100k users (webhook handles high traffic)
    """
    try:
        update = Update.de_json(request.get_json(force=True), bot_application.bot)
        await bot_application.process_update(update)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/set_webhook")
async def set_webhook():
    """
    Helper endpoint to set Telegram webhook
    
    Usage: curl https://your-app.onrender.com/set_webhook
    
    // Run this once after deployment to register webhook with Telegram
    """
    try:
        webhook_url = f"{WEBHOOK_URL}"
        await bot_application.bot.set_webhook(webhook_url)
        return jsonify({
            "status": "ok",
            "webhook_url": webhook_url
        }), 200
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================
# Bot Handlers Registration
# ============================================

def setup_handlers():
    """
    Register all bot handlers
    
    // UPDATED COMMENTS: ConversationHandler manages multi-step flows
    """
    # Conversation handler for video creation flow
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(create_video_callback, pattern="^create_video$")
        ],
        states={
            SELECT_RAPPERS: [
                CallbackQueryHandler(rapper_selection_callback, pattern="^rapper_\\d+$"),
                CallbackQueryHandler(confirm_rappers_callback, pattern="^confirm_rappers$"),
                CallbackQueryHandler(reset_callback, pattern="^reset$"),
            ],
            ENTER_THEME: [
                CallbackQueryHandler(theme_selection_callback, pattern="^theme_\\d+$"),
                CallbackQueryHandler(custom_theme_callback, pattern="^custom_theme$"),
                CallbackQueryHandler(reset_callback, pattern="^reset$"),
            ],
            CUSTOM_THEME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, custom_theme_message),
                CallbackQueryHandler(reset_callback, pattern="^reset$"),
            ],
            CONFIRM: [
                CallbackQueryHandler(start_generation_callback, pattern="^start_generation$"),
                CallbackQueryHandler(reset_callback, pattern="^reset$"),
            ],
            GENERATING: [
                # No handlers during generation
            ],
            SETTINGS: [
                CallbackQueryHandler(back_to_main_callback, pattern="^back_to_main$"),
                # TODO: Add settings handlers
            ],
        },
        fallbacks=[
            CallbackQueryHandler(reset_callback, pattern="^reset$"),
            CallbackQueryHandler(back_to_main_callback, pattern="^back_to_main$"),
        ],
    )
    
    # Register handlers
    bot_application.add_handler(CommandHandler("start", start_command))
    bot_application.add_handler(conv_handler)
    bot_application.add_handler(CallbackQueryHandler(settings_callback, pattern="^settings$"))
    
    logger.info("Bot handlers registered successfully")


# ============================================
# Application Initialization
# ============================================

# Setup handlers on import
setup_handlers()

# ============================================
# Main Entry Point
# ============================================

if __name__ == "__main__":
    """
    Run Flask app for local development
    
    Production: Use gunicorn (see Procfile)
    """
    logger.info(f"Starting bot in {ENVIRONMENT} mode on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=(ENVIRONMENT == "development"))

# // UPDATED COMMENTS: Complete webhook-based bot with Google Sheets integration
# // TODO: Implement video generation pipeline (Phase 3)
# // TODO: Implement settings persistence with PostgreSQL (Phase 4)
