import json
import logging
from os import path

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from telebot import TeleBot, types
from rest_framework.response import Response
from rest_framework.views import APIView

from data_filtering.core import ConverterData, BotConnect, ConnectGoogleSheet
from data_filtering.models import SessionTaxi, Profile, Sheet
from taxi_service import settings

token = settings.BOT_TOKEN[1:-1]
bot = TeleBot(token)
logger = logging.getLogger(__name__)


class UpdateBot(APIView):
    def post(self, request):
        # Сюда должны получать сообщения от телеграм и далее обрабатываться ботом
        json_str = request.body.decode('UTF-8')
        update = types.Update.de_json(json_str)
        bot.process_new_updates([update])

        return Response({'code': 200})


@bot.message_handler(commands=['start'])
def start(message: types.Message):
    user_id = message.chat.id
    telegram_username = message.chat.username
    Profile.objects.get_or_create(
        telegram_id=user_id,
        telegram_username=telegram_username,
    )
    bot.send_message(message.chat.id, "Вы успешно инициализированны в боте, "
                                      "для получения прав обратитесь к администратору")


@bot.message_handler(commands=['clear'])
def clear_bd(message: types.Message):
    session = SessionTaxi.objects.all()
    session.delete()
    bot.send_message(message.chat.id, "Список сессий успешно очищен")


@bot.message_handler(commands=['add'])
def add(message: types.Message):
    bot.send_message(message.chat.id, "Для добавления нового листа таблицы, введите имя листа: ")
    bot.register_next_step_handler(message, add_sheet)


# Доделать опцию создания новой таблицы
@bot.message_handler(commands=['create'])
def create_table(message: types.Message):
    """Используется при создании новой таблицы"""
    # sheets = ConnectGoogleSheet()
    # sh = sheets.client.create('Taxi_klp')
    # sh.share('blackwood20192@gmail.com', perm_type='user', role='writer')
    bot.send_message(message.chat.id, "Таблица создана")


@bot.message_handler(commands=['read'])
def read_table(message: types.Message):
    sheets = ConnectGoogleSheet()
    # worksheet = sheets.sh.add_worksheet(title="A worksheet24", rows=10000, cols=20)
    worksheet = sheets.sh.worksheet("Такси_Счастье_1")
    values_list = worksheet.col_values(1)
    sessions = SessionTaxi.objects.all()
    list_sessions = []

    for session in sessions:
        if session.time:
            correct_time = session.time.strftime("%H:%M.%f")
        else: correct_time = session.time
        list_sessions.append([
            session.date_session.strftime("%Y-%m-%d %H:%M:%S.%f"),
            session.phone,
            correct_time,
            session.starting_point,
            session.end_point,
            session.price
        ])
    position = f"A{len(values_list) + 1}:F{len(values_list) + len(sessions)}"
    worksheet.update(position, list_sessions, value_input_option='USER_ENTERED')

    bot.send_message(message.chat.id, "Данные добавлены в таблицу")


@bot.message_handler(content_types=["document"])
def get_document(message: types.Message):
    connect_bot = BotConnect(bot, message)

    name_sheet = connect_bot.file_name[25: -4]

    if Sheet.objects.filter(name=name_sheet).exists():
        sheet = Sheet.objects.get(name=name_sheet)

    else:
        sheet = generic_sheet(name_sheet)

    file = connect_bot.get_telegram_file()
    if not file:
        connect_bot.error_message("file have zero lines")
        return

    upload_file = ConverterData()
    upload_file.import_session(file)
    upload_file.upload_session(sheet)
    list_sessions = upload_file.list_data_session()
    name_sheet = str(sheet)
    sheet = ConnectGoogleSheet()
    list_sessions_error = upload_file.ticket_error_list
    name_sheet_error = name_sheet + settings.ERROR_NAME_SHEET
    if not (sheet.upload_data_to_sheet(list_sessions, name_sheet) and
        sheet.upload_data_to_sheet(list_sessions_error, name_sheet_error)):
        connect_bot.error_message("not find connect Google API")
        return

    connect_bot.success_message()


def add_sheet(message: types.Message):
    name_sheet = message.text
    if name_sheet == "Break":
        bot.send_message(message.chat.id, "Прерываю выполнение команды")
        return

    if Sheet.objects.filter(name=name_sheet).exists():
        bot.send_message(message.chat.id, "Лист с таким именем уже есть")
        return add(message)

    generic_sheet(message, name_sheet)
    bot.send_message(message.chat.id, "Добавлен новый лист таблицы")


def generic_sheet(name_sheet: str):
    sheet = Sheet.objects.create(name=name_sheet)
    sheets = ConnectGoogleSheet()
    sheets.initial_sheet_google(name_sheet)

    return sheet



# def index(request):
#
#     print(settings.BOT_TOKEN)
#     if request.META['CONTENT_TYPE'] == 'application/json':
#
#         json_data = request.body.decode('utf-8')
#         print(json_data)
#         update = telebot.types.Update.de_json(json_data)
#         bot.process_new_updates([update])
#
#         return HttpResponse("")
#
#     else:
#         raise PermissionDenied
#
#
# @bot.message_handler(content_types=["text"])
# def get_okn(message):
#     bot.send_message(message.chat.id, "Hello, bot!")
#
#


#     if request.method == "POST":
#         update = telebot.types.Update.de_json(request.body.decode('utf-8'))
#         bot.process_new_updates([update])
#
#     return HttpResponse('<h1>Ты подключился!</h1>')
#
#
# @bot.message_handler(commands=['start', 'help'])
# def send_welcome(message):
#     bot.reply_to(message, "Howdy, how are you doing?")


# @bot.message_handler(commands=['start'])
# def start(message: telebot.types.Message):
#     name = ''
#     if message.from_user.last_name is None:
#         name = f'{message.from_user.first_name}'
#     else:
#         name = f'{message.from_user.first_name} {message.from_user.last_name}'
#     bot.send_message(message.chat.id, f'Привет! {name}\n'
#                                       f'Я бот, который будет спамить вам беседу :)\n\n'
#                                       f'Чтобы узнать больше команд, напишите /help')