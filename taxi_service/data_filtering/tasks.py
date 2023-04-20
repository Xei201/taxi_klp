import logging
from time import sleep

from celery import shared_task
from taxi_service import settings

from telebot import TeleBot, types


token = settings.BOT_TOKEN[1:-1]
bot = TeleBot(token)
logger = logging.getLogger(__name__)


@shared_task(bind=True)
def send_test_telegram_message_task(self, id):
    try:
        bot.send_message(id, "Старт отложенного процессаб спать 20")
        sleep(20)
        bot.send_message(id, "Поспал зоебись")
    except Exception as ex:
        logger.info(f"Error celery worker {ex}")


@shared_task(bind=True)
def send_long_message_task(self, id, time_out):
    try:
        bot.send_message(id, f"Вот и прошло {time_out}")
        sleep(20)
        bot.send_message(id, "Поспал зоебись")
    except Exception as ex:
        logger.info(f"Error celery worker {ex}")


@shared_task(bind=True)
def constant_message_task(self, id):
    try:
        bot.send_message(id, f"Ты там всё ещё живой? Пора учиться!")
        sleep(20)
        bot.send_message(id, "Проверка sleep - имитация нагруженной операции с БД")
    except Exception as ex:
        logger.info(f"Error celery worker {ex}")

