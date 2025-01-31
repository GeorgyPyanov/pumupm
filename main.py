import logging
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ConversationHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище данных
registered_players = {}  # {номер: username}
player_points = {}  # {username: points}
user_chat_ids = {}  # {username: chat_id}  <-- Добавлено для хранения chat_id игроков
safe_code = "0000"  # Код от сейфа
special_word = "секрет"  # Специальное слово

WAITING_FOR_NUMBER = 1
ADMIN_1 = "m0onstoun"
ADMIN_2 = "delacamomille"
ADMINS = [ADMIN_1, ADMIN_2]


async def register_number(update, context):
    """Регистрация нового номера (доступно только ADMIN_1)."""
    username = update.effective_user.username
    if username != ADMIN_1:
        await update.message.reply_text("У вас нет прав регистрировать номера.")
        return

    if not context.args:
        await update.message.reply_text("Используйте команду /register <номер>")
        return

    new_number = context.args[0]
    if new_number in registered_players:
        await update.message.reply_text("Этот номер уже зарегистрирован.")
    else:
        registered_players[new_number] = None
        await update.message.reply_text(f"Новый номер {new_number} зарегистрирован. Ожидается ввод игрока.")


async def start(update, context):
    """Приветствие пользователей и запрос номера."""
    username = update.effective_user.username
    chat_id = update.message.chat_id  # Получаем chat_id
    user_chat_ids[username] = chat_id  # Сохраняем chat_id пользователя

    if username == ADMIN_1:
        await update.message.reply_text("Приветствую, господин!")
        return
    elif username == ADMIN_2:
        await update.message.reply_text("Приветствую, госпожа!")
        return

    # Если пользователь уже зарегистрирован
    if username in player_points:
        await update.message.reply_text(f"Ваши очки: {player_points[username]}.")
    else:
        await update.message.reply_text("Введите ваш номер для регистрации")
        return WAITING_FOR_NUMBER


async def check_number(update, context):
    """Проверяет введенный номер и регистрирует пользователя."""
    username = update.effective_user.username
    player_number = update.message.text.strip()

    if player_number in registered_players:
        if registered_players[player_number] is None:
            registered_players[player_number] = username  # Связываем номер с пользователем
            player_points[username] = 0
            context.user_data['number'] = player_number  # Начинаем отсчет очков
            await update.message.reply_text(f"Добро пожаловать, {player_number}.")
        elif registered_players[player_number] == username:
            await update.message.reply_text(f"Ваш номер уже зарегистрирован. Ваши очки: {player_points[username]}.")
        else:
            await update.message.reply_text("Этот номер уже используется другим игроком.")
    else:
        await update.message.reply_text("Этот номер не зарегистрирован.")
    return ConversationHandler.END


async def add_point(update, context):
    """Добавляет очко игроку при вводе специального слова или номера игрока админом."""
    username = update.effective_user.username
    message_text = update.message.text.strip()

    # Если игрок вводит специальное слово — он получает очко
    if message_text.lower() == special_word:
        if username in player_points:
            player_points[username] += 1
            await update.message.reply_text(
                f"Вам добавлено 1 очко. Теперь у вас {player_points[username]}."
            )

            # Проверка на 3 очка
            if player_points[username] >= 3:
                await update.message.reply_text(f"Поздравляю, {context.user_data['number']}! Код от сейфа: {safe_code}")
        else:
            await update.message.reply_text("Вы еще не зарегистрированы. Введите ваш номер.")
        return

    # Если админ вводит номер — игрок получает очко
    if username in ADMINS and message_text in registered_players:
        target_username = registered_players[message_text]
        if target_username:
            player_points[target_username] = player_points.get(target_username, 0) + 1

            # Сообщение администратору
            await update.message.reply_text(
                f"{target_username} получил 1 очко! Теперь у него {player_points[target_username]}."
            )

            # Отправка сообщения игроку
            if target_username in user_chat_ids:
                target_chat_id = user_chat_ids[target_username]
                await context.bot.send_message(
                    chat_id=target_chat_id,
                    text=f"Вам добавлено 1 очко. Теперь у вас {player_points[target_username]}."
                )

                # Проверка на 3 очка
                if player_points[target_username] >= 3:
                    await context.bot.send_message(
                        chat_id=target_chat_id,
                        text=f"Поздравляю! Код от сейфа: {safe_code}. Торопись, он действует 5 минут."
                    )
        else:
            await update.message.reply_text("Этот номер зарегистрирован, но игрок еще не вошел в систему.")


async def change_safe_code(update, context):
    """Меняет код от сейфа (доступно только m0onstoun)."""
    global safe_code
    username = update.effective_user.username

    if username != "m0onstoun":
        await update.message.reply_text("У вас нет прав для изменения кода сейфа.")
        return

    if not context.args:
        await update.message.reply_text("Используйте команду /setcode <новый_код>")
        return

    safe_code = context.args[0]
    await update.message.reply_text(f"Новый код от сейфа установлен: {safe_code}")


def main():
    application = Application.builder().token("7580913605:AAFz1PVVEe9_HHxl7U-az4m1zyJMGnWiuT8").build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_number)],
        },
        fallbacks=[],
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("register", register_number))
    application.add_handler(CommandHandler("setcode", change_safe_code))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_point))
    application.run_polling()


if __name__ == '__main__':
    main()
