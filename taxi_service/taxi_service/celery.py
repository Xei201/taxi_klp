from __future__ import absolute_import, unicode_literals
import os

from celery import Celery
from celery.schedules import crontab

# from data_filtering.models import Profile
# taxi_service
# celery -A taxi_service worker --loglevel=info
# celery -A taxi_service flower --loglevel=info
#
# celery -A taxi_service beat --loglevel=info

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taxi_service.settings')

app = Celery('taxi_service')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.enable_utc = False

app.conf.update(timezone='UTC')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'send-tg-mail-every-day': {
        'task': 'data_filtering.tasks.constant_message_task',
        'schedule': crontab(minute='*/2')
    },
    'upload_taxi_session_in_bd': {
        'task': 'data_filtering.tasks.beat_upload_bd',
        'schedule': crontab(minute='*/3')
    }
}

# 'schedule': crontab(minute=0, hour='*/24')
