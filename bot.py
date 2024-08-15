import json
import os
import sqlite3
import telegram
import random
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, filters

load_dotenv()
TOKEN = os.getenv('TOKEN')
ADMIN_CHAT_ID = 6984945831
SEARCH_BOOK = "SEARCH_BOOK"
# 808174847 м
# 6984945831 т


HISTORY_FILE = 'message_history.json'
ANON_FILE = 'anonymous_messages.json'
USER_STATUS_FILE = 'user_status.json'

def load_message_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as file:
                loaded_history = json.load(file)
                return {int(key): value for key, value in loaded_history.items()}
        else:
            print(f"Файл {HISTORY_FILE} не найден.")
            return {}
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON в файле {HISTORY_FILE}: {e}")
        return {}

def save_message_history():
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as file:
            json.dump({str(key): value for key, value in message_history.items()}, file, ensure_ascii=False, indent=4)
        print("История сообщений сохранена.")
    except IOError as e:
        print(f"Ошибка при записи файла {HISTORY_FILE}: {e}")

def load_anonymous_messages():
    try:
        if os.path.exists(ANON_FILE):
            with open(ANON_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        else:
            print(f"Файл {ANON_FILE} не найден.")
            return []
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON в файле {ANON_FILE}: {e}")
        return []

def save_anonymous_messages():
    try:
        with open(ANON_FILE, 'w', encoding='utf-8') as file:
            json.dump(anonymous_messages, file, ensure_ascii=False, indent=4)
        print("Анонимные сообщения сохранены.")
    except IOError as e:
        print(f"Ошибка при записи файла {ANON_FILE}: {e}")

def load_user_status():
    default_status = {"active_users": [], "inactive_users": []}
    if not os.path.exists(USER_STATUS_FILE):
        return default_status

    try:
        with open(USER_STATUS_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
            active_users = [user for user in data.get("active_users", []) if user != ADMIN_CHAT_ID]
            inactive_users = data.get("inactive_users", [])
            return {
                "active_users": active_users,
                "inactive_users": inactive_users,
            }
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error reading {USER_STATUS_FILE}: {e}")
        return default_status

def save_user_status(active_users, inactive_users):
    try:
        with open(USER_STATUS_FILE, 'w', encoding='utf-8') as file:
            json.dump({"active_users": active_users, "inactive_users": inactive_users}, file, ensure_ascii=False, indent=4)
        print("Статус пользователей сохранен.")
    except IOError as e:
        print(f"Ошибка при записи файла {USER_STATUS_FILE}: {e}")

user_status = load_user_status()

user_admin_chat = {}
active_dialogs = {}
message_history = load_message_history()
anonymous_messages = load_anonymous_messages()
book_titles = {}
is_recording_user = {}
is_recording_admin = False
is_admin_reply_mode = False


async def start(update, context):
    user = update.effective_user

    context.user_data.pop('awaiting_reply_user_id', None)
    global is_recording_admin, is_admin_reply_mode
    is_recording_admin = False
    is_admin_reply_mode = False

    await send_welcome_message(update, context, user)

    if not context.user_data.get('initialized'):
        context.user_data['initialized'] = True

    if user.id == ADMIN_CHAT_ID:
        await show_admin_menu(update, context)
    else:
        await show_main_menu(update, context)


async def send_welcome_message(update, context, user):
    welcome_text = (
        f"Привет! Я бот канала 'Good Books'.\n\n"
        f"Если у вас есть вопросы или предложения, обратитесь к администратору.\n"
        f"Администратор: @biblioteka_gb 💌"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text)


async def show_main_menu(update: Update, context: CallbackContext):
    buttons = [
        ["📚 Предложка"],
        ["🔍 Поиск книги"],
        ["👋 Позвать администратора"],
        ["✍️ Анонимное предложение/жалоба"],
        ["😹 Мемчик"]
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    await update.message.reply_text("Главное меню", reply_markup=reply_markup)

SEARCH_BOOK = "SEARCH_BOOK"


async def handle_message(update: Update, context: CallbackContext):
    user = update.message.from_user
    message = update.message
    text = message.text if message.text else ""
    global user_status, is_admin_reply_mode

    if context.user_data.get('ignore_next_message'):
        context.user_data['ignore_next_message'] = False
        return

    buttons = [
        ["Назад ⬅️"]
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    if text.lower() == "назад ⬅️" or text.lower() == "/start":
        context.user_data['awaiting_suggestion'] = False
        context.user_data['awaiting_search_query'] = False
        context.user_data['awaiting_admin_message'] = False
        context.user_data['awaiting_anonymous_suggestion'] = False
        context.user_data.pop('awaiting_reply_user_id', None)

        if user.id == ADMIN_CHAT_ID:
            is_admin_reply_mode = False
            await show_admin_menu(update, context)
        else:
            await show_main_menu(update, context)
        return

    if text.lower() == "😹 мемчик":
        await send_random_meme(update, context)
        return

    if text.lower() == "меню пользователей":
        if user.id == ADMIN_CHAT_ID:
            await show_main_menu(update, context)
        return

    if text.lower() == "🔍 поиск книги":
        context.user_data['awaiting_search_query'] = True
        await update.message.reply_text("Введите название книги для поиска:", reply_markup=reply_markup)
        return

    if context.user_data.get('awaiting_search_query'):
        await handle_search_query(update, context, text)
        return

    if text.lower() == "показать активные диалоги" and user.id == ADMIN_CHAT_ID:
        await show_active_dialogs(update, context)
        return

    if text.lower() == "👋 позвать администратора":
        context.user_data['awaiting_admin_message'] = True
        await update.message.reply_text("Напишите сообщение администратору, скоро он Вам ответит⚡️", reply_markup=reply_markup)
        return

    if context.user_data.get('awaiting_admin_message'):
        context.user_data['awaiting_admin_message'] = False
        if user.id not in user_status['active_users']:
            user_status['active_users'].append(user.id)
        if user.id in user_status['inactive_users']:
            user_status['inactive_users'].remove(user.id)
        save_user_status(user_status['active_users'], user_status['inactive_users'])

        # Save user message history
        if user.id not in message_history:
            message_history[user.id] = []
        message_history[user.id].append({
            "from": "user",
            "text": text,
            "timestamp": update.message.date.isoformat()
        })
        save_message_history()

        # Save admin message history
        if ADMIN_CHAT_ID not in message_history:
            message_history[ADMIN_CHAT_ID] = []
        message_history[ADMIN_CHAT_ID].append({
            "from": "user",
            "text": text,
            "timestamp": update.message.date.isoformat()
        })
        save_message_history()

        admin_message = f"Сообщение от пользователя @{user.username} (ID: {user.id}):\n{text}"
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
        await update.message.reply_text("Ваше сообщение отправлено администратору. Он скоро свяжется с вами.", reply_markup=reply_markup)
        return

    if text.lower() == "📚 предложка":
        context.user_data['awaiting_suggestion'] = True
        await update.message.reply_text("Мы рады, что у Вас есть предложение к нам!) Пришлите фото и название книги, а мы постараемся, чтобы она в скором времени поступила в продажу ❤️", reply_markup=reply_markup)
        return

    if context.user_data.get('awaiting_suggestion'):
        context.user_data['awaiting_suggestion'] = False

        info_message = (
            f"Предложение от @{user.username}:\n"
            f"ID пользователя: {user.id}\n"
            #f"ID сообщения: {message.message_id}\n"
        )

        if message.text:
            info_message += f"Текст: {message.text}"
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=info_message)
        else:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=info_message)
            await context.bot.forward_message(chat_id=ADMIN_CHAT_ID, from_chat_id=message.chat_id, message_id=message.message_id)

        await update.message.reply_text(
            "Спасибо, мы обязательно присмотримся к Вашему предложению🤝❤️\n"
            "Если Вы хотите добавить еще позицию, нажмите на 'Предложка' заново и отправьте сообщение)\n"
            "Хорошего дня 😊",
            reply_markup=reply_markup
        )
        return

    if text.lower() == "✍️ анонимное предложение/жалоба":
        context.user_data['awaiting_anonymous_suggestion'] = True
        await update.message.reply_text("Отправьте ваше предложение или жалобу. Сообщение будет анонимным", reply_markup=reply_markup)
        return

    if context.user_data.get('awaiting_anonymous_suggestion'):
        context.user_data['awaiting_anonymous_suggestion'] = False
        anonymous_message = update.message.text
        anonymous_messages.append(anonymous_message)
        save_anonymous_messages()
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"Анонимное предложение/жалоба:\n{anonymous_message}"
        )
        await update.message.reply_text("Ваше сообщение отправлено✅")
        return

    if user.id in active_dialogs and active_dialogs[user.id] == SEARCH_BOOK:
        await handle_search_query(update, context, text)
        return

    if user.id == ADMIN_CHAT_ID:
        await handle_admin_message(update, context)
        return

    await update.message.reply_text("Неизвестная команда⚠️ Пожалуйста, используйте меню для навигации.", reply_markup=reply_markup)




async def handle_search_query(update: Update, context: CallbackContext, query: str):
    books = search_books(query)

    buttons = [
        [InlineKeyboardButton(book['title'], callback_data=f"select_book_{book['id']}")] for book in books
    ]

    if books:
        reply_markup = InlineKeyboardMarkup(buttons)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Найденные книги (только название и цена):",
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Книги не найдены. Введите название книги для нового поиска."
        )

async def show_book_details(update: Update, context: CallbackContext, book_id: int):
    book = get_book_by_id(book_id)

    if book:
        buttons = [
            [InlineKeyboardButton("Купить на Авито", callback_data=f"buy_avito_{book['id']}")],
            [InlineKeyboardButton("Купить на Озон", callback_data=f"buy_ozon_{book['id']}")],
            [InlineKeyboardButton("Купить на Вайлдберриз", callback_data=f"buy_wb_{book['id']}")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

        if book["image_url"]:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=book["image_url"],
                caption=f"📚 {book['title']}\n💰 Цена: {book['price']}\n📦 Наличие: {book['availability']}",
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"📚 {book['title']}\n💰 Цена: {book['price']}\n📦 Наличие: {book['availability']}\n(Фото отсутствует)",
                reply_markup=reply_markup
            )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Информация о книге не найдена."
        )

async def button_click_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    data = query.data

    if data.startswith("select_book_"):
        book_id = int(data.split('_')[2])
        await show_book_details(update, context, book_id)
        await query.answer()

    elif data.startswith("buy_"):
        platform, book_id = data.split('_')[1:3]
        platform_name = {
            "avito": "Авито",
            "ozon": "Озон",
            "wb": "Вайлдберриз"
        }[platform]

        # Получаем полное название книги из словаря
        book_title = book_titles.get(int(book_id), "неизвестная книга")

        # Запись в историю сообщений
        if user.id not in message_history:
            message_history[user.id] = []
        message_history[user.id].append({
            "from": user.id,
            "text": f"Просит ссылку на книгу '{book_title}' на платформе {platform_name}",
            "timestamp": update.callback_query.message.date.isoformat()
        })
        save_message_history()

        # Отметка пользователя как активного
        if user.id not in user_status['active_users']:
            user_status['active_users'].append(user.id)
        if user.id in user_status['inactive_users']:
            user_status['inactive_users'].remove(user.id)
        save_user_status(user_status['active_users'], user_status['inactive_users'])

        # Уведомление администратора
        admin_message = f"Пользователь @{user.username} (ID: {user.id}) выбрал покупку книги '{book_title}' на {platform_name}."
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)

        # Ответ пользователю
        user_message = f"Вы выбрали покупку на {platform_name}. Администратор уведомлен и скоро пришлет ссылку."
        await context.bot.send_message(chat_id=user.id, text=user_message)

        # Закрытие уведомления
        await query.answer()



async def handle_admin_message(update: Update, context: CallbackContext):
    global is_admin_reply_mode
    user = update.message.from_user
    text = update.message.text

    if user.id == ADMIN_CHAT_ID:
        if text.lower() == "назад ⬅️" or text == "/start":
            is_admin_reply_mode = False
            context.user_data.pop('awaiting_reply_user_id', None)
            await update.message.reply_text("Режим ответа отключен.", reply_markup=ReplyKeyboardMarkup([["Меню администратора"]], resize_keyboard=True))
            await show_admin_menu(update, context)
            return

        if text.lower() == "закрыть диалог":
            if 'awaiting_reply_user_id' in context.user_data:
                user_id = context.user_data['awaiting_reply_user_id']
                await close_dialog_command(update, context, user_id)
                is_admin_reply_mode = False
                context.user_data.pop('awaiting_reply_user_id', None)
            else:
                await update.message.reply_text("Нет активного диалога для закрытия.")
            return

        if text.lower().startswith("/closedia"):
            parts = text.split()
            if len(parts) == 2:
                await close_dialog_command(update, context, parts[1])
            else:
                await update.message.reply_text("Неправильный формат команды. Используйте: /closedia <user_id>")
            return

        if is_admin_reply_mode:
            if 'awaiting_reply_user_id' in context.user_data:
                user_id = context.user_data['awaiting_reply_user_id']

                try:
                    user_id = int(user_id)

                    # Отправка сообщения пользователю
                    await context.bot.send_message(chat_id=user_id, text=f"Ответ от администратора:\n{text}")
                    await update.message.reply_text(f"Сообщение отправлено пользователю {user_id}.")

                    # Обновляем статус пользователя на активный
                    if user_id not in user_status['active_users']:
                        user_status['active_users'].append(user_id)
                    if user_id in user_status['inactive_users']:
                        user_status['inactive_users'].remove(user_id)
                    save_user_status(user_status['active_users'], user_status['inactive_users'])

                    # Сохраняем сообщение в историю
                    if user_id not in message_history:
                        message_history[user_id] = []
                    message_history[user_id].append({
                        "from": "admin",
                        "text": text,
                        "timestamp": update.message.date.isoformat()
                    })
                    save_message_history()

                except Exception as e:
                    await update.message.reply_text(f"Ошибка при отправке сообщения: {e}")

            return

        if text.startswith('/reply'):
            parts = text.split(' ', 2)
            if len(parts) < 3:
                await update.message.reply_text("Неправильный формат команды. Используйте: /reply <user_id> <сообщение>")
                return
            user_id = parts[1]
            reply_message = parts[2]

            try:
                user_id = int(user_id)

                # Отправка сообщения пользователю
                await context.bot.send_message(chat_id=user_id, text=f"Ответ от администратора:\n{reply_message}")
                await update.message.reply_text(f"Сообщение отправлено пользователю {user_id}.")

                # Обновляем статус пользователя на активный
                if user_id not in user_status['active_users']:
                    user_status['active_users'].append(user_id)
                if user_id in user_status['inactive_users']:
                    user_status['inactive_users'].remove(user_id)
                save_user_status(user_status['active_users'], user_status['inactive_users'])

                # Сохраняем сообщение в историю
                if user_id not in message_history:
                    message_history[user_id] = []
                message_history[user_id].append({
                    "from": "admin",
                    "text": reply_message,
                    "timestamp": update.message.date.isoformat()
                })
                save_message_history()

            except Exception as e:
                await update.message.reply_text(f"Ошибка при отправке сообщения: {e}")
            return

    await update.message.reply_text("Неправильный формат команды. Используйте: /reply <user_id> <сообщение>")


async def notify_admin(update: Update, context: CallbackContext):
    user = update.callback_query.from_user
    admin_message = (
        f"Пользователь @{user.username} ({user.id}) хочет связаться с администратором.\n"
        f"Имя пользователя: {user.first_name} {user.last_name or ''}"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
    user_admin_chat[user.id] = ADMIN_CHAT_ID
    active_dialogs[user.id] = True

async def send_random_meme(update: Update, context: CallbackContext):
    meme_folder = '/root/GoodBooksBot/memes'
    meme_files = os.listdir(meme_folder)
    meme_file = random.choice(meme_files)
    meme_path = os.path.join(meme_folder, meme_file)

    if meme_file.endswith(".jpg") or meme_file.endswith(".png"):
        with open(meme_path, 'rb') as photo:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo)
    elif meme_file.endswith(".gif"):
        with open(meme_path, 'rb') as gif:
            await context.bot.send_animation(chat_id=update.effective_chat.id, animation=gif)
    elif meme_file.endswith(".mp4"):
        with open(meme_path, 'rb') as video:
            await context.bot.send_video(chat_id=update.effective_chat.id, video=video)


async def show_help(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Админ любит книги и Вас🥰")
        return

    help_message = (
        "Команды для администратора:\n"
        "/start - Запустить бота\n"
        "/help - Показать сообщение с командами\n"
        "/users - Показать всех пользователей\n"
        "/history <user_id> - Показать историю сообщений с пользователем\n"
        "/closedia <user_id> - Закрыть диалог с пользователем\n"
        "/clearchat <user_id> - Очистить историю сообщений с пользователем\n"
        "/anon - Показать анонимные сообщения\n"
        "/clearanonall - Очистить все анонимные сообщения\n"
        "/clearanon <номер> - Удалить одно анонимное сообщение по номеру\n"
    )
    await update.message.reply_text(help_message)

async def show_admin_menu(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    buttons = [
        ["Показать активные диалоги"],
        ["Меню пользователей"]
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    await update.message.reply_text("Меню администратора:", reply_markup=reply_markup)

async def close_dialog_command(update: Update, context: CallbackContext, user_id: str):
    global user_status

    try:
        target_user_id = int(user_id)
        if target_user_id in user_status['active_users']:
            user_status['active_users'].remove(target_user_id)
            user_status['inactive_users'].append(target_user_id)
            save_user_status(user_status['active_users'], user_status['inactive_users'])
            await update.message.reply_text(f"Диалог с пользователем {target_user_id} закрыт.")
        else:
            await update.message.reply_text("Этот диалог уже закрыт или не существует.")
    except ValueError:
        await update.message.reply_text("Пожалуйста, укажите корректный ID пользователя.")

async def close_dialog(update: Update, context: CallbackContext):
    user = update.message.from_user
    if user.id == ADMIN_CHAT_ID:
        await close_dialog_command(update, context, context.args[0])
    else:
        await update.message.reply_text("Эта команда доступна только для администратора.")

async def show_users(update: Update, context: CallbackContext):
    global user_status

    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    active_users_message = "Активные пользователи:\n"
    inactive_users_message = "Неактивные пользователи:\n"

    user_status = load_user_status()

    for user_id in user_status['active_users']:
        user_info = await context.bot.get_chat(user_id)
        username = f"@{user_info.username}" if user_info.username else user_info.first_name
        active_users_message += f"ID: {user_id}, Username: {username}\n"

    for user_id in user_status['inactive_users']:
        user_info = await context.bot.get_chat(user_id)
        username = f"@{user_info.username}" if user_info.username else user_info.first_name
        inactive_users_message += f"ID: {user_id}, Username: {username}\n"

    users_message = active_users_message + "\n" + "*"*10 + "\n" + inactive_users_message
    await update.message.reply_text(users_message)

async def show_user_history(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return
    try:
        user_id = int(context.args[0])
        if user_id in message_history:
            history = message_history[user_id]
            user_info = await context.bot.get_chat(user_id)
            username = f"@{user_info.username}" if user_info.username else ""
            history_message = f"История сообщений с пользователем {user_id} ({username}):\n"
            for message in history:
                sender = "Админ" if message['from'] == 'admin' else "Пользователь"
                history_message += f"{sender}: {message['text']}\n"
            await update.message.reply_text(history_message)
        else:
            await update.message.reply_text("История сообщений с этим пользователем пуста.")
    except (IndexError, ValueError):
        await update.message.reply_text("Пожалуйста, укажите корректный ID пользователя.")

async def show_active_dialogs(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    user_status = load_user_status()
    active_users = user_status['active_users']

    if not active_users:
        await update.message.reply_text("Нет активных диалогов.")
        return

    messages = []
    buttons = []
    for user_id in active_users:
        last_message = message_history.get(user_id, [])
        if last_message:
            last_message = last_message[-1]
            last_text = last_message.get("text", "No text")
            last_time = last_message.get("timestamp", "No timestamp")
            if last_message.get("from") == "admin":
                messages.append(f"✅  Пользователь ID: {user_id}\nПоследнее сообщение от администратора: {last_text}\nВремя: {last_time}\n")
            else:
                messages.append(f"🆘  Пользователь ID: {user_id}\nПоследнее сообщение от пользователя: {last_text}\nВремя: {last_time}\n")
            buttons.append([InlineKeyboardButton(f"Ответить {user_id}", callback_data=f"reply_{user_id}")])
        else:
            messages.append(f"Пользователь ID: {user_id}\nНет сообщений.\n")
            buttons.append([InlineKeyboardButton(f"Ответить {user_id}", callback_data=f"reply_{user_id}")])

    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_html("<b>Активные диалоги:</b>\n\n" + "\n".join(messages), reply_markup=reply_markup)

async def handle_reply_callback(update: Update, context: CallbackContext):
    global is_admin_reply_mode
    query = update.callback_query
    await query.answer()

    user_id = query.data.split('_')[1]
    context.user_data['awaiting_reply_user_id'] = user_id
    is_admin_reply_mode = True

    buttons = [
        ["Назад ⬅️", "Закрыть диалог"]
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    await query.edit_message_text(text=f"Введите сообщение для пользователя {user_id}:")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Режим ответа. Нажмите 'Назад ⬅️' для выхода.", reply_markup=reply_markup)


async def clearchat(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Вы не имеете прав для выполнения этой команды.")
        return

    args = context.args
    if len(args) != 1:
        await update.message.reply_text("Использование: /clearchat <user_id>")
        return

    try:
        user_id = int(args[0])
        if user_id in message_history:
            del message_history[user_id]
            save_message_history()
            await update.message.reply_text(f"История сообщений пользователя {user_id} удалена.")
        else:
            await update.message.reply_text(f"История сообщений пользователя {user_id} не найдена.")
    except ValueError:
        await update.message.reply_text("user_id должен быть числовым значением.")


async def show_anonymous_messages(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    if anonymous_messages:
        anon_messages = "\n\n".join([f"{index + 1}. {msg}" for index, msg in enumerate(anonymous_messages)])
        await update.message.reply_text(f"Анонимные сообщения:\n{anon_messages}")
    else:
        await update.message.reply_text("Анонимных сообщений нет.")

async def clear_anonymous_messages(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    anonymous_messages.clear()
    save_anonymous_messages()
    await update.message.reply_text("Все анонимные сообщения очищены.")

async def clear_one_anonymous_message(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Эта команда доступна только для администратора.")
        return

    try:
        message_index = int(context.args[0]) - 1
        if 0 <= message_index < len(anonymous_messages):
            del anonymous_messages[message_index]
            save_anonymous_messages()
            await update.message.reply_text(f"Сообщение номер {message_index + 1} удалено.")
        else:
            await update.message.reply_text("Неверный номер сообщения.")
    except (IndexError, ValueError):
        await update.message.reply_text("Пожалуйста, укажите корректный номер сообщения.")



SEARCH_BOOK = 1
def search_books(query):
    global book_titles
    try:
        conn = sqlite3.connect('books.db')
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, price, image_url, availability
            FROM Book
        """)

        rows = cursor.fetchall()
        books = [
            {
                "id": row[0],
                "title": row[1],
                "price": row[2],
                "image_url": row[3],
                "availability": row[4]
            }
            for row in rows
        ]

        query_lower = query.lower()
        filtered_books = [
            book for book in books
            if query_lower in book['title'].lower()
        ]

        # Сохраняем названия книг в глобальный словарь book_titles
        for book in books:
            book_titles[book['id']] = book['title']

        conn.close()
        return filtered_books

    except Exception as e:
        print(f"Произошла ошибка при выполнении поиска: {e}")
        return []

def get_book_by_id(book_id):
    try:
        conn = sqlite3.connect('books.db')
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, title, price, image_url, availability
            FROM Book
            WHERE id = ?
        """, (book_id,))

        row = cursor.fetchone()
        if row:
            book = {
                "id": row[0],
                "title": row[1],
                "price": row[2],
                "image_url": row[3],
                "availability": row[4]
            }
            conn.close()
            return book
        else:
            conn.close()
            return None

    except Exception as e:
        print(f"Произошла ошибка при получении информации о книге: {e}")
        return None

def main():
    global message_history, active_dialogs
    load_message_history()
    load_anonymous_messages()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", show_help))
    application.add_handler(CommandHandler("users", show_users))
    application.add_handler(CommandHandler("history", show_user_history))
    application.add_handler(CommandHandler("closedia", close_dialog))
    application.add_handler(CommandHandler("clearchat", clearchat))
    application.add_handler(CommandHandler("anon", show_anonymous_messages))
    application.add_handler(CommandHandler("clearanonall", clear_anonymous_messages))
    application.add_handler(CommandHandler("clearanon", clear_one_anonymous_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_reply_callback, pattern=r"^reply_"))
    application.add_handler(CallbackQueryHandler(button_click_handler))
    application.add_handler(CallbackQueryHandler(show_book_details, pattern=r"^show_"))

    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & filters.User(ADMIN_CHAT_ID),
        handle_admin_message
    ))

    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.User(ADMIN_CHAT_ID),
        handle_message
    ))

    application.add_handler(MessageHandler(
        filters.PHOTO & filters.ChatType.PRIVATE,
        handle_message
    ))

    application.add_handler(MessageHandler(
        filters.VIDEO & filters.ChatType.PRIVATE,
        handle_message
    ))

    application.add_handler(MessageHandler(
        filters.ANIMATION & filters.ChatType.PRIVATE,
        handle_message
    ))

    application.run_polling()

if __name__ == '__main__':
    main()