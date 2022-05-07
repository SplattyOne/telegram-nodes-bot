"""
    Celery node tasks.
"""

from dtb.celery import app
from celery.utils.log import get_task_logger

from nodes.logic import check_nodes_now, check_nodes_cached
from tgbot.models import User
from tgbot.handlers.broadcast_message.utils import _send_message

logger = get_task_logger(__name__)


@app.task(ignore_result=True)
def check_nodes_task() -> None:
    """ It's used to check all nodes status """
    logger.info(f"Going to check all nodes status")

    for user in User.objects.all():
        try:
            check_nodes_now(user.user_id, send_changes=True)
            logger.info(f"All node for user {user.user_id} checked")
        except Exception as e:
            logger.error(f"Failed to check nodes for {user.user_id}, reason: {e}")

    logger.info("All nodes check finished!")


@app.task(ignore_result=True)
def send_nodes_status_task() -> None:
    """ It's used to send all nodes status to users """
    logger.info(f"Going to send all nodes status")

    for user in User.objects.all():
        try:
            nodes_statuses = check_nodes_cached(user.user_id)
            _send_message(user_id=user.user_id, text=nodes_statuses)
            logger.info(f"Status for user {user.user_id} checked")
            #
            logger.info(f"Status for user {user.user_id} sent")
        except Exception as e:
            logger.error(f"Failed to check nodes for {user.user_id}, reason: {e}")

    logger.info("All nodes statuses sent!")
