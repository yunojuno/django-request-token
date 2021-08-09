"""
Truncate the request token log table.

This command should be run on a schedule if you wish to control the size
of the log table. You can control truncation using either count - the
max number of rows to retain, or date - so that logs are only kept for a
period of time.

"""
from argparse import ArgumentParser
from datetime import datetime, timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Min
from django.utils.timezone import now as tz_now

from request_token.models import RequestTokenLog


def get_timestamp_from_count(count: int) -> datetime:
    """
    Return timestamp of nth record where n=count.

    This function will always return a datetime, even if there are no
    records - defaults to datetime.min.

    """
    if not count:
        return datetime.min
    return (
        RequestTokenLog.objects.order_by("-id")[:count]
        .aggregate(min_timestamp=Min("timestamp"))
        .get("min_timestamp")
    ) or datetime.min


class Command(BaseCommand):

    help = "Truncate request token logs."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--max-count",
            type=int,
            dest="count",
            help="The maximum number of records to retain",
        )
        parser.add_argument(
            "--max-days",
            type=int,
            dest="days",
            help="The maximum number of days to retain records",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write("Truncating request token log records:")
        count = options.get("count")
        days = options.get("days")
        t1 = t2 = datetime.min
        if count:
            self.stdout.write(f"-> Retaining last {count} request token log records")
            t1 = get_timestamp_from_count(count)
        if days:
            self.stdout.write(
                f"-> Retaining last {days} days' request token log records"
            )
            t2 = tz_now() - timedelta(days=days)
        timestamp = max(t1, t2)
        if timestamp == datetime.min:
            self.stdout.write("-> No records available for truncation")
            return
        self.stdout.write(f"-> Truncating request token log records from {timestamp}")
        records = RequestTokenLog.objects.filter(timestamp__lt=timestamp)
        self.stdout.write(f"-> Truncating {records.count()} request token log records.")
        records.delete()
