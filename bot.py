import telebot
from telebot import types
import json

BOT_TOKEN = '8322250527:AAGQWz8_KpbI9vnJ-5k1bb-Il3UGXduJAMk'

ADMIN_CHAT_ID = -5039455693

bot = telebot.TeleBot(BOT_TOKEN)

admin_reply_target = {}

def get_admin_mentions(chat_id):
    mentions = []
    try:
        admins = bot.get_chat_administrators(chat_id)
        for admin in admins:
            if admin.user.is_bot and admin.user.id == bot.get_me().id:
                continue
            
            if admin.user.username:
                mentions.append(f"@{admin.user.username}")
            else:
                mentions.append(f"<a href='tg://user?id={admin.user.id}'>{admin.user.first_name}</a>")
        
        if mentions:
            return " ".join(mentions) + "\n\n"
        else:
            return ""
            
    except telebot.apihelper.ApiTelegramException as e:
        print(f"Ошибка при получении администраторов чата {chat_id}: {e}")
        return "(Не удалось тегнуть админов)\n\n"
    except Exception as e:
        print(f"Неизвестная ошибка при получении администраторов чата {chat_id}: {e}")
        return "(Не удалось тегнуть админов)\n\n"


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Опишите свою проблему или заявку. Я перешлю её нашим администраторам.")

@bot.message_handler(func=lambda message: message.chat.id != ADMIN_CHAT_ID and message.text)
def handle_user_message(message):
    user_id = message.chat.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name if message.from_user.last_name else ''

    user_info_text = (
        f"<b>Новая заявка от пользователя:</b>\n"
        f"ID: <code>{user_id}</code>\n"
        f"Имя: {first_name} {last_name}\n"
    )
    if username:
        user_info_text += f"@{username}\n"
    else:
        user_info_text += "Нет username\n"
    user_info_text += f"Текст заявки:\n{message.text}"

    admin_mentions = get_admin_mentions(ADMIN_CHAT_ID)
    full_admin_message = admin_mentions + user_info_text

    markup = types.InlineKeyboardMarkup()
    callback_data = json.dumps({'action': 'reply_to_user', 'user_id': user_id})
    markup.add(types.InlineKeyboardButton("Ответить", callback_data=callback_data))

    bot.send_message(ADMIN_CHAT_ID, full_admin_message, reply_markup=markup, parse_mode='HTML')
    bot.reply_to(message, "Ваша заявка отправлена администраторам. Ожидайте ответа.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('{"action": "reply_to_user"'))
def handle_reply_callback(call):
    if call.message.chat.id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "Вы не администратор.")
        return

    data = json.loads(call.data)
    user_id_to_reply = data['user_id']

    admin_reply_target[call.message.chat.id] = user_id_to_reply

    bot.answer_callback_query(call.id, "Теперь напишите свой ответ.")
    bot.send_message(call.message.chat.id, f"Пишите ответ для пользователя с ID: <code>{user_id_to_reply}</code>. Следующее сообщение будет переслано этому пользователю.", parse_mode='HTML')

@bot.message_handler(func=lambda message: message.chat.id == ADMIN_CHAT_ID and message.chat.id in admin_reply_target)
def handle_admin_reply(message):
    target_user_id = admin_reply_target.pop(message.chat.id)

    try:
        bot.send_message(target_user_id, f"<b>Ответ администратора:</b>\n{message.text}", parse_mode='HTML')
        bot.reply_to(message, f"Ответ успешно отправлен пользователю с ID: <code>{target_user_id}</code>.", parse_mode='HTML')
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 403:
            bot.reply_to(message, f"Не удалось отправить ответ пользователю <code>{target_user_id}</code>. Возможно, бот заблокирован или чат удален.\nОшибка: {e.description}", parse_mode='HTML')
        else:
            bot.reply_to(message, f"Произошла ошибка Telegram API при отправке ответа пользователю <code>{target_user_id}</code>: {e}", parse_mode='HTML')
    except Exception as e:
        bot.reply_to(message, f"Произошла непредвиденная ошибка при отправке ответа пользователю <code>{target_user_id}</code>: {e}", parse_mode='HTML')


print("Бот запущен...")
bot.polling(none_stop=True)
