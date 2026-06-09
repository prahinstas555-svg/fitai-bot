# bot.py — FitAI Trainer 🤖💪📸 (+ Холодильник, Вода, Мотивация)
import json
import os
import random
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from groq import Groq
from apscheduler.schedulers.asyncio import AsyncIOScheduler

USERS_FILE = "users.json"
WATER_FILE = "water.json"  # 💧 файл для трекера воды

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_user(user_id):
    users = load_users()
    users.add(user_id)
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

# 💧 ФУНКЦИИ ДЛЯ ТРЕКЕРА ВОДЫ
def load_water():
    if os.path.exists(WATER_FILE):
        with open(WATER_FILE, "r") as f:
            return json.load(f)
    return {}

def save_water(data):
    with open(WATER_FILE, "w") as f:
        json.dump(data, f)

def get_today():
    return datetime.now().strftime("%Y-%m-%d")

def add_water(user_id, amount):
    """Добавляет воду юзеру за сегодня, возвращает сколько выпито"""
    data = load_water()
    uid = str(user_id)
    today = get_today()
    # если новый день или новый юзер — сбрасываем
    if uid not in data or data[uid].get("date") != today:
        data[uid] = {"date": today, "amount": 0}
    data[uid]["amount"] += amount
    save_water(data)
    return data[uid]["amount"]

def reset_water(user_id):
    data = load_water()
    uid = str(user_id)
    data[uid] = {"date": get_today(), "amount": 0}
    save_water(data)

def get_water(user_id):
    data = load_water()
    uid = str(user_id)
    today = get_today()
    if uid not in data or data[uid].get("date") != today:
        return 0
    return data[uid]["amount"]

WATER_NORM = 2000  # 💧 норма воды в мл (можно поменять)

# 🔑 КЛЮЧИ
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = (
    "Ты — FitAI, дружелюбный и мотивирующий ИИ фитнес-тренер. "
    "Ты помогаешь с тренировками, питанием и мотивацией. "
    "ВАЖНО: отвечай ВСЕГДА только на русском языке, "
    "не используй слова из других языков. "
    "Отвечай понятно, по делу, с эмодзи. "
    "Если вопрос про здоровье — советуй обратиться к врачу."
)

# 🔥 ФРАЗЫ ДЛЯ МОТИВАЦИИ (рассылка 2 раза в день)
MOTIVATION_PHRASES = [
    "🌅 Доброе утро! Сегодня отличный день стать лучше! 💪",
    "💧 Не забывай пить воду и записывать еду! Ты молодец!",
    "🔥 Маленький шаг сегодня = большой результат завтра!",
    "🏋️ Время размяться! Даже 10 минут зарядки заряжают на весь день!",
    "🥗 Помни: правильное питание — это забота о себе! 💚",
    "🚶 Прогулка на свежем воздухе творит чудеса. Выйди подышать!",
    "⭐ Ты уже на пути к цели. Не сдавайся — у тебя получается!",
    "🌆 Хороший вечер! Подведи итоги дня и похвали себя! 🙌",
]

# 📱 КНОПКИ-МЕНЮ
menu_keyboard = ReplyKeyboardMarkup(
    [
        ["🏋️ Тренировка", "🥗 Питание"],
        ["🔥 Мотивация", "📸 Калории по фото"],
        ["🧊 Что приготовить?", "💧 Вода"],
        ["🔄 Новый диалог"],
    ],
    resize_keyboard=True
)

# 💧 КНОПКИ ТРЕКЕРА ВОДЫ
water_keyboard = ReplyKeyboardMarkup(
    [
        ["➕ 250 мл", "➕ 500 мл"],
        ["♻️ Сбросить воду", "🔙 Назад в меню"],
    ],
    resize_keyboard=True
)

user_history = {}

# 🔧 РЕЖИМЫ юзера (чтобы знать, что он ждёт фото холодильника)
user_mode = {}

MY_ID = 1580782517

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    user_mode[user_id] = None

    welcome_text = (
        f"👋 Привет, *{user_name}*!\n\n"
        "💪 Я — *FitAI Trainer*, твой персональный\n"
        "ИИ фитнес-тренер. Вот что я умею:\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🏋️ *Тренировки* — программы под тебя\n"
        "🥗 *Питание* — советы и рецепты\n"
        "🔥 *Мотивация* — заряд энергии\n"
        "📸 *Калории по фото* — посчитаю КБЖУ\n"
        "🧊 *Что приготовить?* — сфоткай холодильник,\n"
        "      и я предложу рецепты из продуктов!\n"
        "💧 *Вода* — трекер воды на день\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "✨ _Выбери кнопку ниже или просто напиши мне!_"
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=menu_keyboard,
        parse_mode="Markdown"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    my_real_id = update.effective_user.id
    if my_real_id != MY_ID:
        await update.message.reply_text(
            f"⛔ Доступ запрещён.\n\n"
            f"Твой id: {my_real_id}\n"
            f"В коде MY_ID: {MY_ID}"
        )
        return
    users = load_users()
    await update.message.reply_text(
        f"📊 Статистика бота:\n\n"
        f"👥 Всего пользователей: {len(users)}"
    )

async def workout_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_message(update, "Предложи мне тренировку на сегодня")

async def food_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_message(update, "Дай совет по питанию на сегодня")

async def motivate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_message(update, "Замотивируй меня на тренировку!")

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    user_mode[user_id] = None
    await update.message.reply_text(
        "Начали заново! 🆕 О чём поговорим?",
        reply_markup=menu_keyboard
    )

# 💧 ПОКАЗАТЬ ТРЕКЕР ВОДЫ
async def show_water(update: Update):
    user_id = update.effective_user.id
    drunk = get_water(user_id)
    left = max(0, WATER_NORM - drunk)
    # рисуем прогресс-бар
    filled = int((drunk / WATER_NORM) * 10)
    filled = min(filled, 10)
    bar = "🟦" * filled + "⬜" * (10 - filled)

    if drunk >= WATER_NORM:
        status = "🎉 Норма выполнена! Молодец! 💪"
    else:
        status = f"💧 Осталось выпить: *{left} мл*"

    text = (
        "💧 *Трекер воды на сегодня*\n\n"
        f"Выпито: *{drunk} мл* / {WATER_NORM} мл\n"
        f"{bar}\n\n"
        f"{status}\n\n"
        "_Нажми кнопку, когда выпьешь воду!_ 👇"
    )
    await update.message.reply_text(
        text, reply_markup=water_keyboard, parse_mode="Markdown"
    )

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    # 🔘 Кнопки меню
    if user_text == "🔄 Новый диалог":
        await reset_cmd(update, context)
        return

    if user_text == "📸 Калории по фото":
        user_mode[user_id] = "food"
        await update.message.reply_text(
            "📸 Пришли мне фото своей еды 🍽️\n"
            "Я определю блюдо и посчитаю калории и БЖУ! 🔢",
            reply_markup=menu_keyboard
        )
        return

    # 🧊 ХОЛОДИЛЬНИК
    if user_text == "🧊 Что приготовить?":
        user_mode[user_id] = "fridge"
        await update.message.reply_text(
            "🧊 Сфоткай свой открытый холодильник\n"
            "или продукты на столе! 📸\n\n"
            "Я посмотрю, что у тебя есть, и предложу\n"
            "вкусные рецепты! 👨‍🍳",
            reply_markup=menu_keyboard
        )
        return

    # 💧 ВОДА
    if user_text == "💧 Вода":
        await show_water(update)
        return
    if user_text == "➕ 250 мл":
        add_water(user_id, 250)
        await show_water(update)
        return
    if user_text == "➕ 500 мл":
        add_water(user_id, 500)
        await show_water(update)
        return
    if user_text == "♻️ Сбросить воду":
        reset_water(user_id)
        await show_water(update)
        return
    if user_text == "🔙 Назад в меню":
        await update.message.reply_text(
            "Главное меню 👇", reply_markup=menu_keyboard
        )
        return

    if user_text == "🏋️ Тренировка":
        user_text = "Предложи мне тренировку на сегодня"
    elif user_text == "🥗 Питание":
        user_text = "Дай совет по питанию на сегодня"
    elif user_text == "🔥 Мотивация":
        user_text = "Замотивируй меня на тренировку!"

    await process_message(update, user_text)

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

    if len(user_history[user_id]) > 21:
        user_history[user_id] = (
            [user_history[user_id][0]] + user_history[user_id][-20:]
        )

    await update.message.reply_text(answer, reply_markup=menu_keyboard)

# 📸 Обработка ФОТО — еда ИЛИ холодильник
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mode = user_mode.get(user_id)

    await update.message.chat.send_action("typing")

    # 🧊 РЕЖИМ ХОЛОДИЛЬНИКА
    if mode == "fridge":
        await update.message.reply_text("Смотрю, что у тебя есть... 🧊👀")
        prompt_text = (
            "Посмотри на фото холодильника или продуктов. "
            "Перечисли продукты, которые видишь, и предложи 2-3 "
            "простых и полезных рецепта, которые можно из них приготовить. "
            "Отвечай ТОЛЬКО на русском языке, дружелюбно, с эмодзи. "
            "Формат:\n"
            "🧊 Вижу продукты: ...\n\n"
            "👨‍🍳 Рецепт 1: название\n"
            "   • что нужно\n"
            "   • как готовить (кратко)\n"
            "   🔢 примерные калории\n\n"
            "👨‍🍳 Рецепт 2: ...\n\n"
            "💡 Совет от тренера. "
            "Если на фото не продукты — мягко скажи об этом."
        )
    else:
        # 🍽️ РЕЖИМ ЕДЫ (калории) — по умолчанию
        await update.message.reply_text("Анализирую фото... 🔍🍽️")
        prompt_text = (
            "Определи, какое блюдо или продукты на фото. "
            "Посчитай примерные калории, белки, жиры и углеводы. "
            "Отвечай ТОЛЬКО на русском языке, дружелюбно, с эмодзи. "
            "Формат:\n"
            "🍽️ Что на фото\n"
            "🔢 Калории: ... ккал\n"
            "🥩 Белки / 🥑 Жиры / 🍚 Углеводы\n"
            "💡 Короткий совет от тренера. "
            "Если на фото не еда — скажи об этом."
        )

    photo = await update.message.photo[-1].get_file()
    photo_url = photo.file_path

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url",
                         "image_url": {"url": photo_url}},
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

    user_mode[user_id] = None  # сбрасываем режим после фото
    await update.message.reply_text(answer, reply_markup=menu_keyboard)

# 🔥 РАССЫЛКА МОТИВАЦИИ (2 раза в день)
async def send_motivation(app):
    users = load_users()
    phrase = random.choice(MOTIVATION_PHRASES)
    for uid in users:
        try:
            await app.bot.send_message(chat_id=uid, text=phrase)
        except Exception as e:
            print(f"Не отправилось {uid}: {e}")

async def set_commands(app):
    commands = [
        BotCommand("start", "🚀 Запустить бота"),
        BotCommand("workout", "🏋️ Тренировка на сегодня"),
        BotCommand("food", "🥗 Совет по питанию"),
        BotCommand("motivate", "🔥 Мотивация"),
        BotCommand("water", "💧 Трекер воды"),
        BotCommand("reset", "🔄 Новый диалог"),
    ]
    await app.bot.set_my_commands(commands)

# 💧 команда /water
async def water_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_water(update)

# ⏰ Настройка планировщика для мотивации
async def setup_scheduler(app):
    await set_commands(app)
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    # утром в 10:00 и вечером в 19:00
    scheduler.add_job(send_motivation, "cron", hour=10, minute=0, args=[app])
    scheduler.add_job(send_motivation, "cron", hour=19, minute=0, args=[app])
    scheduler.start()
    print("Планировщик мотивации запущен! ⏰🔥")

def main():
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(setup_scheduler)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("workout", workout_cmd))
    app.add_handler(CommandHandler("food", food_cmd))
    app.add_handler(CommandHandler("motivate", motivate_cmd))
    app.add_handler(CommandHandler("water", water_cmd))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    print("Бот запущен! ✅📸🧊💧⏰")
    app.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
