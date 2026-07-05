import random

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from PIL import Image, ImageDraw, ImageFont
import os
import psycopg2

NUMBER_OF_TASKS = 27
EXAM_SCORE_CONVERSION = [0, 7, 14, 20, 27, 34, 40, 43, 46, 48, 51, 54, 56, 59, 62, 64, 67, 70, 72, 75, 78, 80, 83, 85, 88, 90, 93, 95, 98, 100]

with open('token.txt', 'r') as f:
    token = f.read()

bot=telebot.TeleBot(token)

#correct_answers = ["26", "xzy", "801", "14", "19", "17", "10", "270", "3094", "64", "94", "28", "192", "3", "23", "120", "180 190360573", "1911 178", "43", "2324324445", "25", "17", "13", "1004", "101075762 101417282 101588258 101645282", "568 50", "471228 49113954961677"]

user_states = {}

#Подключение к БД
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="postgres",
    host="localhost"
)

cursor = conn.cursor()

#Создать markup с кнопками для навигации по заданиям
def create_task_markup(task_number):
    if task_number == 1:
        prev_task_number = NUMBER_OF_TASKS
    else:
        prev_task_number = task_number - 1

    if task_number == NUMBER_OF_TASKS:
        next_task_number = 1
    else:
        next_task_number = task_number + 1

    prev_task_callback = "task_" + str(prev_task_number)
    next_task_callback = "task_" + str(next_task_number)
    task_markup = InlineKeyboardMarkup()
    buttons = []
    buttons.append(InlineKeyboardButton(text="Предыдущее", callback_data=prev_task_callback))
    buttons.append(InlineKeyboardButton(text="Следующее", callback_data=next_task_callback))
    task_markup.row(*buttons)
    task_markup.add(InlineKeyboardButton(text="К списку заданий", callback_data="btn_start_exam"))
    task_markup.add(InlineKeyboardButton(text="Очистить мой выбор", callback_data="clear_answer"))
    task_markup.add(InlineKeyboardButton(text="Завершить экзамен", callback_data="finish_exam_warning_message"))

    return task_markup

@bot.message_handler(commands=['start'])
def send_main_menu_options(message):
    user_id = message.from_user.id

    #Добавление в sql таблицу записи о статистике пользователя, если ее еще нет
    cursor.execute("""
        INSERT INTO bot.user_stats (
            user_id,
            variants_completed,
            tasks_completed,
            correct_tasks,
            uncorrect_tasks,
            unanswered_tasks
        )
        VALUES (%s, 0, 0, 0, 0, 0)
        ON CONFLICT(user_id) DO NOTHING
    """, (user_id,))

    conn.commit()

    user_answers = []
    for i in range(NUMBER_OF_TASKS):
        user_answers.append(None)

    #Создание варианта из случайных заданий
    task_variants = []
    for i in range(NUMBER_OF_TASKS):
        task_variants.append(random.randint(1, 3))

    #Получение правильных ответов на вариант
    correct_answers = []
    for i in range(NUMBER_OF_TASKS):
        path_to_answer = "tasks/" + str(i+1) + "/" + str(task_variants[i]) + "/answer.txt"
        with open(path_to_answer, "r", encoding="utf-8") as f:
            answer = f.read()
            correct_answers.append(answer)

    user_states[user_id] = {
        "stage": "Menu",
        "current_task_number" : None,
        "user_answers": user_answers,
        "is_task_sent": False,
        "task_image_message_id": None,
        "task_answer_message_id": None,
        "task_answer_message_text": None,
        "document_message_ids": [],
        "task_variants": task_variants,
        "correct_answers": correct_answers
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

    task_variant = user_states[user_id]["task_variants"][task_number - 1]
    path_to_task_files = "tasks/" + str(task_number) + "/" + str(task_variant)
    path_to_task_image = path_to_task_files + "/image.png"
    path_to_task_text = path_to_task_files + "/task.txt"

    with open(path_to_task_text, "r", encoding="utf-8") as file:
        text = file.read()
        text_message = bot.send_message(user_id, text=text)
        user_states[user_id]["task_image_message_id"] = text_message.id

    if os.path.isfile(path_to_task_image):
        with open(path_to_task_image, "rb") as photo:
            image_message = bot.send_photo(user_id, photo)
            user_states[user_id]["task_image_message_id"] = image_message.id

    task_files = os.listdir(path_to_task_files)
    for filename in task_files:
        if not ((filename == "image.png") or (filename == "task.txt") or (filename == "answer.txt")):
            path_to_file = path_to_task_files + "/" + filename
            with open(path_to_file, "rb") as file:
                message = bot.send_document(user_id, file)
                user_states[user_id]["document_message_ids"].append(message.id)

    user_answer = user_states[user_id]["user_answers"][task_number - 1]
    if user_answer is None:
        message = "Вы не давали ответ на это задание"
    else:
        message = "Ваш ответ: " + user_answer

    task_markup = create_task_markup(task_number)
    user_states[user_id]["task_answer_message_text"] = message
    answer_message = bot.send_message(chat_id=user_id, reply_markup=task_markup, text=message)
    user_states[user_id]["task_answer_message_id"] = answer_message.id

@bot.message_handler(func=lambda message:
    user_states.get(message.from_user.id, {}).get("stage") == "task")
def handle_task_input(message):
    user_id = message.from_user.id
    task_number = user_states.get(user_id).get("current_task_number")
    text = message.text

    task_markup = create_task_markup(task_number)

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

    task_markup = create_task_markup(task_number)
    bot.edit_message_text(
        chat_id=user_id,
        message_id=user_states[user_id]["task_answer_message_id"],
        reply_markup=task_markup,
        text="Вы не давали ответ на это задание"
    )

    user_states[user_id]["task_answer_message_text"] = "Вы не давали ответ на это задание"
    user_states[user_id]["user_answers"][task_number - 1] = None

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

    #Подсчет баллов
    user_answers = user_states.get(user_id).get("user_answers")
    primary_score = 0
    for task in range(1, NUMBER_OF_TASKS + 1):
        if user_answers[task - 1] == user_states[user_id]["correct_answers"][task - 1]:
            if (task >= 1) and (task <= 25):
                primary_score += 1
            elif (task >= 26) and (task <= 27):
                primary_score += 2

    secondary_score = EXAM_SCORE_CONVERSION[primary_score]

    #Сборка статистики об этом прорешанном варианте
    correct_tasks_count = 0
    uncorrect_tasks_count = 0
    uncompleted_tasks_count = 0

    for task in range(1, NUMBER_OF_TASKS + 1):
        if user_answers[task - 1] == user_states[user_id]["correct_answers"][task - 1]:
            correct_tasks_count += 1
        elif user_answers[task - 1] is None:
            uncompleted_tasks_count += 1
        else:
            uncorrect_tasks_count += 1

    cursor.execute("""
        UPDATE bot.user_stats
        SET
            variants_completed = variants_completed + 1,
            tasks_completed = tasks_completed + %s,
            correct_tasks = correct_tasks + %s,
            uncorrect_tasks = uncorrect_tasks + %s,
            unanswered_tasks = unanswered_tasks + %s
        WHERE user_id = %s
    """, (
        NUMBER_OF_TASKS,
        correct_tasks_count,
        uncorrect_tasks_count,
        uncompleted_tasks_count,
        user_id,
    ))

    conn.commit()

    #Заполнение таблицы ответами, покрас ячеек
    img = Image.open("results_empty.png")
    draw = ImageDraw.Draw(img)
    font_text = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", size=14)
    border_color = "#2D3436"
    correct_color = "#D4EDDA"
    wrong_color = "#F8D7DA"
    neutral_color = "#FFFFFF"

    for number in range(NUMBER_OF_TASKS):

        y1 = 45 * (number + 1)
        y2 = 45 * (number + 2)

        user_answer = user_answers[number]
        correct_answer = user_states[user_id]["correct_answers"][number]

        if user_answer == correct_answer:
            color = correct_color
        elif user_answer is None:
            color = neutral_color
        else:
            color = wrong_color

        draw.rounded_rectangle(
        [(95, y1 + 5),
            (90 * 5 - 5, y2 - 5)],
            radius=8,
            fill=color,
            outline=border_color,
            width=1
        )

        text_y = (y1 + 45 // 2)

        if user_answer is not None:
            draw.text(
                (270, text_y),
                str(user_answer),
                font=font_text,
                fill="#2D3436",
                anchor="mm"
            )

        draw.text(
            (630, text_y),
            str(correct_answer),
            font=font_text,
            fill="#2D3436",
            anchor="mm"
        )

    img.save("results.png")

    message = "Ваш итоговый результат: " + str(secondary_score) + " баллов из 100"
    with open("results.png", "rb") as photo:
        bot.send_photo(user_id, photo, caption=message)

@bot.callback_query_handler(func=lambda call: call.data == "btn_statistics")
def send_statistics(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)

    cursor.execute("""
        SELECT
            variants_completed,
            tasks_completed,
            correct_tasks,
            uncorrect_tasks,
            unanswered_tasks
        FROM bot.user_stats
        WHERE user_id = %s
    """, (user_id,))

    row = cursor.fetchone()

    text = (
        f"Ваша статистика:\n"
        f"Выполнено вариантов: {row[0]}\n"
        f"Выполнено задач: {row[1]}\n"
        f"Правильно выполненных задач: {row[2]}\n"
        f"Неправильно выполненных задач: {row[3]}\n"
        f"Задач, на которые не дан ответ: {row[4]}\n")

    bot.send_message(user_id, text=text)

bot.polling()
conn.close()