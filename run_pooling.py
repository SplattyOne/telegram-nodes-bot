import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dtb.settings")
django.setup()

from tgbot.dispatcher import run_pooling  # noqa

if __name__ == "__main__":
    run_pooling()
