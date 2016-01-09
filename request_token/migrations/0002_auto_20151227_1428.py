# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('request_token', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='requesttokenlog',
            name='status_code',
            field=models.IntegerField(help_text=b'Response status code associated with this use of the token.', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='requesttoken',
            name='data',
            field=models.TextField(default=b'{}', help_text=b'Custom data (JSON) added to the default payload.', max_length=1000, blank=True),
        ),
        migrations.AlterField(
            model_name='requesttokenlog',
            name='timestamp',
            field=models.DateTimeField(help_text=b'Time the request was logged.', blank=True),
        ),
    ]
