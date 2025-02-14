import os
import psycopg2
import random
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)

TOKEN = "7846671959:AAE9QJ3nFNWNrGXZInp6utnCugaYU1QhJpI"
ADMIN_USERNAME = "m0onstoun"

# Создание базы данных
DATABASE_URL = os.getenv("DATABASE_URL",
                         "postgresql://postgres:NeHOTwRTxSabYitdgNedblEXNsYvGLBi@postgres.railway.internal:5432/railway")

# Подключение к PostgreSQL
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY SERIAL,
    username TEXT UNIQUE,
    question TEXT,
    answer TEXT,
    message TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS greetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT UNIQUE
)
""")

# Добавляем стандартное поздравление (если нет)
cursor.execute("INSERT OR IGNORE INTO greetings (text) VALUES ('С днем любви!')")
conn.commit()

# Состояния для добавления валентинки
USERNAME, QUESTION, ANSWER, MESSAGE = range(4)


# === Функции ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие"""
    username = update.message.from_user.username
    cursor.execute("SELECT question FROM users WHERE username=?", (username,))
    user = cursor.fetchone()

    if user:
        await update.message.reply_text(f"Привет, {username}! Ответь на секретный вопрос:\n {user[0]}")
        return

    # Получаем список всех поздравлений и выбираем рандомное
    cursor.execute("SELECT text FROM greetings")
    greetings = cursor.fetchall()

    if greetings:
        greeting = random.choice(greetings)[0]
        await update.message.reply_text(greeting)
    else:
        await update.message.reply_text("С днем любви!")


async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.from_user.username
    answer = update.message.text.strip()

    cursor.execute("SELECT answer, message FROM users WHERE username=?", (username,))
    user = cursor.fetchone()

    if user and user[0].lower() == answer.lower():
        await update.message.reply_text(f"Лично в чатик! Как сказал Гоша:\n\n💌 {user[1]}")
        admin_chat_id = update.message.chat_id  # ID админа
        await context.bot.send_message(chat_id=admin_chat_id, text=f"💌 @{username} прочитал(а) свою валентинку!")
    elif user:
        await update.message.reply_text("Неправильно!")
    else:
        cursor.execute("SELECT text FROM greetings")
        greetings = cursor.fetchall()
        greeting = random.choice(greetings)[0] if greetings else "С днем любви!"
        await update.message.reply_text(greeting)


# === Добавление валентинки ===
async def add_valentine_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса добавления валентинки"""
    if update.message.from_user.username != ADMIN_USERNAME:
        return
    await update.message.reply_text("Введите username получателя:")
    return USERNAME


async def add_valentine_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос секретного вопроса"""
    context.user_data["username"] = update.message.text.strip()
    await update.message.reply_text("Введите секретный вопрос:")
    return QUESTION


async def add_valentine_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос ответа на секретный вопрос"""
    context.user_data["question"] = update.message.text.strip()
    await update.message.reply_text("Введите ответ на секретный вопрос:")
    return ANSWER


async def add_valentine_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос текста валентинки"""
    context.user_data["answer"] = update.message.text.strip()
    await update.message.reply_text("Введите текст валентинки:")
    return MESSAGE


async def add_valentine_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Финальный этап — сохранение в БД"""
    context.user_data["message"] = update.message.text.strip()

    username = context.user_data["username"]
    question = context.user_data["question"]
    answer = context.user_data["answer"]
    message = context.user_data["message"]

    cursor.execute("INSERT INTO users (username, question, answer, message) VALUES (%s, %s, %s, %s)",
                   (username, question, answer, message))
    conn.commit()

    await update.message.reply_text(f"✅ Валентинка для @{username} добавлена!")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена ввода"""
    await update.message.reply_text("🚫 Добавление отменено.")
    return ConversationHandler.END


# === Управление поздравлениями ===
async def add_greeting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавляет новое поздравление"""
    if update.message.from_user.username != ADMIN_USERNAME:
        return
    greeting = " ".join(context.args)

    if greeting:
        try:
            cursor.execute("INSERT INTO greetings (text) VALUES (%s)", (greeting,))
            conn.commit()
            await update.message.reply_text(f"✅ Добавлено новое поздравление:\n{greeting}")
        except sqlite3.IntegrityError:
            await update.message.reply_text("⚠ Такое поздравление уже есть в базе!")
    else:
        await update.message.reply_text("⚠ Используйте формат:\n/add_greeting текст")


async def remove_greeting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет конкретное поздравление"""
    if update.message.from_user.username != ADMIN_USERNAME:
        return
    greeting = " ".join(context.args)

    cursor.execute("DELETE FROM greetings WHERE text=?", (greeting,))
    conn.commit()

    if cursor.rowcount:
        await update.message.reply_text(f"✅ Поздравление удалено:\n{greeting}")
    else:
        await update.message.reply_text("⚠ Такого поздравления нет в базе!")


async def list_greetings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выводит список всех поздравлений"""
    if update.message.from_user.username != ADMIN_USERNAME:
        return

    cursor.execute("SELECT text FROM greetings")
    greetings = cursor.fetchall()

    if greetings:
        text = "\n".join([f"🔹 {g[0]}" for g in greetings])
        await update.message.reply_text(f"📜 Список поздравлений:\n{text}")
    else:
        await update.message.reply_text("❌ В базе пока нет поздравлений.")


# === Команды для админа ===
async def remove_valentine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет пользователя (для m0onstoun)"""
    if update.message.from_user.username != ADMIN_USERNAME:
        return
    try:
        username = context.args[0]
        cursor.execute("DELETE FROM users WHERE username=%s", (username,))
        conn.commit()
        await update.message.reply_text(f"✅ Валентинка для @{username} удалена!")
    except:
        await update.message.reply_text("⚠ Ошибка! Используйте формат:\n/remove_valentine username")


async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает всех зарегистрированных пользователей"""
    if update.message.from_user.username != ADMIN_USERNAME:
        return
    cursor.execute("SELECT username FROM users")
    users = cursor.fetchall()

    if users:
        user_list = "\n".join([f"🔹 @{u[0]}" for u in users])
        await update.message.reply_text(f"📜 Список пользователей:\n{user_list}")
    else:
        await update.message.reply_text("❌ Пока нет зарегистрированных пользователей.")


# === Запуск Бота ===
def main():
    app = Application.builder().token(TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add_valentine", add_valentine_start)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_valentine_username)],
            QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_valentine_question)],
            ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_valentine_answer)],
            MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_valentine_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("add_greeting", add_greeting))
    app.add_handler(CommandHandler("remove_greeting", remove_greeting))
    app.add_handler(CommandHandler("list_greetings", list_greetings))
    app.add_handler(CommandHandler("remove_valentine", remove_valentine))
    app.add_handler(CommandHandler("list_users", list_users))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer))
    print("🚀 Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()