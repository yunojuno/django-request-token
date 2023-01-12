from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("request_token", "0003_auto_20151229_1105")]

    operations = [migrations.RemoveField(model_name="requesttoken", name="target_url")]
