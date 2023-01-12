from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("request_token", "0005_auto_20160103_1655")]

    operations = [
        migrations.AlterModelOptions(
            name="requesttokenlog",
            options={
                "verbose_name": "Token use",
                "verbose_name_plural": "Token use logs",
            },
        )
    ]
