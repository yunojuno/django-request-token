# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("request_token", "0004_remove_requesttoken_target_url")]

    operations = [
        migrations.AddField(
            model_name="requesttoken",
            name="login_mode",
            field=models.CharField(
                default="None",
                help_text="How should the request be authenticated?",
                max_length=10,
                choices=[
                    ("None", "Do not authenticate"),
                    ("Request", "Authenticate a single request"),
                    ("Session", "Authenticate for the entire session"),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="requesttoken",
            name="data",
            field=models.TextField(
                default="{}",
                help_text="Custom data add to the token, but not encoded (must be fetched from DB).",
                max_length=1000,
                blank=True,
            ),
        ),
    ]
