# Generated by Django 3.2.13 on 2022-08-29 08:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nodes', '0009_nodesguru'),
    ]

    operations = [
        migrations.AddField(
            model_name='node',
            name='same_status_count',
            field=models.IntegerField(default=0),
        ),
    ]
