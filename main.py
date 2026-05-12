import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

with open('token.txt', 'r') as f:
    token = f.read()


bot=telebot.TeleBot(token)

correct_answers = ["26", "xzy", "801", "14", "19", "17", "10", "270", "3094", "64", "94", "28", "192", "3", "23", "120", "180 190360573", "1911 178", "43", "2324324445", "25", "17", "13", "1004", "101075762 101417282 101588258 101645282", "568 50", "471228 49113954961677"]

user_states = {}

@bot.message_handler(commands=['start'])
def send_main_menu_options(message):
    user_id = message.from_user.id
    user_states[user_id] = {
        "stage": "Menu",
        "current_task_number" : None
    }

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="Начать пробный экзамен",
        callback_data="btn_start_exam"))
    markup.add(InlineKeyboardButton(text="Моя статистика",
        callback_data="btn_statistics"))

    bot.send_message(chat_id=user_id, text = "Выберите пункт меню:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "btn_start_exam")
def send_task_buttons(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)

    markup = InlineKeyboardMarkup()
    buttons = []
    for i in range(1, 28):
        buttons.append(InlineKeyboardButton(text=str(i), callback_data="task_" + str(i)))
        if i % 8 == 0:
            markup.row(*buttons)
            buttons = []

    if buttons:
        markup.row(*buttons)

    bot.send_message(chat_id=user_id, reply_markup=markup, text = "Выберите задание:")

@bot.callback_query_handler(func=lambda call: call.data.startswith("task_"))
def send_task(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    task_number = int(call.data.split("_")[1])
    user_states[user_id]["current_task_number"] = task_number
    user_states[user_id]["stage"] = "task"
    path_to_task_image = "tasks/" + str(task_number) + "/task" + str(task_number) + "_1.png"
    with open(path_to_task_image, "rb") as photo:
        bot.send_photo(user_id, photo, caption="Выполните задание и отправьте ответ:")

@bot.message_handler(func=lambda message:
    user_states.get(message.from_user.id, {}).get("stage") == "task")
def handle_task_input(message):
    user_id = message.from_user.id
    text = message.text
    task_number = user_states.get(user_id).get("current_task_number")

    if text == correct_answers[task_number - 1]:
        bot.send_message(chat_id=user_id, text = "Ответ верный!")
    else:
        bot.send_message(chat_id=user_id, text="Ответ неверный")

bot.polling()
