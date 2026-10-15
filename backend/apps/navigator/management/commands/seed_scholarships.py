from core.corpus import fingerprint, records
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.navigator.models import Scholarship


class Command(BaseCommand):
    help = "Seed operational scholarship metadata without copying the corpus."

    @transaction.atomic
    def handle(self, *args, **options):
        for scheme in records():
            Scholarship.objects.update_or_create(
                scheme_id=scheme["scheme_id"],
                defaults={
                    "name": scheme["name"],
                    "corpus_hash": fingerprint(),
                    "original_record_key": scheme["provenance"]["original_record_key"],
                },
            )
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(records())} scholarship records."))
