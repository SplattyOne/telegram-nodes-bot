from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from tgbot.handlers.onboarding.manage_data import ADD_CHECKER_BUTTON, DELETE_CHECKER_BUTTON, \
    CHECK_NOW_BUTTON
from tgbot.handlers.onboarding.static_text import add_checker_button_text, delete_checker_button_text, \
    check_now_button_text


def make_keyboard_for_start_command() -> InlineKeyboardMarkup:
    buttons = [[
        InlineKeyboardButton(check_now_button_text, callback_data=f'{CHECK_NOW_BUTTON}'),
        InlineKeyboardButton(add_checker_button_text, callback_data=f'{ADD_CHECKER_BUTTON}'),
        InlineKeyboardButton(delete_checker_button_text, callback_data=f'{DELETE_CHECKER_BUTTON}')
    ]]

    return InlineKeyboardMarkup(buttons)
