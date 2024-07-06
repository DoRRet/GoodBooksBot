from wsgiref.util import application_uri
from telegram.ext import Application
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
from telegram.ext import filters

TOKEN = '7012177270:AAHVn0WARbchPLZO1lmg4ixPv0HltXIO-ME'


async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    await update.message.reply_text(
        f"Привет! Я бот канала 'Книги Books'. Если у вас есть вопросы или предложения, обратитесь к администратору. "
        f"\n\nАдминистратор: @admin_books"
    )
    # Создаем клавиатуру
    keyboard = [
        [
            InlineKeyboardButton("Предложка", callback_data='suggest'),
            InlineKeyboardButton("Позвать админа", callback_data='call_admin'),
        ],
        [
            InlineKeyboardButton("Поиск книги", callback_data='search_book'),
            InlineKeyboardButton("Анонимное предложение/жалоба", callback_data='anonymous_suggestion'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите нужную опцию:', reply_markup=reply_markup)

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'suggest':
        await query.edit_message_text("Вы выбрали 'Предложка'. Отправьте ваше предложение.")
        # Здесь можно обработать предложку

    elif query.data == 'call_admin':
        await query.edit_message_text("Администратор будет оповещен о вашем запросе.")
        # Здесь можно добавить логику для оповещения админа

    elif query.data == 'search_book':
        await query.edit_message_text("Вы выбрали 'Поиск книги'. Отправьте название книги для поиска.")
        # Здесь можно добавить логику для поиска книги

    elif query.data == 'anonymous_suggestion':
        await query.edit_message_text("Вы выбрали 'Анонимное предложение/жалоба'. "
                                      "Отправьте ваше предложение или жалобу анонимно.")
        # Здесь можно обработать анонимное предложение или жалобу

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))

    application.run_polling()

if __name__ == '__main__':
    main()