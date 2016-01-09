# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('request_token', '0002_auto_20151227_1428'),
    ]

    operations = [
        migrations.AddField(
            model_name='requesttoken',
            name='scope',
            field=models.CharField(default='', help_text=b'Label used to match request to view function in decorator.', max_length=100),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='requesttoken',
            name='expiration_time',
            field=models.DateTimeField(help_text=b'Token will expire at this time (raises ExpiredSignatureError).', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='requesttoken',
            name='issued_at',
            field=models.DateTimeField(help_text=b'Time the token was created (set in the initial save).', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='requesttoken',
            name='max_uses',
            field=models.IntegerField(default=1, help_text=b'The maximum number of times the token can be used.'),
        ),
        migrations.AlterField(
            model_name='requesttoken',
            name='not_before_time',
            field=models.DateTimeField(help_text=b'Token cannot be used before this time (raises ImmatureSignatureError).', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='requesttoken',
            name='used_to_date',
            field=models.IntegerField(default=0, help_text=b'Number of times the token has been used to date (raises MaxUseError).'),
        ),
        migrations.AlterField(
            model_name='requesttoken',
            name='user',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, help_text=b'Intended recipient of the JWT (can be used by anyone if not set).', null=True),
        ),
    ]
