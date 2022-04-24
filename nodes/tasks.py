"""
    Celery node tasks.
"""

from dtb.celery import app
from celery.utils.log import get_task_logger

from nodes.logic import check_nodes
from tgbot.models import User

logger = get_task_logger(__name__)


@app.task(ignore_result=True)
def check_nodes_task() -> None:
    """ It's used to check all nodes status """
    logger.info(f"Going to check all nodes status")

    for user in User.objects.all():
        try:
            check_nodes(user.user_id)
            logger.info(f"All node for user {user.user_id} checked")
        except Exception as e:
            logger.error(f"Failed to check nodes for {user.user_id}, reason: {e}")

    logger.info("All nodes check finished!")


