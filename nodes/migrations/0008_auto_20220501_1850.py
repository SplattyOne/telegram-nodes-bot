# Generated by Django 3.2.13 on 2022-05-01 15:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nodes', '0007_auto_20220501_1836'),
    ]

    operations = [
        migrations.AlterField(
            model_name='checkhistory',
            name='reward_value',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='node',
            name='last_reward_value',
            field=models.FloatField(default=0),
        ),
    ]
