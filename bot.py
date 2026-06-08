# bot.py — FitAI с памятью и кнопками 🤖💪
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from groq import Groq

# 🔑 КЛЮЧИ
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

# Роль тренера
SYSTEM_PROMPT = (
    "Ты — FitAI, дружелюбный и мотивирующий ИИ фитнес-тренер. "
    "Ты помогаешь с тренировками, питанием и мотивацией. "
    "ВАЖНО: отвечай ВСЕГДА только на русском языке, "
    "не используй слова из других языков. "
    "Отвечай понятно, по делу, с эмодзи. "
    "Если вопрос про здоровье — советуй обратиться к врачу."
)

# 📱 КНОПКИ-МЕНЮ (внизу экрана)
menu_keyboard = ReplyKeyboardMarkup(
    [
        ["🏋️ Тренировка", "🥗 Питание"],
        ["🔥 Мотивация", "🔄 Новый диалог"],
    ],
    resize_keyboard=True   # кнопки компактные
)

# 💾 ПАМЯТЬ: хранит историю для каждого пользователя
# (словарь: id пользователя → список сообщений)
user_history = {}

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Очищаем историю при старте
    user_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    await update.message.reply_text(
        "Привет! 💪 Я FitAI — твой ИИ фитнес-тренер.\n"
        "Выбери кнопку ниже или просто напиши мне! 🔥",
        reply_markup=menu_keyboard   # показываем кнопки
    )

# Обработка ВСЕХ сообщений
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    # Если памяти ещё нет — создаём
    if user_id not in user_history:
        user_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 🔘 Обработка кнопок
    if user_text == "🔄 Новый диалог":
        user_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        await update.message.reply_text(
            "Начали заново! 🆕 О чём поговорим?",
            reply_markup=menu_keyboard
        )
        return

    if user_text == "🏋️ Тренировка":
        user_text = "Предложи мне тренировку на сегодня"
    elif user_text == "🥗 Питание":
        user_text = "Дай совет по питанию на сегодня"
    elif user_text == "🔥 Мотивация":
        user_text = "Замотивируй меня на тренировку!"

    # Показываем "печатает..."
    await update.message.chat.send_action("typing")

    # Добавляем сообщение пользователя в память
    user_history[user_id].append({"role": "user", "content": user_text})

    # Спрашиваем Groq, передавая ВСЮ историю
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=user_history[user_id],
    )
    answer = response.choices[0].message.content

    # Сохраняем ответ бота в память
    user_history[user_id].append({"role": "assistant", "content": answer})

    # 🧹 Чтобы память не разрасталась — храним последние 20 сообщений
    if len(user_history[user_id]) > 21:  # 1 системный + 20 диалоговых
        user_history[user_id] = (
            [user_history[user_id][0]] + user_history[user_id][-20:]
        )

    await update.message.reply_text(answer, reply_markup=menu_keyboard)

# Запуск
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    print("Бот с памятью и кнопками запущен! ✅")
    app.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
