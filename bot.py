# bot.py — FitAI Trainer 🤖💪📸 (с счётчиком юзеров)
import json
import os
from telegram import Update, ReplyKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from groq import Groq

USERS_FILE = "users.json"  # файл, где храним юзеров

def load_users():
    """Читаем список юзеров из файла"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_user(user_id):
    """Добавляем нового юзера в файл"""
    users = load_users()
    users.add(user_id)
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

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
    resize_keyboard=True
)

# 💾 ПАМЯТЬ: история для каждого пользователя
user_history = {}

# 👇 СЮДА свой id (если не уверен — бот сам покажет, см. /stats)
MY_ID = 1580782517

# Команда /start — красивое приветствие
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    welcome_text = (
        f"👋 Привет, *{user_name}*!\n\n"
        "💪 Я — *FitAI Trainer*, твой персональный\n"
        "ИИ фитнес-тренер. Вот что я умею:\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🏋️ *Тренировки* — программы под тебя\n"
        "🥗 *Питание* — советы и рецепты\n"
        "🔥 *Мотивация* — заряд энергии\n"
        "📸 *Калории по фото* — пришли фото еды,\n"
        "      и я посчитаю калории и БЖУ!\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "✨ _Выбери кнопку ниже или просто напиши мне!_"
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=menu_keyboard,
        parse_mode="Markdown"
    )

# 📊 Команда /stats — статистика (только для тебя)
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    my_real_id = update.effective_user.id  # твой настоящий id

    if my_real_id != MY_ID:
        await update.message.reply_text(
            f"⛔ Доступ запрещён.\n\n"
            f"Твой id: {my_real_id}\n"
            f"В коде MY_ID: {MY_ID}\n\n"
            f"Если это ТЫ — скопируй свой id выше\n"
            f"и вставь его в строку MY_ID в коде!"
        )
        return

    users = load_users()
    await update.message.reply_text(
        f"📊 Статистика бота:\n\n"
        f"👥 Всего пользователей: {len(users)}"
    )

# Команды для меню Telegram (быстрые действия)
async def workout_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_message(update, "Предложи мне тренировку на сегодня")

async def food_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_message(update, "Дай совет по питанию на сегодня")

async def motivate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_message(update, "Замотивируй меня на тренировку!")

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    await update.message.reply_text(
        "Начали заново! 🆕 О чём поговорим?",
        reply_markup=menu_keyboard
    )

# Обработка ВСЕХ текстовых сообщений
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    # 🔘 Обработка кнопок
    if user_text == "🔄 Новый диалог":
        await reset_cmd(update, context)
        return

    if user_text == "📸 Калории по фото":
        await update.message.reply_text(
            "📸 Пришли мне фото своей еды 🍽️\n"
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

    await process_message(update, user_text)

# 🧠 Общая функция: отправляет текст в ИИ и отвечает
async def process_message(update: Update, user_text: str):
    user_id = update.effective_user.id

    if user_id not in user_history:
        user_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

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

# 📸 Обработка ФОТО — расчёт калорий через Groq Vision
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action("typing")
    await update.message.reply_text("Анализирую фото... 🔍🍽️")

    photo = await update.message.photo[-1].get_file()
    photo_url = photo.file_path

    try:
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

# Устанавливаем команды в меню Telegram
async def set_commands(app):
    commands = [
        BotCommand("start", "🚀 Запустить бота"),
        BotCommand("workout", "🏋️ Тренировка на сегодня"),
        BotCommand("food", "🥗 Совет по питанию"),
        BotCommand("motivate", "🔥 Мотивация"),
        BotCommand("reset", "🔄 Новый диалог"),
    ]
    await app.bot.set_my_commands(commands)

# Запуск
def main():
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(set_commands)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("workout", workout_cmd))
    app.add_handler(CommandHandler("food", food_cmd))
    app.add_handler(CommandHandler("motivate", motivate_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    print("Красивый бот запущен! ✅📸✨")
    app.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
