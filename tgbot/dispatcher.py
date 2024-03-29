"""
    Telegram event handlers
"""
import logging
import sys
from typing import Dict

import telegram.error
from telegram import Bot, BotCommand, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, Dispatcher, \
    Updater

from dtb.celery import app  # event processing in async mode
from dtb.settings import DEBUG, TELEGRAM_TOKEN
from tgbot.handlers.admin import handlers as admin_handlers
from tgbot.handlers.onboarding import handlers as onboarding_handlers

# from tgbot.handlers.broadcast_message import handlers as broadcast_handlers
from tgbot.handlers.onboarding.manage_data import (
    ADD_CHECKER_BUTTON,
    CHECK_CACHED_BUTTON,
    CHECK_NOW_BUTTON,
    DELETE_CHECKER_BUTTON,
    LIST_CHECKERS_BUTTON,
)
from tgbot.handlers.utils import error

# from tgbot.handlers.broadcast_message.manage_data import CONFIRM_DECLINE_BROADCAST
# from tgbot.handlers.broadcast_message.static_text import broadcast_command


def setup_dispatcher(dp):
    """
    Adding handlers for events from Telegram
    """
    # onboarding
    dp.add_handler(CommandHandler("start", onboarding_handlers.command_start))
    dp.add_handler(CommandHandler("cached", onboarding_handlers.check_nodes_cached_cmd))
    dp.add_handler(CommandHandler("now", onboarding_handlers.check_nodes_now_cmd))
    dp.add_handler(CommandHandler("list", onboarding_handlers.list_nodes_now_cmd))
    dp.add_handler(CommandHandler("add", onboarding_handlers.add_node_checker_cmd))
    dp.add_handler(CommandHandler("delete", onboarding_handlers.delete_node_checker_cmd))

    # admin commands
    dp.add_handler(CommandHandler("admin", admin_handlers.admin))
    dp.add_handler(CommandHandler("stats", admin_handlers.stats))
    # dp.add_handler(CommandHandler('export_users', admin_handlers.export_users))

    # nodes
    dp.add_handler(CallbackQueryHandler(onboarding_handlers.check_nodes_now, pattern=f"^{CHECK_NOW_BUTTON}"))
    dp.add_handler(CallbackQueryHandler(onboarding_handlers.check_nodes_cached, pattern=f"^{CHECK_CACHED_BUTTON}"))
    dp.add_handler(CallbackQueryHandler(onboarding_handlers.list_nodes_now, pattern=f"^{LIST_CHECKERS_BUTTON}"))
    dp.add_handler(CallbackQueryHandler(onboarding_handlers.add_node_checker, pattern=f"^{ADD_CHECKER_BUTTON}"))
    dp.add_handler(CallbackQueryHandler(onboarding_handlers.delete_node_checker, pattern=f"^{DELETE_CHECKER_BUTTON}"))

    # secret level
    # dp.add_handler(CallbackQueryHandler(onboarding_handlers.secret_level, pattern=f"^{SECRET_LEVEL_BUTTON}"))

    # broadcast message
    # dp.add_handler(
    #     MessageHandler(Filters.regex(rf'^{broadcast_command}(/s)?.*'),
    #     broadcast_handlers.broadcast_command_with_message)
    # )
    # dp.add_handler(
    #     CallbackQueryHandler(broadcast_handlers.broadcast_decision_handler, pattern=f"^{CONFIRM_DECLINE_BROADCAST}")
    # )

    # files
    # dp.add_handler(MessageHandler(
    #     Filters.animation, files.show_file_id,
    # ))

    # handling errors
    dp.add_error_handler(error.send_stacktrace_to_tg_chat)

    # EXAMPLES FOR HANDLERS
    # dp.add_handler(MessageHandler(Filters.text, <function_handler>))
    # dp.add_handler(MessageHandler(
    #     Filters.document, <function_handler>,
    # ))
    # dp.add_handler(CallbackQueryHandler(<function_handler>, pattern="^r\d+_\d+"))
    # dp.add_handler(MessageHandler(
    #     Filters.chat(chat_id=int(TELEGRAM_FILESTORAGE_ID)),
    #     # & Filters.forwarded & (Filters.photo | Filters.video | Filters.animation),
    #     <function_handler>,
    # ))

    return dp


def run_pooling():
    """Run bot in pooling mode"""
    updater = Updater(TELEGRAM_TOKEN, use_context=True)

    dp = updater.dispatcher
    dp = setup_dispatcher(dp)

    bot_info = Bot(TELEGRAM_TOKEN).get_me()
    bot_link = "https://t.me/" + bot_info["username"]

    print(f"Pooling of '{bot_link}' started")
    # it is really useful to send '👋' emoji to developer
    # when you run local test
    # bot.send_message(text='👋', chat_id=<YOUR TELEGRAM ID>)

    updater.start_polling()
    updater.idle()


# Global variable - best way I found to init Telegram bot
bot = Bot(TELEGRAM_TOKEN)
try:
    TELEGRAM_BOT_USERNAME = bot.get_me()["username"]
except telegram.error.Unauthorized:
    logging.error("Invalid TELEGRAM_TOKEN.")
    sys.exit(1)


@app.task(ignore_result=True)
def process_telegram_event(update_json):
    update = Update.de_json(update_json, bot)
    dispatcher.process_update(update)


def set_up_commands(bot_instance: Bot) -> None:
    langs_with_commands: Dict[str, Dict[str, str]] = {
        "en": {
            "start": "Start bot 🚀",
            "cached": "Get all nodes statuses 🚀",
            "now": "Check all nodes statuses 🚀",
            "list": "List all nodes 📊",
            "add": "Add node for check 📊",
            "delete": "Delete node for check 📊",
            # 'stats': 'Statistics of bot 📊'
        },
        "ru": {
            "start": "Start bot 🚀",
            "cached": "Get all nodes statuses 🚀",
            "now": "Check all nodes statuses 🚀",
            "list": "List all nodes 📊",
            "add": "Add node for check 📊",
            "delete": "Delete node for check 📊",
            # 'stats': 'Statistics of bot 📊'
        },
    }

    bot_instance.delete_my_commands()
    for language_code in langs_with_commands:
        bot_instance.set_my_commands(
            language_code=language_code,
            commands=[
                BotCommand(command, description) for command, description in langs_with_commands[language_code].items()
            ],
        )


# WARNING: it's better to comment the line below in DEBUG mode.
# Likely, you'll get a flood limit control error, when restarting bot too often
set_up_commands(bot)

n_workers = 0 if DEBUG else 4
dispatcher = setup_dispatcher(Dispatcher(bot, update_queue=None, workers=n_workers, use_context=True))
