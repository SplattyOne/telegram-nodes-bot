from telegram import ParseMode, Update
from telegram.ext import CallbackContext

from tgbot.handlers.onboarding import static_text
from tgbot.handlers.admin import static_text as static_text_admin
from tgbot.handlers.utils.info import extract_user_data_from_update
from tgbot.models import User
from tgbot.handlers.onboarding.keyboards import make_keyboard_for_start_command

from nodes.logic import check_nodes_cached as check_cached, check_nodes_now as check_now, list_nodes, create_user_node, delete_user_node


def command_start(update: Update, context: CallbackContext) -> None:
    u, created = User.get_user_and_created(update, context)

    if created:
        text = static_text.start_created.format(first_name=u.first_name)
    else:
        text = static_text.start_not_created.format(first_name=u.first_name)
    update.message.reply_text(text=text,
                              reply_markup=make_keyboard_for_start_command())


def check_nodes_now(update: Update, context: CallbackContext) -> None:
    u = User.get_user(update, context)
    if not u.is_admin:
        context.bot.edit_message_text(
            text=static_text_admin.only_for_admins,
            chat_id=update.callback_query.message.chat.id,
            message_id=update.callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        return

    user_id = u.user_id
    context.bot.edit_message_text(
        text=static_text.loading,
        chat_id=update.callback_query.message.chat.id,
        message_id=update.callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )
    text = check_now(user_id)
    context.bot.edit_message_text(
        text=text,
        chat_id=update.callback_query.message.chat.id,
        message_id=update.callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )


def check_nodes_now_cmd(update: Update, context: CallbackContext) -> None:
    u = User.get_user(update, context)
    if not u.is_admin:
        update.message.reply_text(static_text_admin.only_for_admins)
        return

    user_id = u.user_id
    update.message.reply_text(text=static_text.loading, parse_mode=ParseMode.HTML)
    text = check_now(user_id)
    update.message.reply_text(text=text, parse_mode=ParseMode.HTML)


def check_nodes_cached(update: Update, context: CallbackContext) -> None:
    u = User.get_user(update, context)
    if not u.is_admin:
        context.bot.edit_message_text(
            text=static_text_admin.only_for_admins,
            chat_id=update.callback_query.message.chat.id,
            message_id=update.callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        return

    user_id = u.user_id
    text = check_cached(user_id)
    context.bot.edit_message_text(
        text=text,
        chat_id=update.callback_query.message.chat.id,
        message_id=update.callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )


def check_nodes_cached_cmd(update: Update, context: CallbackContext) -> None:
    u = User.get_user(update, context)
    if not u.is_admin:
        update.message.reply_text(static_text_admin.only_for_admins)
        return

    user_id = u.user_id
    text = check_cached(user_id)
    update.message.reply_text(text=text, parse_mode=ParseMode.HTML)


def list_nodes_now(update: Update, context: CallbackContext) -> None:
    print(update)
    u = User.get_user(update, context)
    if not u.is_admin:
        context.bot.edit_message_text(
            text=static_text_admin.only_for_admins,
            chat_id=update.callback_query.message.chat.id,
            message_id=update.callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        return

    user_id = u.user_id
    text = list_nodes(user_id)
    context.bot.edit_message_text(
        text=text,
        chat_id=update.callback_query.message.chat.id,
        message_id=update.callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )


def list_nodes_now_cmd(update: Update, context: CallbackContext) -> None:
    u = User.get_user(update, context)
    if not u.is_admin:
        update.message.reply_text(static_text_admin.only_for_admins)
        return

    user_id = u.user_id
    text = list_nodes(user_id)
    update.message.reply_text(text=text, parse_mode=ParseMode.HTML)


def delete_node_checker(update: Update, context: CallbackContext) -> None:
    u = User.get_user(update, context)
    if not u.is_admin:
        context.bot.edit_message_text(
            text=static_text_admin.only_for_admins,
            chat_id=update.callback_query.message.chat.id,
            message_id=update.callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        return

    text = static_text.delete_checker_support_text
    context.bot.edit_message_text(
        text=text,
        chat_id=update.callback_query.message.chat.id,
        message_id=update.callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )


def delete_node_checker_cmd(update: Update, context: CallbackContext) -> None:
    u = User.get_user(update, context)
    if not u.is_admin:
        update.message.reply_text(static_text_admin.only_for_admins)
        return

    user_id = u.user_id
    new_node_data = update.message.text.split(' ')
    if len(new_node_data) != 2:
        update.message.reply_text(text=static_text.delete_checker_wrong_len_text, parse_mode=ParseMode.HTML)
        return
    (cmd, node_number) = new_node_data
    update.message.reply_text(text=delete_user_node(user_id, node_number), parse_mode=ParseMode.HTML)


def add_node_checker(update: Update, context: CallbackContext) -> None:
    u = User.get_user(update, context)
    if not u.is_admin:
        context.bot.edit_message_text(
            text=static_text_admin.only_for_admins,
            chat_id=update.callback_query.message.chat.id,
            message_id=update.callback_query.message.message_id,
            parse_mode=ParseMode.HTML
        )
        return

    text = static_text.add_checker_support_text
    context.bot.edit_message_text(
        text=text,
        chat_id=update.callback_query.message.chat.id,
        message_id=update.callback_query.message.message_id,
        parse_mode=ParseMode.HTML
    )

def add_node_checker_cmd(update: Update, context: CallbackContext) -> None:
    u = User.get_user(update, context)
    if not u.is_admin:
        update.message.reply_text(static_text_admin.only_for_admins)
        return

    user_id = u.user_id
    new_node_data = update.message.text.split(' ')
    if len(new_node_data) == 4:
        node_type = new_node_data[1]
        node_ip = new_node_data[2]
        node_port = new_node_data[3]
        update.message.reply_text(text=create_user_node(user_id, node_type, node_ip, node_port=node_port), parse_mode=ParseMode.HTML)
    elif len(new_node_data) >= 5 and len(new_node_data) <=7:
        node_type = new_node_data[1]
        node_ip = new_node_data[2]
        ssh_username = new_node_data[3]
        ssh_password = new_node_data[4]
        screen_name = new_node_data[5] if len(new_node_data) > 5 else None
        sudo_flag = new_node_data[6] if len(new_node_data) > 6 else False
        update.message.reply_text(text=create_user_node(user_id, node_type, node_ip, screen_name=screen_name, \
            ssh_username=ssh_username, ssh_password=ssh_password, sudo_flag=sudo_flag), parse_mode=ParseMode.HTML)
    else:
        update.message.reply_text(text=static_text.add_checker_wrong_len_text, parse_mode=ParseMode.HTML)
