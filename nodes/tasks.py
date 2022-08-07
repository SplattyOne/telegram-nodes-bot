"""
    Celery node tasks.
"""
import json

from dtb.celery import app
from celery.utils.log import get_task_logger

from nodes.logic import check_nodes_now, check_nodes_cached
from nodes.nodesguru import check_nodes_guru_updates
from tgbot.models import User
from tgbot.handlers.broadcast_message.utils import _send_message

logger = get_task_logger(__name__)


@app.task(ignore_result=True)
def check_nodes_task() -> None:
    """ It's used to check all nodes status """
    logger.info(f"Going to check all nodes status")

    for user in User.objects.all():
        try:
            logger.info(f'Checking for {user.user_id}')
            check_nodes_now(user.user_id, send_changes=True)
            logger.info(f"All nodes for user {user.user_id} checked")
        except Exception as e:
            logger.error(f"Failed to check nodes, reason: {e}")

    logger.info("All nodes check finished!")


@app.task(ignore_result=True)
def send_nodes_status_task() -> None:
    """ It's used to send all nodes status to users """
    logger.info(f"Going to send all nodes status")

    for user in User.objects.all():
        try:
            logger.info(f'Checking for {user.user_id}')
            nodes_statuses = check_nodes_cached(user.user_id)
            logger.info(f"Status for user {user.user_id} checked")
            _send_message(user_id=user.user_id, text=nodes_statuses)
            logger.info(f"Status for user {user.user_id} sent")
        except Exception as e:
            logger.error(f"Failed to check nodes, reason: {e}")

    logger.info("All nodes statuses sent!")


@app.task(ignore_result=True)
def send_nodes_guru_updates() -> None:
    """ It's used to send NodesGuru site updates """
    logger.info(f"Going to send NodesGuru updates")
    NODES_GURU_CHAT_ID = -777355318

    try:
        deviations = check_nodes_guru_updates()
        if len(deviations):
            missed_deviations = deviations.get('missed', [])
            new_deviations = deviations.get('new', [])
            logger.info(f"Found deviations missed nodes {len(missed_deviations)}, new nodes {len(new_deviations)}, send it in chat")
            _send_message(user_id=NODES_GURU_CHAT_ID, text=f'Missed nodes: {json.dumps(missed_deviations)}')
            _send_message(user_id=NODES_GURU_CHAT_ID, text=f'New nodes: {json.dumps(new_deviations)}')
        else:
            logger.info(f"No deviations - nothing to send")
    except Exception as e:
        logger.error(f"Failed to check NodesGuru for updates, reason: {e}")
