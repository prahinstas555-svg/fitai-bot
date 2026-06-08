# bot.py — FitAI с памятью, кнопками и расчётом калорий по фото 🤖💪📸
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
        ["🔥 Мотивация", "📸 Калории по фото"],
        ["🔄 Новый диалог"],
    ],
    resize_keyboard=True   # кнопки компактные
)

# 💾 ПАМЯТЬ: хранит историю для каждого пользователя
user_history = {}

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    await update.message.reply_text(
        "Привет! 💪 Я FitAI — твой ИИ фитнес-тренер.\n"
        "Выбери кнопку ниже или просто напиши мне! 🔥\n\n"
        "📸 А ещё я могу посчитать калории по фото твоей еды!",
        reply_markup=menu_keyboard
    )

# Обработка ВСЕХ текстовых сообщений
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

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

    if user_text == "📸 Калории по фото":
        await update.message.reply_text(
            "Пришли мне фото своей еды 🍽️\n"
            "Я определю блюдо и посчитаю калории и БЖУ! 🔢",
            reply_markup=menu_keyboard
        )
        return

    if user_text == "🏋️ Тренировка":
        user_text = "Предложи мне тренировку на сегодня"
    elif user_text == "🥗 Питание":
        user_text = "Дай совет по питанию на сегодня"
    elif user_text == "🔥 Мотивация":
        user_text = "Замотивируй меня на тренировку!"

    await update.message.chat.send_action("typing")

    user_history[user_id].append({"role": "user", "content": user_text})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=user_history[user_id],
    )
    answer = response.choices[0].message.content

    user_history[user_id].append({"role": "assistant", "content": answer})

    # 🧹 Храним последние 20 сообщений
    if len(user_history[user_id]) > 21:
        user_history[user_id] = (
            [user_history[user_id][0]] + user_history[user_id][-20:]
        )

    await update.message.reply_text(answer, reply_markup=menu_keyboard)

# 📸 НОВОЕ: Обработка ФОТО — расчёт калорий через Groq Vision
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action("typing")
    await update.message.reply_text("Анализирую фото... 🔍🍽️")

    # Берём фото в лучшем качестве и получаем ссылку на него
    photo = await update.message.photo[-1].get_file()
    photo_url = photo.file_path

    try:
        # Отправляем фото в Groq Vision (бесплатная модель)
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Определи, какое блюдо или продукты на фото. "
                                "Посчитай примерные калории, белки, жиры и углеводы. "
                                "Отвечай ТОЛЬКО на русском языке, дружелюбно, с эмодзи. "
                                "Формат:\n"
                                "🍽️ Что на фото\n"
                                "🔢 Калории: ... ккал\n"
                                "🥩 Белки / 🥑 Жиры / 🍚 Углеводы\n"
                                "💡 Короткий совет от тренера. "
                                "Если на фото не еда — скажи об этом."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": photo_url},
                        },
                    ],
                }
            ],
        )
        answer = response.choices[0].message.content
    except Exception as e:
        answer = (
            "Упс, не получилось разобрать фото 😔\n"
            "Попробуй сделать фото чётче и при хорошем свете. 📷"
        )
        print("Ошибка vision:", e)

    await update.message.reply_text(answer, reply_markup=menu_keyboard)

# Запуск
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))  # 📸 фото
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    print("Бот с памятью, кнопками и расчётом калорий запущен! ✅📸")
    app.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
