import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# Токен твоего бота от BotFather
TOKEN = "8778902859:AAFByvDJGksCuPapFAKKYiF6t0-3WB3TTpU"

# ID канала (куда публиковать)
CHANNEL_ID = "@MrMoro_Lyalakaet"

# ТВОЙ USERNAME и ID
ADMIN_USERNAME = "@MrMoro_5675"
ADMIN_ID = 1585791662  # Твой числовой ID

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище для ожидающих подтверждения сообщений
pending_messages = {}
# Хранилище для забаненных пользователей
banned_users = set()  # Множество ID забаненных пользователей

def is_admin(user) -> bool:
    """Проверяет, является ли пользователь админом"""
    if user.id == ADMIN_ID:
        return True
    if user.username and f"@{user.username}" == ADMIN_USERNAME:
        return True
    return False

def is_banned(user_id: int) -> bool:
    """Проверяет, забанен ли пользователь"""
    return user_id in banned_users

# ========== ФУНКЦИЯ ПОДПИСИ ==========
def make_signature(message):
    """Создает подпись для сообщения с учётом источника"""
    user = message.from_user
    full_name = user.full_name or user.first_name

    if message.forward_from_chat:
        chat = message.forward_from_chat
        source = f"@{chat.username}" if chat.username else chat.title
        sender_name = message.forward_from.first_name if message.forward_from else chat.title
        return f"👥 {sender_name} (источник: \"{source}\")"

    if message.forward_from:
        sender_name = message.forward_from.full_name or message.forward_from.first_name
        if message.forward_from.username:
            source = f"@{message.forward_from.username}"
            return f"👥 {sender_name} (источник: \"{source}\")"
        else:
            return f"👤 {sender_name}"

    return f"👤 {full_name}"

# ========== ФУНКЦИЯ ПУБЛИКАЦИИ ==========
async def publish_to_channel(context, message_info):
    """Публикует сообщение в канал с подписью ВНИЗУ"""
    
    original_message = message_info['message']
    signature = make_signature(original_message)

    try:
        # ТЕКСТ
        if original_message.text:
            final_text = f"{original_message.text}\n\n{signature}"
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=final_text
            )

        # ФОТО
        elif original_message.photo:
            caption = original_message.caption or ""
            final_caption = f"{caption}\n\n{signature}" if caption else signature
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=original_message.photo[-1].file_id,
                caption=final_caption
            )

        # ВИДЕО
        elif original_message.video:
            caption = original_message.caption or ""
            final_caption = f"{caption}\n\n{signature}" if caption else signature
            await context.bot.send_video(
                chat_id=CHANNEL_ID,
                video=original_message.video.file_id,
                caption=final_caption
            )

        # ГИФКИ
        elif original_message.animation:
            caption = original_message.caption or ""
            final_caption = f"{caption}\n\n{signature}" if caption else signature
            await context.bot.send_animation(
                chat_id=CHANNEL_ID,
                animation=original_message.animation.file_id,
                caption=final_caption
            )

        # АУДИО
        elif original_message.audio:
            caption = original_message.caption or ""
            final_caption = f"{caption}\n\n{signature}" if caption else signature
            await context.bot.send_audio(
                chat_id=CHANNEL_ID,
                audio=original_message.audio.file_id,
                caption=final_caption
            )

        # ГОЛОСОВЫЕ
        elif original_message.voice:
            await context.bot.send_voice(
                chat_id=CHANNEL_ID,
                voice=original_message.voice.file_id,
                caption=signame
            )

        # ВИДЕОКРУЖКИ (БЕЗ ПОДПИСИ)
        elif original_message.video_note:
            await context.bot.send_video_note(
                chat_id=CHANNEL_ID,
                video_note=original_message.video_note.file_id
            )

        # Всё остальное
        else:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"⚠️ Неподдерживаемый тип\n\n{signature}"
            )

    except Exception as e:
        logger.error(f"Ошибка при публикации: {e}")

# ========== КОМАНДЫ ДЛЯ АДМИНА ==========

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Блокирует пользователя по username или ID"""
    user = update.effective_user
    
    if not is_admin(user):
        await update.message.reply_text("⛔ Только админ может использовать эту команду")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Использование: `/ban @username` или `/ban 123456789`\n"
            "Пример: `/ban @spammer`",
            parse_mode='Markdown'
        )
        return
    
    target = context.args[0]
    
    try:
        # Пытаемся получить информацию о пользователе
        if target.startswith('@'):
            username = target[1:]  # Убираем @
            # Ищем пользователя в pending_messages
            user_id = None
            for msg in pending_messages.values():
                if msg['user'].username and msg['user'].username.lower() == username.lower():
                    user_id = msg['user'].id
                    break
            
            if user_id:
                banned_users.add(user_id)
                await update.message.reply_text(f"✅ Пользователь {target} заблокирован")
            else:
                # Если не нашли в pending, просто баним по username (сохраняем в отдельный словарь)
                banned_users.add(target)  # Временно, лучше хранить username отдельно
                await update.message.reply_text(f"✅ Пользователь {target} заблокирован (по username)")
        else:
            # Баним по ID
            try:
                user_id = int(target)
                banned_users.add(user_id)
                await update.message.reply_text(f"✅ Пользователь с ID {user_id} заблокирован")
            except ValueError:
                await update.message.reply_text("❌ Неверный формат. Укажи @username или числовой ID")
    
    except Exception as e:
        logger.error(f"Ошибка в ban: {e}")
        await update.message.reply_text("❌ Ошибка при блокировке")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Разблокирует пользователя"""
    user = update.effective_user
    
    if not is_admin(user):
        await update.message.reply_text("⛔ Только админ может использовать эту команду")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Использование: `/unban @username` или `/unban 123456789`",
            parse_mode='Markdown'
        )
        return
    
    target = context.args[0]
    
    try:
        if target.startswith('@'):
            # Удаляем из бана по username
            if target in banned_users:
                banned_users.remove(target)
                await update.message.reply_text(f"✅ Пользователь {target} разблокирован")
            else:
                await update.message.reply_text(f"❌ Пользователь {target} не найден в списке забаненных")
        else:
            try:
                user_id = int(target)
                if user_id in banned_users:
                    banned_users.remove(user_id)
                    await update.message.reply_text(f"✅ Пользователь с ID {user_id} разблокирован")
                else:
                    await update.message.reply_text(f"❌ Пользователь с ID {user_id} не найден в списке забаненных")
            except ValueError:
                await update.message.reply_text("❌ Неверный формат")
    
    except Exception as e:
        logger.error(f"Ошибка в unban: {e}")
        await update.message.reply_text("❌ Ошибка при разблокировке")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет сообщение всем пользователям, которые когда-либо писали боту"""
    user = update.effective_user
    
    if not is_admin(user):
        await update.message.reply_text("⛔ Только админ может использовать эту команду")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Использование: `/broadcast Текст сообщения для всех`",
            parse_mode='Markdown'
        )
        return
    
    broadcast_text = ' '.join(context.args)
    
    # Собираем уникальные ID пользователей из pending_messages
    users_to_notify = set()
    for msg_info in pending_messages.values():
        users_to_notify.add(msg_info['user'].id)
    
    if not users_to_notify:
        await update.message.reply_text("❌ Нет пользователей для рассылки")
        return
    
    # Отправляем сообщение каждому пользователю
    success_count = 0
    fail_count = 0
    
    for user_id in users_to_notify:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 **Сообщение от администратора:**\n\n{broadcast_text}",
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
            fail_count += 1
    
    await update.message.reply_text(
        f"✅ Рассылка завершена!\n"
        f"📨 Отправлено: {success_count}\n"
        f"❌ Не удалось: {fail_count}"
    )

# ========== КОМАНДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ==========

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает правила канала"""
    await update.message.reply_text(
        "📋 **Правила канала:**\n\n"
        "1. 18+ не кидать, а именно: Расчленнёнку, Свастику, большие жопы\n"
        "2. Не спамьте\n"
        "3. \n"
        "4. \n\n"
        "Нарушение правил может привести к блокировке.",
        parse_mode='Markdown'
    )

# ========== ОБРАБОТЧИК СООБЩЕНИЙ ==========
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает сообщения от обычных пользователей"""
    try:
        message = update.effective_message
        user = update.effective_user
        
        # Проверяем, не забанен ли пользователь
        if is_banned(user.id):
            await message.reply_text("⛔ Вы заблокированы и не можете отправлять сообщения.")
            return
        
        # Сохраняем информацию о сообщении
        message_id = message.message_id
        pending_messages[message_id] = {
            'from_chat_id': update.effective_chat.id,
            'message_id': message_id,
            'user': user,
            'message': message
        }
        
        # Копируем сообщение админу
        await context.bot.copy_message(
            chat_id=ADMIN_ID,
            from_chat_id=update.effective_chat.id,
            message_id=message_id
        )

        # Определяем тип сообщения для превью
        if message.text:
            content_preview = "📝 Текст"
            preview = message.text[:50] + "..." if len(message.text) > 50 else message.text
        elif message.photo:
            content_preview = "🖼 Фото"
            preview = message.caption or "Без подписи"
        elif message.video:
            content_preview = "🎥 Видео"
            preview = message.caption or "Без подписи"
        elif message.audio:
            content_preview = "🎵 Аудио"
            preview = message.caption or "Без подписи"
        elif message.voice:
            content_preview = "🎤 Голосовое"
            preview = "Голосовое сообщение"
        elif message.video_note:
            content_preview = "🔄 Видеокружок"
            preview = "Видеосообщение"
        else:
            content_preview = "📎 Другое"
            preview = "Неизвестный тип"
        
        # Формируем строку отправителя
        sender_line = f"{user.full_name}"
        if user.username:
            sender_line += f" (@{user.username})"
        
        # Создаем пример подписи
        signature_example = make_signature(message)
        
        # Кнопки для админа
        admin_keyboard = [
            [
                InlineKeyboardButton("✅ Опубликовать", callback_data=f"publish_{message_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{message_id}")
            ]
        ]
        
        # Отправляем уведомление админу с кнопками
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(f"📨 **Новое сообщение**\n\n"
                  f"👤 От: {sender_line}\n"
                  f"📎 Тип: {content_preview}\n"
                  f"🔍 Превью: {preview}\n"
                  f"📝 Подпись будет: {signature_example}\n\n"
                  f"Выбери действие:"),
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode='Markdown'
        )
        
        # Пользователю отправляем простое сообщение
        await message.reply_text(
            "✅ Твоё сообщение отправлено администратору на рассмотрение!\n"
            "Если оно будет одобрено, оно появится в канале.\n\n"
            "📋 Используй /rules чтобы узнать правила канала."
        )
        
        logger.info(f"Сообщение от {user.id} отправлено админу на модерацию")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("❌ Произошла ошибка")

# ========== ОБРАБОТЧИК КНОПОК ==========
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия на кнопки"""
    query = update.callback_query
    await query.answer()
    
    try:
        data = query.data
        message_id = int(data.split('_')[1])
        
        if data.startswith('publish_'):
            if message_id in pending_messages:
                await publish_to_channel(context, pending_messages[message_id])
                
                await context.bot.send_message(
                    chat_id=pending_messages[message_id]['from_chat_id'],
                    text="✅ Твоё сообщение было одобрено и опубликовано в канале!"
                )
                
                await query.edit_message_text("✅ Опубликовано!")
                del pending_messages[message_id]
                
        elif data.startswith('reject_'):
            if message_id in pending_messages:
                await context.bot.send_message(
                    chat_id=pending_messages[message_id]['from_chat_id'],
                    text="❌ Твоё сообщение не прошло модерацию."
                )
                
                await query.edit_message_text("❌ Отклонено")
                del pending_messages[message_id]
                
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await query.edit_message_text("❌ Ошибка")

# ========== КОМАНДЫ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение"""
    user = update.effective_user
    
    if is_admin(user):
        await update.message.reply_text(
            f"👋 Привет, админ!\n\n"
            f"📢 Канал: {CHANNEL_ID}\n"
            f"📝 Ты будешь получать уведомления о новых сообщениях.\n\n"
            f"📋 Доступные команды:\n"
            f"/ban @user - заблокировать пользователя\n"
            f"/unban @user - разблокировать\n"
            f"/broadcast текст - отправить сообщение всем"
        )
    else:
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            f"📝 Твои сообщения будут отправлены администратору на рассмотрение.\n"
            f"Используй /rules чтобы узнать правила канала."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь"""
    user = update.effective_user
    
    if is_admin(user):
        await update.message.reply_text(
            "📚 **Команды для админа:**\n"
            "/start - Начать работу\n"
            "/help - Эта справка\n"
            "/ban @user - заблокировать пользователя\n"
            "/unban @user - разблокировать\n"
            "/broadcast текст - отправить сообщение всем\n\n"
            "📨 Ты получаешь уведомления о каждом сообщении\n"
            "и решаешь - публиковать или нет."
        )
    else:
        await update.message.reply_text(
            "📚 **Как пользоваться ботом:**\n"
            "1. Отправь любое сообщение\n"
            "2. Оно уйдет администратору на проверку\n"
            "3. Если одобрят - появится в канале\n\n"
            "📋 Правила: /rules"
        )

# ========== ЗАПУСК ==========
def main():
    """Запуск бота"""
    print("=" * 60)
    print("🤖 ЗАПУСК БОТА-ПРЕДЛОЖКИ")
    print("=" * 60)
    print(f"📢 Канал: {CHANNEL_ID}")
    print(f"👤 Админ: {ADMIN_USERNAME} (ID: {ADMIN_ID})")
    print("=" * 60)
    
    application = Application.builder().token(TOKEN).build()
    
    # Команды для админа
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # Команды для пользователей
    application.add_handler(CommandHandler("rules", rules_command))
    
    # Обработчик сообщений
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("✅ Бот-предложка готов!")
    print("📨 Уведомления будут приходить только админу")
    print(f"👥 Забаненных пользователей: {len(banned_users)}")
    print("=" * 60)
    
    application.run_polling()

if __name__ == "__main__":
    main()
