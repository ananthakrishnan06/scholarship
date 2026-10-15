"""Explicit retention cleanup for private session data."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.navigator.models import UserSession


class Command(BaseCommand):
    help = "Delete inactive sessions older than the supplied retention period."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)

    def handle(self, *args, **options):
        if options["days"] < 1:
            raise ValueError("Retention days must be positive.")
        count, _ = UserSession.objects.filter(
            updated_at__lt=timezone.now() - timedelta(days=options["days"])
        ).delete()
        self.stdout.write(f"Deleted {count} retained objects.")
