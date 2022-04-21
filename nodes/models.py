from django.db import models

from tgbot.models import User


class Node(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    node_type = models.CharField(max_length=256)
    node_ip = models.CharField(max_length=256)
    node_port = models.CharField(max_length=256)
    created = models.DateTimeField(auto_now_add=True)
    last_checked = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(null=True, blank=True, max_length=1024)


class CheckHistory(models.Model):
    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    checked = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=1024)
