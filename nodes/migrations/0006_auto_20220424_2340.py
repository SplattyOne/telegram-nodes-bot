# Generated by Django 3.2.13 on 2022-04-24 20:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nodes', '0005_auto_20220424_1947'),
    ]

    operations = [
        migrations.AlterField(
            model_name='checkhistory',
            name='status',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='node',
            name='last_status',
            field=models.BooleanField(default=False),
        ),
    ]
