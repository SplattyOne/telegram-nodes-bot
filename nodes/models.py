from django.db import models

from tgbot.models import User


class Node(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    node_type = models.CharField(max_length=256)
    node_ip = models.CharField(max_length=256)
    node_port = models.CharField(max_length=256, null=True, blank=True)
    ssh_username = models.CharField(max_length=256, null=True, blank=True)
    ssh_password = models.CharField(max_length=256, null=True, blank=True)
    screen_name = models.CharField(max_length=256, null=True, blank=True)
    sudo_flag = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    last_checked = models.DateTimeField(null=True, blank=True)
    last_status = models.BooleanField(default=False)
    last_status_text = models.CharField(null=True, blank=True, max_length=2048)
    last_reward_value = models.IntegerField(default=0)


class CheckHistory(models.Model):
    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    checked = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=False)
    status_text = models.CharField(null=True, blank=True, max_length=2048)
    reward_value = models.IntegerField(default=0)
