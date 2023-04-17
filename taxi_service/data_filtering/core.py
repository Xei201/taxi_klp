from datetime import datetime
import logging
import re
from os import path
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from django.db import transaction
from django.utils import timezone
from telebot import TeleBot, types

from data_filtering.models import SessionTaxi
from taxi_service import settings

logger = logging.getLogger(__name__)


class BotConnect():
    """Отвечает за выгрузку из телеграм TXT файла + его валидацию"""
    def __init__(self, bot: TeleBot, message: types.Message):
        self.bot = bot
        self.file_name, self.user_name, self.user_id, self.file_id = self.get_param_message(message)

    @classmethod
    def get_param_message(cls, message: types.Message) -> tuple:
        """Из message достаёт параметры сообщения"""

        file_name = message.document.file_name
        user_name = message.chat.username
        user_id = message.chat.id
        file_id = message.document.file_id
        return file_name, user_name, user_id, file_id

    def get_telegram_file(self) -> str:
        logger.info(f"Get FILE {self.file_name} from USER {self.user_name} mit ID {self.user_id}")

        try:
            # Проверка формата файла на TXT
            if self.valid_file():
                self.bot.send_message(self.user_id, "Файл успешно загружен, веду обработку")

                # Получение файла из хранилиза
                downloaded_file = self.get_file()

                if len(downloaded_file) < settings.CONTROL_SIZE_FILE:
                    self.error_message("ERROR ZERO FILE")

                    return None

                # В случае если файл валиден возвращаем декодированный файл
                return downloaded_file.decode('utf-8')

            else:
                self.error_message("Формат файла должен быть TXT")
                return None
        except Exception as ex:
            logger.info(f"Error FILE {self.file_name} from USER {self.user_name} mit ID {self.user_id} - ERROR {ex}")
            self.error_message("Что-то пошло не так")
            return None

    def get_file(self) -> str:
        """Получает файл из хранилища telegram через встроенные методы бота"""

        file_info = self.bot.get_file(self.file_id)
        downloaded_file = self.bot.download_file(file_info.file_path)
        return downloaded_file

    def valid_file(self) -> bool:
        """Проверяет формат файла"""

        if self.file_name.endswith(".txt"):
            return True
        return False

    def success_message(self):
        """Событие успешной загрузки файла"""

        logger.info(f"Get FILE {self.file_name} from USER {self.user_name} mit ID {self.user_id}")
        self.bot.send_message(self.user_id, "Файл успешно обработан, данные внесены в таблицы")

    def error_message(self, mes: str):
        """Событие ошибки при обработке файла"""

        logger.info(f"Get FILE {self.file_name} from USER {self.user_name} "
                    f"mit ID {self.user_id} ERROR {mes}")
        self.bot.send_message(self.user_id, f"Возникла внутренняя ошибка {mes}, обратитесь к администратору")


class ConverterData():
    """преобразует данные для записи в БД и для записи в Google Sheets"""

    def __init__(self):
        self.ticket_list = []
        self.ticket_error_list = []
        self.amount = 0

    def import_session(self, file: str):
        """Чтение файла и разбиение строк в нём на два списка
        Первый список содержит обработанные для загрузки в Бд валидные строки
        Второй содержит строки с ошибками или не читаймые строки
        Пустые строки сразу отсеиваются, так как имеется проблема с загрузкой пустой строки в Google Sheets"""

        for line in file.split("\n"):
            try:
                # В валидных строках в вкачестве разделителя применяетс ','
                ticket = line.split(',')
                # Проверка строки на размер
                if len(ticket) < 4 or len(ticket) > 8:
                    if len(line) > 0:
                        self.ticket_error_list.append([line])
                    continue

                # Сборка параметров сессии такси из распличенных данных строки
                data = ticket[0] + ticket[1].split(" ")[1]
                # Приводим строку с датой в формат datetine через маску '%d.%m.%Y%H:%M' +
                # добавляем timezone для корректной записи в БД
                data_correct = datetime.strptime(data, '%d.%m.%Y%H:%M')
                data_correct_timezone = timezone.make_aware(data_correct, timezone.get_current_timezone())
                phone = ticket[1].split(" ")[-1]

                # Блок с валидаторами для параметров сессии, в случае невалидных данных
                # строка бракуется и добвляется в список невалидных строк + внутри каждого валидатора идёт проверка
                # размерности строки для отсечения пустых строк

                # Опционально  можно подключить проверку номера
                # if not re.fullmatch(r'^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$', phone):
                #     if line != "":
                #       self.ticket_error_list.append(line)
                #     print("point2")
                #     continue

                if not ticket[-1].strip().isdigit():
                    if len(line) > 0:
                        self.ticket_error_list.append([line])
                    continue

                if re.fullmatch(r'\d+:\d+', ticket[-4]):
                    time_correct = datetime.strptime(ticket[-4], '%H:%M')
                else:
                    time_correct = None

                # Формируется list c корректными строками записанными в виде tuple - для последующей записи в БД
                ticket_correct = (data_correct_timezone, phone, time_correct, *ticket[-3:])
                self.ticket_list.append(ticket_correct)

            except Exception:
                """В случае исключения на строке она не будет потеряна а записна в ошибочные строки"""
                if len(line) > 0:
                    self.ticket_error_list.append([line])
                continue

    def upload_session(self, sheet: str):
        """Отвечает за запись валидных данных в БД"""
        list_session = []

        for ticket in self.ticket_list:
            """Разбирает до этого отвалидированные строки для записи в БД, 
            в случае неполадок производится фиксация строки в списке ошибочных для дальнейшей ручной обработки"""
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
        """Выгружает данные сессии для формирования list наполненного list для внесения их в Google Sheets"""

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
    """Организует подключение к API Google Sheets"""

    def __init__(self):
        self.client = self.get_client()
        self.sh = self.get_client().open_by_key(settings.GOOGLE_SHEETS_ID)

    @classmethod
    def get_client(cls):
        """Получение доступа к клиенту Google API"""

        scope = [settings.GOOGLE_API_SHEETS,
                 settings.GOOGLE_API_AUTH]
        # Для получения доступа к Google API используется файл с ключами
        file = path.join("data_filtering", settings.FILE_API_GOOGLE_KEY)
        credentials = ServiceAccountCredentials.from_json_keyfile_name(file, scope)
        client = gspread.authorize(credentials)
        return client

    def initial_sheet_google(self, name_sheet):
        """Создание новой пвры листов в Google Sheets
        Один для валидных данных, другой для записи бракованных строк"""

        # Создание 2 листов
        worksheet = self.sh.add_worksheet(title=name_sheet, rows=10000, cols=20)
        name_sheet_error = name_sheet + settings.ERROR_NAME_SHEET
        worksheet2 = self.sh.add_worksheet(title=name_sheet_error, rows=10000, cols=20)

        # Внесение в них колонтитулов
        worksheet.update(
            'A1',
            [["Дата", "Телефон", "Время", "Начальная точка", "Конечная точка", "Сумма"]],
            value_input_option='USER_ENTERED')
        worksheet2.update('A1', [["Ошибочные строки"]], value_input_option='USER_ENTERED')

    def upload_data_to_sheet(self, list_sessions: list, name: str, num_start_col: int) -> bool:
        """Загружает данные в указанный лист Google Sheets"""

        worksheet = self.sh.worksheet(str(name))
        # Загрузка указанного столбца из листа для получения данных о количестве строк уже записанных данных
        values_list = worksheet.col_values(num_start_col)

        # Определение начальной колонки
        start_col = settings.LATIN[num_start_col]
        amount_line = len(values_list)

        # Расчитывает диапазон ячеек для загрузки новых данных с учётом уже имеющихся в листе данных,
        # чтобы не перетереть их
        position = f"{start_col}{amount_line + 1}"
        print(position)
        try:
            worksheet.update(position, list_sessions, value_input_option='USER_ENTERED')
            col2 = settings.LATIN[len(list_sessions[0]) + num_start_col]

            # Как дополнительный маркер в начале и конце загруженных данных добавляется метка
            position_start_line = f"{col2}{amount_line}"
            print(position_start_line)
            worksheet.update(position_start_line, "Начало сессии записи", value_input_option='USER_ENTERED')

            position_end_line = f"{col2}{amount_line + len(list_sessions)}"
            print(position_end_line)
            worksheet.update(position_end_line, "Конец сессии записи", value_input_option='USER_ENTERED')
        except Exception as ex:
            logger.info(f"Error load str in Google Sheets, error {ex}")
            return False
        return True



