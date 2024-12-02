import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.ext import CommandHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)
test = [['Школьником в какой стране ты бы хотел быть?', ['Япония 1', 'Россия 2', 'США 3', 'Англия 4'], 'https://trikky.ru/wp-content/blogs.dir/1/files/2020/09/09/raznoe-flagi-gerby-raznocvetnyj-mnogo-535787.jpg'],
        ['Какое слово лучше всего описывает твою жизнь?', ['вайб 1', 'кринж 2', 'норм 3', 'хайп 4'], 'https://otvet.imgsmail.ru/download/u_36970c72a731157a35a3186261224124_800.jpg'],
        ['Что тебе не хватает для счастья?', ['любви 1', 'денег 2', 'приключений 3', 'все есть. 4'], 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTzAtC7rPgwFQ7CFzyOxDJWH0cGX8l5OeJcIg&usqp=CAU'],
        ['Какой у тебя темперамент?', ['холерик 3', 'сангвиник 1',
                               'флегматик 4', 'меланхолик 3'], 'https://avatars.dzeninfra.ru/get-zen_doc/8220767/pub_643946d0a7f3c1447c301c8b_6439b739b727dd713a164737/scale_1200'],
        ['Каким персонажем фильма вы бы были?', ['злодей 4', 'супергерой 1',
                                  'друг гг 3', 'второго плана 2'], 'https://avatars.dzeninfra.ru/get-zen_doc/271828/pub_65eacdc810c9542b72b6909a_65eb023e5851e30b8c894995/scale_1200']
        ]
ansewrs = {'5 6 7 8': ['Дети моря', 'https://avatars.mds.yandex.net/get-kinopoisk-image/1946459/83dc47d9-a58d-4592-9a41-f694a60beef8/600x900'],
           '9 10 11': ['Горько', 'https://avatars.mds.yandex.net/get-kinopoisk-image/4774061/8bb4add4-5830-4297-8457-bde488fe7a23/600x900'],
           '12': ['Отчаянные домохозяйки', 'https://www.kino-teatr.ru/movie/posters/big/8/9/18598.jpg'],
           '13': ['Субстанция', 'https://www.kino-teatr.ru/movie/posters/big/7/0/182607.jpg'],
           '14': ['Интерстеллар', 'https://cdn.ananasposter.ru/image/cache/catalog/poster/film/99/1463-1000x830.jpg'],
           '15 16': ['Леон', 'https://avatars.mds.yandex.net/get-kinopoisk-image/1704946/d869e2f5-4575-47db-9855-23b5066a4bf0/576x'],
           '17': ['Достать ножи', 'https://upload.wikimedia.org/wikipedia/ru/8/83/Knives_Out_%28film%29.jpg'],
           '18 19 20': ['11 друзей Оушена', 'https://img.mvideo.ru/Pdb/40060550b.jpg']}


async def echo(update, context):
    await update.message.reply_text('Приветствуем тебя, кинопутешественник! '
                                    '🍿🎬Хочешь узнать каким бы было твое воплощение в формате фильма? '
                                    'Тогда скорее жми на /play')


async def start(update, context):
    await update.message.reply_text('Приветствуем тебя, кинопутешественник! '
                                   '🍿🎬Хочешь узнать каким бы было твое воплощение в формате фильма? '
                                   'Тогда скорее жми на /play')


async def testik(update, context):
    context.user_data['test'] = test
    context.user_data['counter'] = 0
    keyboard = []
    for i in context.user_data['test'][0][1]:
        keyboard.append([InlineKeyboardButton(' '.join(i.split()[:-1]), callback_data=i)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = await context.bot.sendPhoto(chat_id=update.message.chat.id,
                                          photo=context.user_data['test'][0][2],
                                          caption=context.user_data['test'][0][0],
                                          reply_markup=reply_markup)
    context.user_data['message_id'] = message.message_id


async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if len(context.user_data['test']) > 1:
        context.user_data['counter'] += int(query.data.split()[-1])
        context.user_data['test'] = context.user_data['test'][1:]
        keyboard = []
        for i in context.user_data['test'][0][1]:
            keyboard.append([InlineKeyboardButton(' '.join(i.split()[:-1]), callback_data=i)])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.edit_message_media(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            media={
                "type": "photo",
                "media": context.user_data['test'][0][2],
            }
        )
        await context.bot.edit_message_caption(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            caption=context.user_data['test'][0][0],
            reply_markup=reply_markup
        )
    else:
        context.user_data['counter'] += int(query.data.split()[-1])
        for i in ansewrs.keys():
            if str(context.user_data['counter']) in i.split(' '):
                await query.message.delete()
                await context.bot.send_photo(
                    chat_id=query.message.chat.id,
                    photo=ansewrs[i][1],
                    caption=ansewrs[i][0]
                )
        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text='Приветствуем тебя, кинопутешественник! '
                 '🍿🎬Хочешь узнать каким бы было твое воплощение в формате фильма? '
                 'Тогда скорее жми на /play'
        )


def main():
    application = Application.builder().token('7400337270:AAETFmp98pQHbmjW7olfHZJYXmUkOBqiK2I').build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(catalog))
    application.add_handler(CommandHandler("play", testik))
    text_handler = MessageHandler(filters.TEXT, echo)
    application.add_handler(text_handler)
    application.run_polling()


if __name__ == '__main__':
    main()