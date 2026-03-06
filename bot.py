import logging
import time
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, CommandHandler, ContextTypes, filters

# Токен из переменных окружения (безопасно!)
TOKEN = os.getenv("BOT_TOKEN", "8778902859:AAEoxPJHpNm4p-Gvdny1ct2-83mm2f9oxrA")

ADMIN_ID = 1585791662
ADMIN_USERNAME = "@MrMoro_5675"
CHANNEL_ID = "@MrMoro_Lyalakaet"

MAX_PENDING = 100
pending_messages = {}

# Защита от спама
user_last_message = {}
SPAM_TIMEOUT = 5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def format_user_info(user, source=None):
    name = user.full_name

    if source:
        return f'👥 {name} (источник: "{source}")'
    else:
        return f'👤 {name}'


# ========== СЛОВАРЬ ОБРАБОТЧИКОВ ==========
MEDIA_HANDLERS = {
    'text': lambda bot, chat_id, msg, caption: bot.send_message(chat_id=chat_id, text=caption),
    'photo': lambda bot, chat_id, msg, caption: bot.send_photo(chat_id=chat_id, photo=msg.photo[-1].file_id, caption=caption),
    'video': lambda bot, chat_id, msg, caption: bot.send_video(chat_id=chat_id, video=msg.video.file_id, caption=caption),
    'audio': lambda bot, chat_id, msg, caption: bot.send_audio(chat_id=chat_id, audio=msg.audio.file_id, caption=caption),
    'voice': lambda bot, chat_id, msg, caption: bot.send_voice(chat_id=chat_id, voice=msg.voice.file_id, caption=caption),
    'animation': lambda bot, chat_id, msg, caption: bot.send_animation(chat_id=chat_id, animation=msg.animation.file_id, caption=caption),
}

# ========== ПУБЛИКАЦИЯ В КАНАЛ ==========
async def publish_to_channel(context, message_info):
    user = message_info["user"]
    source = message_info.get("source")
    original_message = message_info["message"]

    signature = format_user_info(user, source)

    try:
        # ========== ОСОБЫЙ СЛУЧАЙ: ВИДЕОКРУЖКИ ==========
        if original_message.video_note:
            await context.bot.send_video_note(
                chat_id=CHANNEL_ID,
                video_note=original_message.video_note.file_id
            )
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=signature
            )
            return  # Выходим, чтобы не попасть в общий обработчик

        # Определяем тип сообщения и caption для остальных типов
        msg_type = None
        caption = None
        
        if original_message.text:
            msg_type = 'text'
            caption = f"{original_message.text}\n\n{signature}"
        elif original_message.photo:
            msg_type = 'photo'
            base_caption = original_message.caption or ""
            caption = f"{base_caption}\n\n{signature}".strip()
        elif original_message.video:
            msg_type = 'video'
            base_caption = original_message.caption or ""
            caption = f"{base_caption}\n\n{signature}".strip()
        elif original_message.audio:
            msg_type = 'audio'
            base_caption = original_message.caption or ""
            caption = f"{base_caption}\n\n{signature}".strip()
        elif original_message.voice:
            msg_type = 'voice'
            caption = signature
        elif original_message.animation:
            msg_type = 'animation'
            base_caption = original_message.caption or ""
            caption = f"{base_caption}\n\n{signature}".strip()

        # Отправляем через словарь обработчиков
        if msg_type and msg_type in MEDIA_HANDLERS:
            await MEDIA_HANDLERS[msg_type](context.bot, CHANNEL_ID, original_message, caption)
        else:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"⚠️ Тип сообщения не поддерживается\n\n{signature}"
            )

    except Exception as e:
        logger.error(f"Ошибка публикации: {e}")


# ========== ОБРАБОТЧИК ПРЕДЛОЖЕК ==========
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    user = update.effective_user

    # Не создаем предложку от самого админа
    if user.id == ADMIN_ID:
        return

    # Защита от спама
    now = time.time()
    if user.id in user_last_message:
        time_diff = now - user_last_message[user.id]
        if time_diff < SPAM_TIMEOUT:
            wait_time = int(SPAM_TIMEOUT - time_diff)
            await message.reply_text(f"⏳ Подожди {wait_time} сек. перед новой предложкой")
            return

    user_last_message[user.id] = now

    unique_id = f"{update.effective_chat.id}_{message.message_id}"

    # Определяем источник
    source = None
    if message.forward_from_chat:
        if message.forward_from_chat.username:
            source = f"@{message.forward_from_chat.username}"
        else:
            source = message.forward_from_chat.title
    elif message.forward_from:
        if message.forward_from.username:
            source = f"@{message.forward_from.username}"
        else:
            source = message.forward_from.full_name

    # Сохраняем предложку
    pending_messages[unique_id] = {
        "user": user,
        "message": message,
        "source": source
    }

    # Автоочистка старых предложек
    if len(pending_messages) > MAX_PENDING:
        oldest = next(iter(pending_messages))
        del pending_messages[oldest]

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Опубликовать", callback_data=f"publish_{unique_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{unique_id}")
        ]
    ])

    await context.bot.copy_message(
        chat_id=ADMIN_ID,
        from_chat_id=update.effective_chat.id,
        message_id=message.message_id
    )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📨 Новая предложка\n\n👤 {user.full_name}",
        reply_markup=keyboard
    )

    await update.message.reply_text("✅ Предложка отправлена!")


# ========== ОБРАБОТЧИК КНОПОК ==========
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # Проверяем, что кнопку нажимает админ
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Только админ может нажимать кнопки", show_alert=True)
        return

    data = query.data
    await query.answer()

    if data.startswith("publish_"):
        message_id = data.replace("publish_", "")

        if message_id in pending_messages:
            message_info = pending_messages[message_id]
            await publish_to_channel(context, message_info)
            del pending_messages[message_id]
            await query.edit_message_text("✅ Опубликовано")
        else:
            await query.edit_message_text("❌ Предложка устарела или уже обработана")

    elif data.startswith("reject_"):
        message_id = data.replace("reject_", "")

        if message_id in pending_messages:
            del pending_messages[message_id]
            await query.edit_message_text("❌ Отклонено")
        else:
            await query.edit_message_text("❌ Предложка уже не существует")


# ========== КОМАНДЫ ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение"""
    user = update.effective_user
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"📝 Я бот-предложка для канала @MrMoro_Lyalakaet\n\n"
        f"📨 Отправь мне любое сообщение (текст, фото, видео, голосовое), "
        f"и оно уйдёт админу на проверку.\n"
        f"Если одобрят — появится в канале!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь"""
    await update.message.reply_text(
        "📚 **Как пользоваться:**\n"
        "1. Отправь любое сообщение\n"
        "2. Оно уйдет администратору на проверку\n"
        "3. Если одобрят — появится в канале\n\n"
        "Поддерживаются: текст, фото, видео, аудио, голосовые, кружки",
        parse_mode='Markdown'
    )


# ========== ЗАПУСК ==========
def main():
    if not TOKEN:
        print("❌ ОШИБКА: BOT_TOKEN не найден!")
        return

    print("=" * 50)
    print("🚀 ПРЕДЛОЖКА ЗАПУЩЕНА")
    print("=" * 50)
    print(f"👤 Админ: {ADMIN_ID}")
    print(f"📢 Канал: {CHANNEL_ID}")
    print(f"⏱ Защита от спама: {SPAM_TIMEOUT} сек.")
    print(f"📦 Макс. ожидающих: {MAX_PENDING}")
    print("=" * 50)

    app = Application.builder().token(TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))

    # Обработчики
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))
    app.add_handler(CallbackQueryHandler(handle_buttons))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

