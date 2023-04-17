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

# Загрузка токена для активации бота, slice не трогать
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
    """Производит добавление пользователя в БД"""

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
    """Очистка списка всех сессий в БД"""

    session = SessionTaxi.objects.all()
    session.delete()
    bot.send_message(message.chat.id, "Список сессий успешно очищен")


@bot.message_handler(commands=['add'])
def add(message: types.Message):
    """Отвечает за добавление нового листа таблицы в БД и в Google Sheets"""

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
    """Тестовый модуль для отработки работы с Google Sheets"""
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
    """Ключевой модуль занимается обработкой документов"""

    # Создаём экземпляр класса, отвечающего за удобство взаимодействия с ботом
    connect_bot = BotConnect(bot, message)
    # Окончание названия файла является названием листа в Google Sheets
    name_sheet = connect_bot.file_name[25: -4]

    # Проверяет по названию факт наличия листа, если нет создаёт, если есть вызывает его,
    # так как он нужен для корректного создания сессий
    if Sheet.objects.filter(name=name_sheet).exists():
        sheet = Sheet.objects.get(name=name_sheet)
    else:
        sheet = generic_sheet(name_sheet)

    # Загружает файл из хранилища telegram, если файл пустой пишет сообщение человеку и логирует данный факт
    file = connect_bot.get_telegram_file()
    if not file:
        connect_bot.error_message("file have zero lines")
        return

    # Через класс ConverterData осуществляется чтение ланных из файла и их запись в БД
    upload_file = ConverterData()
    upload_file.import_session(file)
    upload_file.upload_session(sheet)

    # Стение данных из БД с приведением их к допустимому для загрузки в Google Sheets формату
    list_sessions = upload_file.list_data_session()
    # Загружаем list в который собраны все строки из файла, что не могли быть обработаны
    list_sessions_error = upload_file.ticket_error_list
    name_sheet = str(sheet)

    # Через класс ConnectGoogleSheet взаимодействуем с API Google Sheets
    sheet = ConnectGoogleSheet()

    # Для строк обработанных с ошибкой в Google Sheets предполагается отдельный лист,
    # имя которого образона от имени листа для записи корректных данных + строка ERROR_NAME_SHEET
    name_sheet_error = name_sheet + settings.ERROR_NAME_SHEET

    # Через метод upload_data_to_sheet осуществляется загрузка данных в листы таблицы
    if not (sheet.upload_data_to_sheet(list_sessions, name_sheet, 1) and
        sheet.upload_data_to_sheet(list_sessions_error, name_sheet, 9)):
        connect_bot.error_message("not find connect Google API")
        return

    connect_bot.success_message()


def add_sheet(message: types.Message):
    """Проверяет валидность имени для листа и в случае корректного названия вызывает его созлание"""

    name_sheet = message.text

    # Через ключевое слово Break можно выйти из режима создания листа
    if name_sheet == "Break":
        bot.send_message(message.chat.id, "Прерываю выполнение команды")
        return

    # Проверка наличия листа
    if Sheet.objects.filter(name=name_sheet).exists():
        bot.send_message(message.chat.id, "Лист с таким именем уже есть")
        return add(message)

    # Создаёт лист
    generic_sheet(message, name_sheet)
    bot.send_message(message.chat.id, "Добавлен новый лист таблицы")


def generic_sheet(name_sheet: str):
    """Отвечает за создание листа в таблице по запросу"""

    sheet = Sheet.objects.create(name=name_sheet)
    sheets = ConnectGoogleSheet()
    sheets.initial_sheet_google(name_sheet)

    return sheet

