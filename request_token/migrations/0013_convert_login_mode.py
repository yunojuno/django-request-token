import logging

from django.db import migrations

logger = logging.getLogger(__name__)


MODE_MAPPINGS = (
    ("None", "NONE"),
    ("Request", "REQUEST"),
    ("Session", "SESSION"),
)


def convert_login_mode(klass, before, after):
    tokens = klass.objects.filter(login_mode=before)
    count = tokens.count()
    logger.info("Updating %s tokens from '%s' to '%s'", count, before, after)
    tokens.update(login_mode=after)


def forwards(apps, schema_editor):
    RequestToken = apps.get_model("request_token", "RequestToken")
    for before, after in MODE_MAPPINGS:
        convert_login_mode(RequestToken, before, after)


def backwards(apps, schema_editor):
    RequestToken = apps.get_model("request_token", "RequestToken")
    for after, before in MODE_MAPPINGS:
        convert_login_mode(RequestToken, before, after)


class Migration(migrations.Migration):

    dependencies = [
        ("request_token", "0012_update_login_mode"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
