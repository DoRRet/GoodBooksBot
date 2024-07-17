from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

TOKEN = '6728896783:AAGZhYW1m7rbXOM4DPNJy8Z9pWigQlN30Uo'
ADMIN_CHAT_ID = 808174847
# 808174847 м
# 6984945831 т

async def forward_to_admin(update: Update, context: CallbackContext):
    user = update.message.from_user
    message = update.message

    info_message = (
        f"Сообщение от {user.first_name} {user.last_name} (@{user.username}):\n"
        f"ID пользователя: {user.id}\n"
        f"ID сообщения: {message.message_id}\n"
    )

    if message.text:
        info_message += f"Текст: {message.text}"
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=info_message)
    else:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=info_message)
        await context.bot.forward_message(chat_id=ADMIN_CHAT_ID, from_chat_id=message.chat_id, message_id=message.message_id)

    await update.message.reply_text(
        "Спасибо, мы обязательно присмотримся к Вашему предложению🤝❤️\n"
        "Если Вы хотите добавить еще позицию, то отправьте еще одно сообщение)\n"
        "Хорошего дня 😊"
    )

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        'Привет!) Мы рады, что у Вас есть предложение к нам!) Пришлите фото и название книги, '
        'а мы постараемся, чтобы она в скором времени поступила в продажу ❤️'
    )

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ALL, forward_to_admin))

    application.run_polling()

if __name__ == '__main__':
    main()