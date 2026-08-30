import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# ============================================================
# 1. ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (СЕКРЕТЫ)
# ============================================================
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
OWNER_TELEGRAM_ID = int(os.getenv("OWNER_TELEGRAM_ID", 0))
MAIN_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Токен основного бота

# ============================================================
# 2. ХРАНИЛИЩЕ ВОПРОСОВ
# ============================================================
PENDING_FILE = "pending_questions.json"

def load_pending():
    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_pending(data):
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================
# 3. ОТПРАВКА КЛИЕНТУ (через основной бот)
# ============================================================
async def send_to_client(user_id, text):
    try:
        from telegram.ext import Application
        app = Application.builder().token(MAIN_BOT_TOKEN).build()
        await app.bot.send_message(chat_id=user_id, text=text)
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки клиенту: {e}")
        return False

# ============================================================
# 4. ОБРАБОТЧИКИ
# ============================================================
async def start(update: Update, context):
    await update.message.reply_text(
        "👋 Привет! Я — админ-бот for.homemade.\n\n"
        "Я буду присылать тебе вопросы, на которые основной бот не знает ответа.\n"
        "Ты сможешь отвечать на них, и ответ будет отправлен клиенту.\n\n"
        "Просто нажми «Ответить» под вопросом и напиши свой ответ."
    )

async def handle_forwarded_question(update: Update, context):
    text = update.message.text
    if not text.startswith("QUESTION|"):
        return

    try:
        parts = text.split("|")
        user_id = parts[1]
        user_name = parts[2]
        question = parts[3]

        pending = load_pending()
        pending[user_id] = {
            "question": question,
            "user_name": user_name,
            "timestamp": datetime.now().isoformat()
        }
        save_pending(pending)

        keyboard = [
            [
                InlineKeyboardButton("💬 Ответить", callback_data=f"answer_{user_id}"),
                InlineKeyboardButton("❌ Пропустить", callback_data=f"skip_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"📩 **Новый вопрос от пользователя**\n\n"
            f"👤 {user_name}\n"
            f"🆔 {user_id}\n\n"
            f"❓ {question}\n\n"
            f"Нажми «Ответить», чтобы написать клиенту.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        print(f"⚠️ Ошибка обработки вопроса: {e}")

async def button_callback(update: Update, context):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = data.split("_")[1]

    if data.startswith("answer_"):
        context.user_data["reply_to_user"] = user_id
        await query.message.reply_text(
            f"✍️ Напиши ответ для пользователя `{user_id}`.\n\n"
            f"Я отправлю его клиенту.",
            parse_mode="Markdown"
        )

    elif data.startswith("skip_"):
        pending = load_pending()
        if user_id in pending:
            del pending[user_id]
            save_pending(pending)
        await query.message.reply_text(f"✅ Вопрос от `{user_id}` пропущен.")

async def handle_owner_reply(update: Update, context):
    user_id = context.user_data.get("reply_to_user")
    if not user_id:
        await update.message.reply_text(
            "🤔 Я не знаю, кому отправить ответ. Нажми «Ответить» на вопросе сначала."
        )
        return

    answer = update.message.text
    pending = load_pending()
    user_data = pending.get(user_id)

    if not user_data:
        await update.message.reply_text("❌ Вопрос уже удалён или пропущен.")
        return

    success = await send_to_client(user_id, f"📩 **Ответ от основателя:**\n\n{answer}")

    if success:
        await update.message.reply_text(
            f"✅ Ответ отправлен пользователю @{user_data['user_name']}!"
        )
        if user_id in pending:
            del pending[user_id]
            save_pending(pending)
        context.user_data["reply_to_user"] = None
    else:
        await update.message.reply_text("⚠️ Не удалось отправить ответ. Попробуй позже.")

# ============================================================
# 5. ЗАПУСК БОТА
# ============================================================
def main():
    print("🚀 Запуск админ-бота for.homemade...")
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_forwarded_question))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_owner_reply))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("✅ Админ-бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()