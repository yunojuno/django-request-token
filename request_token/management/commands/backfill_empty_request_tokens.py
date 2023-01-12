from typing import Any

from django.core.management.base import BaseCommand

from request_token.models import RequestToken


class Command(BaseCommand):

    help = "Backfill empty RequestToken.token fields."

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write("Backfilling empty tokens")
        records = RequestToken.objects.filter(token="")  # noqa: S106
        self.stdout.write(f"-> Found {records.count()} empty tokens.")
        for token in records.order_by("-id").iterator():
            self.stdout.write(f"-> Updating {token}")
            token.update_token()
