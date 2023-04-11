import logging
from pprint import pprint

from telebot import TeleBot, types
from rest_framework.response import Response
from rest_framework.views import APIView

from data_filtering.core import ConverterData
from data_filtering.models import SessionTaxi
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

#
# @bot.message_handler(content_types=["text"])
# def get_okn(message):
#     bot.send_message(message.chat.id, "Ты пидор!")


@bot.message_handler(content_types=["document"])
def get_document(message):
    try:
        file_name = message.document.file_name
        user_name = message.chat.username
        user_id = message.chat.id
        fileID = message.document.file_id

        logger.info(f"Get FILE {file_name} from USER {user_name} mit ID {user_id}")
        if file_name.endswith(".txt"):
            bot.send_message(message.chat.id, "Файл успешно загружен, веду обработку")
            file_info = bot.get_file(fileID)
            downloaded_file = bot.download_file(file_info.file_path)
            if len(downloaded_file) < 10:
                logger.info(f"Error FILE {file_name} from USER {user_name} mit ID {user_id} - ERROR ZERO FILE")
                bot.send_message(message.chat.id, "Вы загрузили пустой файл")

            tiket_list = ConverterData.import_record(downloaded_file.decode('utf-8'))
            ConverterData.upload_session(tiket_list)

            logger.info(f"Get FILE {file_name} from USER {user_name} mit ID {user_id}")
            bot.send_message(message.chat.id, "Файл успешно обработан, данные внесены в таблицы")
        else:
            bot.send_message(message.chat.id, "Формат файла должен быть TXT")

    except Exception as ex:
        logger.info(f"Error FILE {file_name} from USER {user_name} mit ID {user_id} - ERROR {ex}")
        bot.send_message(message.chat.id, "Что-то пошло не так, попробуйте обратиться к боту позже")


@bot.message_handler(commands=['clear'])
def start_message(message):
    session = SessionTaxi.objects.all()
    session.delete()
    bot.send_message(message.chat.id, "Список сессий успешно очищен")


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