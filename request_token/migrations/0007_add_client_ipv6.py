# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models

# gets around "django.db.utils.ProgrammingError: column "client_ip" cannot be cast automatically to type inet"
ALTER_SQL = (
    "ALTER TABLE request_token_requesttokenlog "
    "ALTER COLUMN client_ip TYPE inet "
    "USING client_ip::inet;"
)

# if we are using postgresql then we use the ALTER_FIELD version
POSTGRES = (
    settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql_psycopg2"
)


class Migration(migrations.Migration):

    dependencies = [("request_token", "0006_auto_20161104_1428")]

    alter_field = migrations.AlterField(
        model_name="requesttokenlog",
        name="client_ip",
        field=models.GenericIPAddressField(
            help_text="Client IP of device used to make the request.",
            null=True,
            unpack_ipv4=True,
            blank=True,
        ),
    )

    run_sql = migrations.RunSQL(
        ALTER_SQL,  # run the SQL to alter the column
        None,  # reverse_sql - none available
        state_operations=[alter_field],
    )

    operations = [run_sql] if POSTGRES else [alter_field]
