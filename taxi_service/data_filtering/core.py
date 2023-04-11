from datetime import datetime
import logging
import re
from django.db import transaction
from django.utils import timezone

from data_filtering.models import Profile, SessionTaxi

logger = logging.getLogger(__name__)


class ConverterData():

    @staticmethod
    def import_record(file: str):
        tiket_list = []
        tiket_error_list = []
        for line in file.split("\n"):
            try:
                tiket = line.split(',')

                if len(tiket) < 4:
                    tiket_error_list.append(tiket)
                    continue

                data = tiket[0] + tiket[1].split(" ")[1]

                data_correct = datetime.strptime(data, '%d.%m.%Y%H:%M')
                data_correct_timezone = timezone.make_aware(data_correct, timezone.get_current_timezone())
                phone = tiket[1].split(" ")[-1]
                if re.fullmatch(r'\d+:\d+', tiket[-4]):
                    time_correct = datetime.strptime(tiket[-4], '%H:%M')
                else:
                    time_correct = None

                tiket_correct = (data_correct_timezone, phone, time_correct, *tiket[-3:])
                tiket_list.append(tiket_correct)
            except Exception as ex:
                tiket_error_list.append(line)
                print("List bild", ex)
                continue
        return tiket_list

    @staticmethod
    @transaction.atomic
    def upload_session(tiket_list):
        profile = Profile.objects.get(id=1)
        list_session = []
        for tiket in tiket_list:
            try:
                list_session.append(SessionTaxi(
                    profile=profile,
                    date_session=tiket[0],
                    phone=tiket[1],
                    time=tiket[2],
                    starting_point=tiket[3],
                    end_point=tiket[4],
                    price=int(tiket[5]),
                ))
            except Exception as ex:
                print("Bulk bild", ex)
                continue
        SessionTaxi.objects.bulk_create(list_session)




