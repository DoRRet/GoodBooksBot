import asyncio
from telegram import Bot

TOKEN = '7012177270:AAHVn0WARbchPLZO1lmg4ixPv0HltXIO-ME'
ADMIN_CHAT_ID = 6984945831

async def test_send_message():
    bot = Bot(token=TOKEN)
    try:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text="Тестовое сообщение от бота.")
        print("Сообщение успешно отправлено администратору.")
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")

if __name__ == '__main__':
    asyncio.run(test_send_message())