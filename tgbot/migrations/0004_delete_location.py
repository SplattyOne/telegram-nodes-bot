# Generated by Django 3.2.13 on 2022-04-22 19:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tgbot', '0003_rm_unused_fields'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Location',
        ),
    ]
