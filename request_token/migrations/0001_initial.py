# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RequestToken',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('target_url', models.CharField(help_text=b'The target endpoint.', max_length=200)),
                ('expiration_time', models.DateTimeField(help_text=b'DateTime at which this token expires.', null=True, blank=True)),
                ('not_before_time', models.DateTimeField(help_text=b'DateTime before which this token is invalid.', null=True, blank=True)),
                ('data', models.TextField(help_text=b'Custom data (JSON) added to the default payload.', max_length=1000, blank=True)),
                ('issued_at', models.DateTimeField(help_text=b'Time the token was created, set in the initial save.', null=True, blank=True)),
                ('max_uses', models.IntegerField(default=1, help_text=b'Cap on the number of times the token can be used, defaults to 1 (single use).')),
                ('used_to_date', models.IntegerField(default=0, help_text=b'Denormalised count of the number times the token has been used.')),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, help_text=b'Intended recipient of the JWT.', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='RequestTokenLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('user_agent', models.TextField(help_text=b'User-agent of client used to make the request.', blank=True)),
                ('client_ip', models.CharField(help_text=b'Client IP of device used to make the request.', max_length=15)),
                ('timestamp', models.DateTimeField(help_text=b'Time the request was logged.')),
                ('token', models.ForeignKey(help_text=b'The RequestToken that was used.', to='request_token.RequestToken')),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, help_text=b'The user who made the request (None if anonymous).', null=True)),
            ],
        ),
    ]
