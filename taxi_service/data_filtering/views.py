import base64
import logging
from functools import wraps

from django.db.models import Sum
from django.views.generic import TemplateView
from telebot import TeleBot, types
from rest_framework.response import Response
from rest_framework.views import APIView

from .core import ConverterData, BotConnect, ConnectGoogleSheet
from .models import SessionTaxi, Profile, Sheet, SessionImportBD
from .tasks import send_test_telegram_message_task, send_long_message_task
from .graph import GG_Money_Per_Month, GG_Date2Price_AllTime
from taxi_service import settings


# Загрузка токена для активации бота, slice не трогать

token = settings.BOT_TOKEN[1:-1]
bot = TeleBot(token)
# Подключение для логирования ошибок
logger = logging.getLogger(__name__)


def private_access():
    """Проверяет право доступа пользователя к операциям бота"""
    def deco_restrict(f):

        @wraps(f)
        def f_restrict(message, *args, **kwargs):
            telegram_user_id = message.chat.id
            profile = Profile.objects.get(telegram_id=telegram_user_id)

            if not profile.user:
                bot.send_message(message.chat.id, "Вы не имеете прав доступа, обратитесь к Администратору")

            if profile.user.is_staff:
                return f(message, *args, **kwargs)
            else:
                bot.send_message(message.chat.id, "Вы не имеете прав доступа, обратитесь к Администратору")

        return f_restrict  # сам декоратор

    return deco_restrict


class UpdateBot(APIView):
    # permission_classes = (StaffPermission, )

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
@private_access()
def add(message: types.Message):
    """Отвечает за добавление нового листа таблицы в БД и в Google Sheets"""

    bot.send_message(message.chat.id, "Для добавления нового листа таблицы, введите имя листа: ")
    bot.register_next_step_handler(message, add_sheet)


@bot.message_handler(commands=['test_m'])
@private_access()
def test_m(message: types.Message):
    try:
        bot.send_message(message.chat.id, "Тестирование отложенного процесса")
        send_test_telegram_message_task.delay(
            message.chat.id
        )
    except Exception as ex:
        print("Error:", ex)


@bot.message_handler(commands=['long_m'])
@private_access()
def long_m(message: types.Message):
    """Система для отправки отложенных сообщений"""
    bot.send_message(message.chat.id, "Для запуска системы укажите время задержки отправки сообщения в секундах: ")
    bot.register_next_step_handler(message, add_test_long_message)


def add_test_long_message(message):
    time_out = int(message.text)
    bot.send_message(message.chat.id, "Введите текст сообщения для рассылки")
    bot.register_next_step_handler(message, add_test_long_message2, time_out)


def add_test_long_message2(message, time_out):
    text_message = message.text
    try:
        bot.send_message(message.chat.id, "Рассылка загружена в очередь")
        send_long_message_task.apply_async(
            (time_out, text_message),
            countdown=time_out
        )
    except Exception as ex:
        print("Error:", ex)


# Доделать опцию создания новой таблицы
@bot.message_handler(commands=['create'])
@private_access()
def create_table(message: types.Message):
    """Используется при создании новой таблицы"""
    # sheets = ConnectGoogleSheet()
    # sh = sheets.client.create('Taxi_klp')
    # sh.share('blackwood20192@gmail.com', perm_type='user', role='writer')
    bot.send_message(message.chat.id, "Таблица создана")


@bot.message_handler(content_types=["document"])
@private_access()
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

    # Через класс ConverterData осуществляется чтение данных из файла и их запись в БД
    upload_file = ConverterData()
    upload_file.import_session(file)
    upload_file.upload_session(sheet)

    # Чтение данных из БД с приведением их к допустимому для загрузки в Google Sheets формату
    list_sessions = upload_file.list_data_session()
    # Загружаем list в который собраны все строки из файла, что не могли быть обработаны
    list_sessions_error = upload_file.ticket_error_list
    name_sheet = str(sheet)

    # Через класс ConnectGoogleSheet взаимодействуем с API Google Sheets
    sheet = ConnectGoogleSheet()

    # СБорка данных для загрузки в общую таблицу отчётности
    sum_data_session = upload_file.sum_data_session()
    sum_data_session[0].insert(1, name_sheet)

    # Через метод upload_data_to_sheet осуществляется загрузка данных в листы таблицы
    if not (
            sheet.upload_data_to_sheet(list_sessions, name_sheet, 1) and
            sheet.upload_data_to_sheet(list_sessions_error, name_sheet, 10) and
            sheet.upload_data_to_sheet(list_sessions, settings.NAME_GROUP_SHEETS, 1) and
            sheet.upload_data_to_sheet(sum_data_session, settings.NAME_GENERAL_SHEETS, 1)
            ):
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
    generic_sheet(name_sheet)
    bot.send_message(message.chat.id, "Добавлен новый лист таблицы")


def generic_sheet(name_sheet: str):
    """Отвечает за создание листа в таблице по запросу"""

    sheet = Sheet.objects.create(name=name_sheet)
    sheets = ConnectGoogleSheet()
    sheets.initial_sheet_google(name_sheet)

    return sheet


@bot.message_handler(commands=['read'])
@private_access()
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


@bot.message_handler(commands=['test_agregate'])
@private_access()
def long_m(message: types.Message):
    try:
        test_list = SessionImportBD.objects.filter(id=2).aggregate(avg_data=Sum("amount_record"))
        bot.send_message(message.chat.id, f"Всего итемов {test_list['avg_data']}")
    except Exception as ex:
        bot.send_message(message.chat.id, f"Ошибка {ex}")


class GraficView(TemplateView):
    template_name = 'graf.html'

    def get_context_data(self, **kwargs):
        context = {}

        test_graph = GG_Money_Per_Month(1)
        pic_hash = test_graph.get_graph_to_base64()

        context['image'] = pic_hash

        test_graph = GG_Money_Per_Month(12)
        pic_hash = test_graph.get_graph_to_base64()

        context['image2'] = pic_hash

        graph_all_time = GG_Date2Price_AllTime()
        result_graph_all_time = graph_all_time.get_graph_to_base64()

        context["image3"] = result_graph_all_time
        return context

