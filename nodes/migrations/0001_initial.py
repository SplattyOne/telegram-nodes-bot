# Generated by Django 3.2.13 on 2022-04-21 10:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tgbot', '0003_rm_unused_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Node',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('node_type', models.CharField(max_length=256)),
                ('node_ip', models.CharField(max_length=256)),
                ('node_port', models.CharField(max_length=256)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_checked', models.DateTimeField(blank=True, null=True)),
                ('last_status', models.CharField(blank=True, max_length=1024, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tgbot.user')),
            ],
        ),
        migrations.CreateModel(
            name='CheckHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('checked', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(max_length=1024)),
                ('node', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nodes.node')),
            ],
        ),
    ]
