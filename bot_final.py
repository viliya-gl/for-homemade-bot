import os
from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# ============================================================
# 1. ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (СЕКРЕТЫ)
# ============================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
OWNER_TELEGRAM_ID = int(os.getenv("OWNER_TELEGRAM_ID", 0))

# ============================================================
# 2. НАСТРОЙКА GROQ
# ============================================================
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
)

# ============================================================
# 3. ОТПРАВКА В АДМИН-БОТА
# ============================================================
async def send_to_admin_bot(question, user_id, user_name):
    try:
        admin_app = Application.builder().token(ADMIN_BOT_TOKEN).build()
        await admin_app.bot.send_message(
            chat_id=OWNER_TELEGRAM_ID,
            text=f"QUESTION|{user_id}|{user_name}|{question}"
        )
        print(f"📨 Вопрос отправлен админ-боту: {question}")
    except Exception as e:
        print(f"⚠️ Ошибка отправки админу: {e}")

# ============================================================
# 4. ГЕНЕРАЦИЯ ОТВЕТА
# ============================================================
async def generate_answer(question, user_id=None, user_name=None):
    if not question or len(question) < 3:
        return "😊 Напиши, пожалуйста, чуть подробнее — я смогу точнее помочь."

    prompt = f"""
Ты — Валли, цифровой хранитель бренда for.homemade. Ты общаешься с клиентами в Telegram.

Твоя задача: ответить на вопрос клиента **человеческим, тёплым голосом**.

Правила:
1. Отвечай **кратко и по делу** (2–4 предложения).
2. Не используй маркдаун, звёздочки, подчёркивания.
3. Если не знаешь точного ответа — скажи: «Я не знаю, но передам твой вопрос основателю».
4. Если вопрос про ароматы — предложи 2–3 варианта и спроси, какой нравится.

Вопрос клиента: {question}

Твой ответ:
"""
    try:
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": "Ты — Валли, тёплый и дружелюбный помощник бренда for.homemade. Отвечай коротко, без маркдауна, по-человечески."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=400
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Ошибка генерации: {e}")
        return "Произошла ошибка. Попробуйте позже."

# ============================================================
# 5. КНОПКИ
# ============================================================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛍 Магазин", url="https://instagram.com/твой_аккаунт")],
        [InlineKeyboardButton("🆘 Помощь", callback_data="help")],
        [InlineKeyboardButton("🏆 Лояльность", callback_data="loyalty")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============================================================
# 6. ОБРАБОТЧИКИ TELEGRAM
# ============================================================
async def start(update: Update, context):
    await update.message.reply_text(
        "👋 Привет! Я Валли — твой цифровой помощник for.homemade.\n\n"
        "Я знаю всё о наших ароматах, мелтсах, доставке и оплате.\n"
        "Расскажи, что тебя интересует, и я помогу!\n\n"
        "А если я не знаю ответа — передам твой вопрос основателю лично 🔥",
        reply_markup=get_main_keyboard()
    )

async def handle_message(update: Update, context):
    question = update.message.text
    user = update.message.from_user
    user_id = user.id
    user_name = user.first_name

    print(f"\n📩 Вопрос от {user_name} (ID: {user_id}): {question}")

    answer = await generate_answer(question, user_id, user_name)

    if "не знаю" in answer.lower() or "передам" in answer.lower():
        await send_to_admin_bot(question, user_id, user_name)
        await update.message.reply_text(answer, reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text(answer)

async def button_callback(update: Update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        await query.message.reply_text(
            "📩 Если у тебя сложный вопрос или я не смогла помочь — напиши основателю напрямую:\n"
            "👉 @твой_телеграм_никнейм",
            reply_markup=get_main_keyboard()
        )
    elif query.data == "loyalty":
        await query.message.reply_text(
            "🏆 Скоро здесь будет система лояльности!\n"
            "А пока — следи за новостями в нашем Instagram 📸",
            reply_markup=get_main_keyboard()
        )

# ============================================================
# 7. ЗАПУСК БОТА
# ============================================================
def main():
    print("🚀 Запуск бота for.homemade (Groq, без Chroma)...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()