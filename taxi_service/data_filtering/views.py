import json
import logging
from os import path

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from telebot import TeleBot, types
from rest_framework.response import Response
from rest_framework.views import APIView

from data_filtering.core import ConverterData, BotConnect, ConnectGoogleSheet
from data_filtering.models import SessionTaxi, Profile
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
def start_message(message: types.Message):
    session = SessionTaxi.objects.all()
    session.delete()
    bot.send_message(message.chat.id, "Список сессий успешно очищен")


@bot.message_handler(commands=['create'])
def create_table(message: types.Message):
    # scope = [settings.GOOGLE_API_SHEETS,
    #          settings.GOOGLE_API_AUTH]
    # file = path.join("data_filtering", settings.FILE_API_GOOGLE_KEY)
    # credentials = ServiceAccountCredentials.from_json_keyfile_name(file, scope)
    # client = gspread.authorize(credentials)
    # sh = client.create('Taxi_klp')
    # sh.share('blackwood20192@gmail.com', perm_type='user', role='writer')
    bot.send_message(message.chat.id, "Таблица создана")


@bot.message_handler(commands=['read'])
def read_table(message: types.Message):
    sheets = ConnectGoogleSheet()
    # worksheet = sheets.sh.add_worksheet(title="A worksheet24", rows=10000, cols=20)
    worksheet = sheets.sh.worksheet("A worksheet24")
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
    print(position)
    worksheet.update(position, list_sessions, value_input_option='USER_ENTERED')

    bot.send_message(message.chat.id, "Данные добавлены в таблицу")


@bot.message_handler(content_types=["document"])
def get_document(message: types.Message):
    connect_bot = BotConnect(bot, message)

    name_sheet = connect_bot.file_name[25: -4]
    if Profile.objects.filter(name_sheet=name_sheet).exists():
        profile = Profile.objects.get(name_sheet=name_sheet)
    else:
        connect_bot.error_message()
        return

    file = connect_bot.get_telegram_file()
    if file:
        upload_file = ConverterData()
        upload_file.import_session(file)
        name_sheet = connect_bot.file_name[25: -4]
        upload_file.upload_session(profile)
        connect_bot.success_message()





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