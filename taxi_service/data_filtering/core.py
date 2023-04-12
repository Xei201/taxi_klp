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

    def error_message(self, mes: str):
        logger.info(f"Get FILE {self.file_name} from USER {self.user_name} "
                    f"mit ID {self.user_id} ERROR {mes}")

        self.bot.send_message(self.user_id, f"Возникла внутренняя ошибка {mes}, обратитесь к администратору")


class ConverterData():
    def __init__(self):
        self.ticket_list = []
        self.ticket_error_list = []
        self.amount = 0

    def import_session(self, file: str):
        for line in file.split("\n"):
            try:
                ticket = line.split(',')

                if len(ticket) < 4:
                    self.ticket_error_list.append([line])
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

    def upload_session(self, sheet):
        list_session = []

        for ticket in self.ticket_list:
            try:
                list_session.append(SessionTaxi(
                    sheet=sheet,
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
            self.amount = len(list_session)
        SessionTaxi.objects.bulk_create(list_session)

    def list_data_session(self) -> list:
        all_session = SessionTaxi.objects.count()
        sessions = SessionTaxi.objects.all().order_by("pk")[(all_session - self.amount):]

        list_sessions = []
        for session in sessions:
            if session.time:
                correct_time = session.time.strftime("%H:%M.%f")
            else:
                correct_time = session.time
            list_sessions.append([
                session.date_session.strftime("%Y-%m-%d %H:%M:%S.%f"),
                session.phone,
                correct_time,
                session.starting_point,
                session.end_point,
                session.price
            ])
        return list_sessions


class ConnectGoogleSheet():
    def __init__(self):
        self.client = self.get_client()
        self.sh = self.get_client().open_by_key(settings.GOOGLE_SHEETS_ID)

    @classmethod
    def get_client(cls):
        scope = [settings.GOOGLE_API_SHEETS,
                 settings.GOOGLE_API_AUTH]
        file = path.join("data_filtering", settings.FILE_API_GOOGLE_KEY)
        credentials = ServiceAccountCredentials.from_json_keyfile_name(file, scope)
        client = gspread.authorize(credentials)
        return client

    def initial_sheet_google(self, name_sheet):
        worksheet = self.sh.add_worksheet(title=name_sheet, rows=10000, cols=20)
        name_sheet_error = name_sheet + settings.ERROR_NAME_SHEET
        worksheet2 = self.sh.add_worksheet(title=name_sheet_error, rows=10000, cols=20)

        worksheet.update(
            'A1',
            [["Дата", "Телефон", "Время", "Начальная точка", "Конечная точка", "Сумма"]],
            value_input_option='USER_ENTERED')
        worksheet2.update('A1', [["Ошибочные строки"]], value_input_option='USER_ENTERED')

    def upload_data_to_sheet(self, list_sessions: list, name: str) -> bool:
        worksheet = self.sh.worksheet(str(name))
        values_list = worksheet.col_values(1)
        col = settings.LATIN[len(list_sessions[0])]

        position = f"A{len(values_list) + 1}:{col}{len(values_list) + len(list_sessions)}"
        try:
            worksheet.update(position, list_sessions, value_input_option='USER_ENTERED')
            col2 = settings.LATIN[len(list_sessions[0]) + 1]
            position_end_line = f"{col2}{len(values_list) + len(list_sessions)}"
            worksheet.update(position_end_line, "Конец сессии записи", value_input_option='USER_ENTERED')
        except Exception:
            return False
        return True



