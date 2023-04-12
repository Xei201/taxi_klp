from datetime import datetime
import logging
import re
from os import path
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from django.db import transaction
from django.utils import timezone

from data_filtering.models import Profile, SessionTaxi
from taxi_service import settings

logger = logging.getLogger(__name__)


class BotConnect():
    """Отвечает за выгрузку из телеграм TXT файла + его валидацию"""
    def __init__(self, bot, message):
        self.bot = bot
        self.file_name, self.user_name, self.user_id, self.file_id = self.get_param_message(message)

    @classmethod
    def get_param_message(cls, message):
        file_name = message.document.file_name
        user_name = message.chat.username
        user_id = message.chat.id
        file_id = message.document.file_id
        return file_name, user_name, user_id, file_id

    def get_telegram_file(self) -> str:
        logger.info(f"Get FILE {self.file_name} from USER {self.user_name} mit ID {self.user_id}")

        try:
            if self.valid_file():
                self.bot.send_message(self.user_id, "Файл успешно загружен, веду обработку")
                downloaded_file = self.get_file()

                if len(downloaded_file) < settings.CONTROL_SIZE_FILE:
                    logger.info(f"Error FILE {self.file_name} from USER {self.user_name} mit ID "
                                f"{self.user_id} - ERROR ZERO FILE")
                    self.bot.send_message(self.user_id, "Вы загрузили пустой файл")

                    return None
                return downloaded_file.decode('utf-8')

            else:
                self.bot.send_message(self.user_id, "Формат файла должен быть TXT")
                return None
        except Exception as ex:
            logger.info(f"Error FILE {self.file_name} from USER {self.user_name} mit ID {self.user_id} - ERROR {ex}")
            self.bot.send_message(self.user_id, "Что-то пошло не так, попробуйте обратиться к боту позже")

    def get_file(self) -> str:
        file_info = self.bot.get_file(self.file_id)
        downloaded_file = self.bot.download_file(file_info.file_path)

        return downloaded_file

    def valid_file(self) -> bool:
        if self.file_name.endswith(".txt"):
            return True
        return False

    def success_message(self):
        logger.info(f"Get FILE {self.file_name} from USER {self.user_name} mit ID {self.user_id}")
        self.bot.send_message(self.user_id, "Файл успешно обработан, данные внесены в таблицы")

    def error_message(self):
        logger.info(f"Get FILE {self.file_name} from USER {self.user_name} "
                    f"mit ID {self.user_id} ERROR name_sheet not found")

        self.bot.send_message(self.user_id, "Таксиста с таким именем не внесён в базу, обратитесь к администратору")


class ConverterData():
    def __init__(self):
        self.ticket_list = []
        self.ticket_error_list = []

    def import_session(self, file: str):
        for line in file.split("\n"):
            try:
                ticket = line.split(',')

                if len(ticket) < 4:
                    self.ticket_error_list.append(ticket)
                    continue

                data = ticket[0] + ticket[1].split(" ")[1]

                data_correct = datetime.strptime(data, '%d.%m.%Y%H:%M')
                data_correct_timezone = timezone.make_aware(data_correct, timezone.get_current_timezone())
                phone = ticket[1].split(" ")[-1]
                if re.fullmatch(r'\d+:\d+', ticket[-4]):
                    time_correct = datetime.strptime(ticket[-4], '%H:%M')
                else:
                    time_correct = None

                ticket_correct = (data_correct_timezone, phone, time_correct, *ticket[-3:])
                self.ticket_list.append(ticket_correct)
            except Exception:
                self.ticket_error_list.append(line)
                continue

    def upload_session(self, profile):
        list_session = []
        for ticket in self.ticket_list:
            try:
                list_session.append(SessionTaxi(
                    profile=profile,
                    date_session=ticket[0],
                    phone=ticket[1],
                    time=ticket[2],
                    starting_point=ticket[3],
                    end_point=ticket[4],
                    price=int(ticket[5]),
                ))
            except Exception:
                self.ticket_error_list.append(" ".join(ticket))
                continue
        SessionTaxi.objects.bulk_create(list_session)


class ConnectGoogleSheet():
    def __init__(self):
        self.sh = self.get_sheets()

    @classmethod
    def get_sheets(cls):
        scope = [settings.GOOGLE_API_SHEETS,
                 settings.GOOGLE_API_AUTH]
        file = path.join("data_filtering", settings.FILE_API_GOOGLE_KEY)
        credentials = ServiceAccountCredentials.from_json_keyfile_name(file, scope)
        client = gspread.authorize(credentials)
        return client.open_by_key(settings.GOOGLE_SHEETS_ID)



