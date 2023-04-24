import logging
from time import sleep

from celery import shared_task
from taxi_service import settings

from telebot import TeleBot, types

from .models import Profile

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
        logger.info(f"LOg ID {staff_user_id}")

        for id in staff_user_id:
            bot.send_message(id, f"Имитация работы системы выгрузки данных в Google Sheets")

        # Иммитация процесс выгрузки данных в Google Sheets
        sleep(20)

        for id in staff_user_id:
            bot.send_message(id, "Выгрузка прошла успешно")
    except Exception as ex:
        logger.info(f"Error celery worker {ex}")

