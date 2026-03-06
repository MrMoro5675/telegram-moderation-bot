import logging
import time
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, ContextTypes, filters

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


async def publish_to_channel(context, message_info):
    user = message_info["user"]
    source = message_info.get("source")

    signature = format_user_info(user, source)

    original_message = message_info["message"]

    try:
        if original_message.text:
            final_text = f"{original_message.text}\n\n{signature}"
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=final_text
            )

        elif original_message.photo:
            caption = original_message.caption or ""
            final_caption = f"{caption}\n\n{signature}" if caption else signature
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=original_message.photo[-1].file_id,
                caption=final_caption
            )

        elif original_message.video:
            caption = original_message.caption or ""
            final_caption = f"{caption}\n\n{signature}" if caption else signature
            await context.bot.send_video(
                chat_id=CHANNEL_ID,
                video=original_message.video.file_id,
                caption=final_caption
            )

        elif original_message.audio:
            caption = original_message.caption or ""
            final_caption = f"{caption}\n\n{signature}" if caption else signature
            await context.bot.send_audio(
                chat_id=CHANNEL_ID,
                audio=original_message.audio.file_id,
                caption=final_caption
            )

        elif original_message.voice:
            await context.bot.send_voice(
                chat_id=CHANNEL_ID,
                voice=original_message.voice.file_id
            )
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=signature
            )

        elif original_message.video_note:
            await context.bot.send_video_note(
                chat_id=CHANNEL_ID,
                video_note=original_message.video_note.file_id
            )
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=signature
            )

        else:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"⚠️ Тип сообщения не поддерживается\n\n{signature}"
            )

    except Exception as e:
        logger.error(f"Ошибка публикации: {e}")


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

    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))
    app.add_handler(CallbackQueryHandler(handle_buttons))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
