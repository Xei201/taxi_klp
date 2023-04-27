import logging
from time import sleep

from celery import shared_task
from django.db.models import Sum

from taxi_service import settings

from telebot import TeleBot, types

from .models import Profile, SessionImportBD, SessionTaxi
from .core import ConverterData, BotConnect, ConnectGoogleSheet


token = settings.BOT_TOKEN[1:-1]
bot = TeleBot(token)
logger = logging.getLogger(__name__)


@shared_task(bind=True)
def send_test_telegram_message_task(self, id):
    try:
        bot.send_message(id, "Старт отложенного процессаб спать 20")
        sleep(20)
        bot.send_message(id, "Поспал хорошо")
    except Exception as ex:
        logger.info(f"Error celery worker {ex}")


@shared_task(bind=True)
def send_long_message_task(self, time_out, text_message):
    staff_user_id = Profile.objects.filter(user__is_staff=True).values_list("telegram_id", flat=True)
    for id in staff_user_id:
        try:
            bot.send_message(id, text_message)
        except Exception as ex:
            logger.info(f"Error celery worker {ex}")


@shared_task(bind=True)
def constant_message_task(self):
    try:
        staff_user_id = Profile.objects.filter(user__is_staff=True).values_list("telegram_id", flat=True)

        for id in staff_user_id:
            bot.send_message(id, f"Имитация работы системы выгрузки данных в Google Sheets")

        # Иммитация процесс выгрузки данных в Google Sheets
        sleep(20)

        for id in staff_user_id:
            bot.send_message(id, "Выгрузка прошла успешно")
    except Exception as ex:
        logger.info(f"Error celery worker {ex}")


@shared_task(bind=True)
def beat_upload_bd(self):
    try:
        # получаем сумму всех прошлых выгрузок, чтобы определить с какой позиции начать новую выгрузку
        amount_record = SessionImportBD.objects.aggregate(avg_data=Sum("amount_record"))["avg_data"]
        # если выгрузок не было, присваиваем нулевое значение
        if not amount_record:
            amount_record = 0

        # считаем сколько записей нужно выгрузить
        offset_num = SessionTaxi.objects.count() - amount_record
        if offset_num == 0:
            return

        # получаем сессии для импорта в гугл таблицу
        upload_file = ConverterData()
        upload_file.amount = offset_num
        list_sessions = upload_file.list_data_session()

        staff_user_id = Profile.objects.filter(user__is_staff=True).values_list("telegram_id", flat=True)

        # запуск загрузки данных в гугл таблицу
        sheet = ConnectGoogleSheet()
        if not sheet.upload_data_to_sheet(list_sessions, settings.NAME_GROUP_SHEETS, 1):
            logger.info(f"Error google sheets connect for listen every day session")

            for id in staff_user_id:
                bot.send_message(id, f"Ошибка выгрузки данных в Google Sheets")
        else:
            logger.info(f"Success import everyday session in google sheets")
            SessionImportBD.objects.create(amount_record=offset_num)
            for id in staff_user_id:
                bot.send_message(id, f"Успешная выгрузка ежедневная выгрузка данных в Google Sheets")

    except Exception as ex:
        logger.info(f"Error celery worker {ex}")

