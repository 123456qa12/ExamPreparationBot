import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from PIL import Image, ImageDraw, ImageFont
import os

NUMBER_OF_TASKS = 27
EXAM_SCORE_CONVERSION = [0, 7, 14, 20, 27, 34, 40, 43, 46, 48, 51, 54, 56, 59, 62, 64, 67, 70, 72, 75, 78, 80, 83, 85, 88, 90, 93, 95, 98, 100]

with open('token.txt', 'r') as f:
    token = f.read()

bot=telebot.TeleBot(token)

correct_answers = ["26", "xzy", "801", "14", "19", "17", "10", "270", "3094", "64", "94", "28", "192", "3", "23", "120", "180 190360573", "1911 178", "43", "2324324445", "25", "17", "13", "1004", "101075762 101417282 101588258 101645282", "568 50", "471228 49113954961677"]

task_markup = InlineKeyboardMarkup()
buttons = []
buttons.append(InlineKeyboardButton(text="Предыдущее", callback_data="prev_task"))
buttons.append(InlineKeyboardButton(text="Следующее", callback_data="next_task"))
task_markup.row(*buttons)
task_markup.add(InlineKeyboardButton(text="К списку заданий", callback_data="btn_start_exam"))
task_markup.add(InlineKeyboardButton(text="Очистить мой выбор", callback_data="clear_answer"))
task_markup.add(InlineKeyboardButton(text="Завершить экзамен", callback_data="finish_exam_warning_message"))

user_states = {}

@bot.message_handler(commands=['start'])
def send_main_menu_options(message):
    user_id = message.from_user.id

    user_answers = []
    for i in range(NUMBER_OF_TASKS):
        user_answers.append(None)

    user_states[user_id] = {
        "stage": "Menu",
        "current_task_number" : None,
        "user_answers": user_answers,
        "is_task_sent": False,
        "task_image_message_id": None,
        "task_answer_message_id": None,
        "task_answer_message_text": None,
        "document_message_ids": []
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
    markup.add(InlineKeyboardButton(text="Завершить экзамен", callback_data="finish_exam_warning_message"))

    bot.send_message(chat_id=user_id, reply_markup=markup, text="Выберите задание:")

@bot.callback_query_handler(func=lambda call: call.data.startswith("task_"))
def send_task(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)

    task_number = int(call.data.split("_")[1])
    user_states[user_id]["current_task_number"] = task_number
    user_states[user_id]["stage"] = "task"
    path_to_task_files = "tasks/" + str(task_number)
    path_to_task_image = path_to_task_files + "/task" + str(task_number) + "_1.png"
    with open(path_to_task_image, "rb") as photo:
        image_message = bot.send_photo(user_id, photo, caption="Выполните задание и отправьте ответ на него")
        user_states[user_id]["task_image_message_id"] = image_message.id

    task_files = os.listdir(path_to_task_files)
    for filename in task_files:
        if not filename.endswith(".png"):
            path_to_file = path_to_task_files + "/" + filename
            with open(path_to_file, "rb") as file:
                message = bot.send_document(user_id, file)
                user_states[user_id]["document_message_ids"].append(message.id)

    user_answer = user_states[user_id]["user_answers"][task_number - 1]
    if user_answer is None:
        message = "Вы не давали ответ на это задание"
    else:
        message = "Ваш ответ: " + user_answer

    user_states[user_id]["task_answer_message_text"] = message
    answer_message = bot.send_message(chat_id=user_id, reply_markup=task_markup, text=message)
    user_states[user_id]["task_answer_message_id"] = answer_message.id

@bot.message_handler(func=lambda message:
    user_states.get(message.from_user.id, {}).get("stage") == "task")
def handle_task_input(message):
    user_id = message.from_user.id
    task_number = user_states.get(user_id).get("current_task_number")
    text = message.text

    bot.edit_message_text(
        chat_id=user_id,
        message_id=user_states[user_id]["task_answer_message_id"],
        reply_markup=task_markup,
        text="Ваш ответ: " + text
    )

    user_states[user_id]["task_answer_message_text"] = "Ваш ответ: " + text
    user_states[user_id]["user_answers"][task_number - 1] = text

@bot.callback_query_handler(func=lambda call: call.data == "clear_answer")
def clear_task_answer(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    task_number = user_states[user_id]["current_task_number"]

    bot.edit_message_text(
        chat_id=user_id,
        message_id=user_states[user_id]["task_answer_message_id"],
        reply_markup=task_markup,
        text="Вы не давали ответ на это задание"
    )

    user_states[user_id]["task_answer_message_text"] = "Вы не давали ответ на это задание"
    user_states[user_id]["user_answers"][task_number - 1] = None

@bot.callback_query_handler(func=lambda call: call.data == "prev_task")
def show_prev_task(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)

    for message_id in user_states[user_id]["document_message_ids"]:
        bot.delete_message(user_id, message_id)
    user_states[user_id]["document_message_ids"] = []

    task_number = int(user_states.get(user_id).get("current_task_number"))
    if task_number == 1:
        task_number = NUMBER_OF_TASKS
    else:
        task_number -= 1

    path_to_new_task_image = "tasks/" + str(task_number) + "/task" + str(task_number) + "_1.png"
    with open(path_to_new_task_image, "rb") as photo:
        bot.edit_message_media(
            media=InputMediaPhoto(photo),
            chat_id=user_id,
            message_id=user_states[user_id]["task_image_message_id"]
        )

    path_to_task_files = "tasks/" + str(task_number)
    task_files = os.listdir(path_to_task_files)
    for filename in task_files:
        if not filename.endswith(".png"):
            path_to_file = path_to_task_files + "/" + filename
            with open(path_to_file, "rb") as file:
                message = bot.send_document(user_id, file)
                user_states[user_id]["document_message_ids"].append(message.id)

    user_answer = user_states[user_id]["user_answers"][task_number - 1]
    if user_answer is None:
        message = "Вы не давали ответ на это задание"
    else:
        message = "Ваш ответ: " + user_answer

    if user_states[user_id]["task_answer_message_text"] != message:
        bot.edit_message_text(
            chat_id=user_id,
            message_id=user_states[user_id]["task_answer_message_id"],
            reply_markup=task_markup,
            text=message
        )

    user_states[user_id]["task_answer_message_text"] = message
    user_states[user_id]["current_task_number"] = task_number

@bot.callback_query_handler(func=lambda call: call.data == "next_task")
def show_next_task(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)

    for message_id in user_states[user_id]["document_message_ids"]:
        bot.delete_message(user_id, message_id)
    user_states[user_id]["document_message_ids"] = []

    task_number = int(user_states.get(user_id).get("current_task_number"))
    if task_number == NUMBER_OF_TASKS:
        task_number = 1
    else:
        task_number += 1

    path_to_new_task_image = "tasks/" + str(task_number) + "/task" + str(task_number) + "_1.png"
    with open(path_to_new_task_image, "rb") as photo:
        bot.edit_message_media(
            media=InputMediaPhoto(photo),
            chat_id=user_id,
            message_id=user_states[user_id]["task_image_message_id"]
        )

    path_to_task_files = "tasks/" + str(task_number)
    task_files = os.listdir(path_to_task_files)
    for filename in task_files:
        if not filename.endswith(".png"):
            path_to_file = path_to_task_files + "/" + filename
            with open(path_to_file, "rb") as file:
                message = bot.send_document(user_id, file)
                user_states[user_id]["document_message_ids"].append(message.id)

    user_answer = user_states[user_id]["user_answers"][task_number - 1]
    if user_answer is None:
        message = "Вы не давали ответ на это задание"
    else:
        message = "Ваш ответ: " + user_answer

    if user_states[user_id]["task_answer_message_text"] != message:
        bot.edit_message_text(
            chat_id=user_id,
            message_id=user_states[user_id]["task_answer_message_id"],
            reply_markup=task_markup,
            text=message
        )

    user_states[user_id]["task_answer_message_text"] = message
    user_states[user_id]["current_task_number"] = task_number

@bot.callback_query_handler(func=lambda call: call.data ==  "finish_exam_warning_message")
def send_finish_exam_warning_message(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)

    markup = InlineKeyboardMarkup()
    buttons = []
    buttons.append(InlineKeyboardButton(text="Да", callback_data="exam_results"))
    buttons.append(InlineKeyboardButton(text="Нет", callback_data="btn_start_exam"))
    markup.row(*buttons)
    bot.send_message(user_id, text="Вы уверены, что хотите завершить экзамен?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data ==  "exam_results")
def send_exam_results(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)

    user_answers = user_states.get(user_id).get("user_answers")
    primary_score = 0
    for task in range(1, NUMBER_OF_TASKS + 1):
        if user_answers[task - 1] == correct_answers[task - 1]:
            if (task >= 1) and (task <= 25):
                primary_score += 1
            elif (task >= 26) and (task <= 27):
                primary_score += 2

    secondary_score = EXAM_SCORE_CONVERSION[primary_score]

    img = Image.open("results_empty.png")
    draw = ImageDraw.Draw(img)
    font_14 = ImageFont.truetype("arial.ttf", 14)
    for number in range(NUMBER_OF_TASKS):
        rectangle_y1 = 45 * (number + 1)
        rectangle_y2 = 45 * (number + 2)
        user_answer = user_states[user_id]["user_answers"][number]
        correct_answer = correct_answers[number]
        if user_answer == correct_answer:
            rectangle_color = "green"
        else:
            rectangle_color = "red"
        draw.rectangle([(90, rectangle_y1), (90 * 5, rectangle_y2)], fill=rectangle_color, outline="black", width=3)

        text_y = 45 * number + 45 + (45 // 2)
        if user_answer is not None:
            draw.text((270, text_y), str(user_answer), font=font_14, fill="black", anchor="mm")
        draw.text((630, text_y), str(correct_answer), font=font_14, fill="black", anchor="mm")

    img.save("results.png")

    message = "Ваш итоговый результат: " + str(secondary_score) + " баллов из 100"
    with open("results.png", "rb") as photo:
        bot.send_photo(user_id, photo, caption=message)

bot.polling()