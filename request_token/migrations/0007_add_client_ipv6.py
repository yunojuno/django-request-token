# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('request_token', '0006_auto_20161104_1428'),
    ]

    operations = [
        migrations.AlterField(
            model_name='requesttokenlog',
            name='client_ip',
            field=models.GenericIPAddressField(help_text=b'Client IP of device used to make the request.', null=True, unpack_ipv4=True, blank=True),
        ),
    ]
