# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('request_token', '0004_remove_requesttoken_target_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='requesttoken',
            name='login_mode',
            field=models.CharField(default=b'None', help_text=b'How should the request be authenticated?', max_length=10, choices=[(b'None', b'Do not authenticate'), (b'Request', b'Authenticate a single request'), (b'Session', b'Authenticate for the entire session')]),
        ),
        migrations.AlterField(
            model_name='requesttoken',
            name='data',
            field=models.TextField(default=b'{}', help_text=b'Custom data add to the token, but not encoded (must be fetched from DB).', max_length=1000, blank=True),
        ),
    ]
