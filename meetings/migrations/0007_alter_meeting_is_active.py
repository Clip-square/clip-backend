# Generated by Django 5.1.3 on 2024-11-29 06:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meetings', '0006_alter_meeting_creator_alter_meeting_is_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='meeting',
            name='is_active',
            field=models.BooleanField(blank=True, default=True),
        ),
    ]
