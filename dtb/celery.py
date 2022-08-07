import os
from celery import Celery
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dtb.settings')

app = Celery('dtb')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
app.conf.enable_utc = False

app.conf.beat_schedule = {
    'check-nodes-every-5-minutes': {
        'task': 'nodes.tasks.check_nodes_task',
        'schedule': crontab(minute='*/5'),  # change to `crontab(minute=0, hour=0)` if you want it to run daily at midnight
    },
    'send-nodes-at-9-00': {
        'task': 'nodes.tasks.send_nodes_status_task',
        'schedule': crontab(hour=9, minute=0),  # change to `crontab(minute=0, hour=0)` if you want it to run daily at midnight
    },
    'send-nodes-guru-updates-every-15-minutes': {
        'task': 'nodes.tasks.send_nodes_guru_updates',
        'schedule': crontab(minute='*/15'),  # change to `crontab(minute=0, hour=0)` if you want it to run daily at midnight
    },
}

    