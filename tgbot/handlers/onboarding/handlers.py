import datetime

from django.utils import timezone
from telegram import ParseMode, Update
from telegram.ext import CallbackContext

from tgbot.handlers.onboarding import static_text
from tgbot.handlers.utils.info import extract_user_data_from_update
from tgbot.models import User
from tgbot.handlers.onboarding.keyboards import make_keyboard_for_start_command

from nodes.logic import check_nodes, create_user_node, delete_user_node, NODE_TYPES


def command_start(update: Update, context: CallbackContext) -> None:
    u, created = User.get_user_and_created(update, context)

    if created:
        text = static_text.start_created.format(first_name=u.first_name)
    else:
        text = static_text.start_not_created.format(first_name=u.first_name)

    update.message.reply_text(text=text,
                              reply_markup=make_keyboard_for_start_command())


def check_nodes_now(update: Update, context: CallbackContext) -> None:
    # user_id = extract_user_data_from_update(update)['user_id']
    u = User.get_user(update, context)
    user_id = u.user_id
    text = check_nodes(user_id)

    context.bot.edit_message_text(
        text=text,
        chat_id=user_id,
        message_id=update.callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )


def check_nodes_now_cmd(update: Update, context: CallbackContext) -> None:
    # user_id = extract_user_data_from_update(update)['user_id']
    u = User.get_user(update, context)
    user_id = u.user_id
    text = check_nodes(user_id)

    update.message.reply_text(text=text, parse_mode=ParseMode.HTML)


def delete_node_checker(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)['user_id']
    text = static_text.delete_checker_support_text

    context.bot.edit_message_text(
        text=text,
        chat_id=user_id,
        message_id=update.callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )

def delete_node_checker_cmd(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)['user_id']
    new_node_data = update.message.text.split(' ')
    if len(new_node_data) != 2:
        update.message.reply_text(text=static_text.delete_checker_wrong_len_text, parse_mode=ParseMode.HTML)
        return

    (cmd, node_number) = new_node_data
    update.message.reply_text(text=delete_user_node(user_id, node_number), parse_mode=ParseMode.HTML)


def add_node_checker(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)['user_id']
    text = static_text.add_checker_support_text + f'\n{NODE_TYPES.keys()}'

    context.bot.edit_message_text(
        text=static_text.add_checker_support_text,
        chat_id=user_id,
        message_id=update.callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )

def add_node_checker_cmd(update: Update, context: CallbackContext) -> None:
    user_id = extract_user_data_from_update(update)['user_id']
    new_node_data = update.message.text.split(' ')
    if len(new_node_data) != 4:
        update.message.reply_text(text=static_text.add_checker_wrong_len_text, parse_mode=ParseMode.HTML)
        return
    
    (cmd, node_type, node_ip, node_port) = new_node_data
    update.message.reply_text(text=create_user_node(user_id, node_type, node_ip, node_port), parse_mode=ParseMode.HTML)
