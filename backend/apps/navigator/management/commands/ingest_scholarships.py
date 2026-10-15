"""Explicit, persistent vector indexing command."""

import time

from core.corpus import fingerprint
from core.rag.documents import content_hash, prepare_documents
from core.rag.embeddings import embed_documents, model_name
from core.rag.retrieval import index_dir
from core.rag.vector_store import FAISSVectorStore
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.navigator.models import ScholarshipChunk


class Command(BaseCommand):
    help = "Prepare provenance-preserving chunks, embed, and atomically persist FAISS."

    def handle(self, *args, **options):
        started = time.perf_counter()
        call_command("seed_scholarships")
        chunks = prepare_documents()
        # Only ingestion may download/build a missing model/index.
        vectors = embed_documents([c.scheme_name + " " + c.section + " " + c.text for c in chunks])
        store = FAISSVectorStore(vectors, chunks)
        with transaction.atomic():
            ScholarshipChunk.objects.all().delete()
            ScholarshipChunk.objects.bulk_create(
                [
                    ScholarshipChunk(
                        chunk_id=c.chunk_id,
                        scholarship_id=c.scheme_id,
                        section=c.section,
                        content_hash=content_hash(c),
                    )
                    for c in chunks
                ]
            )
            store.save(
                index_dir(),
                {
                    "corpus_hash": fingerprint(),
                    "embedding_model": model_name(),
                    "dimension": vectors.shape[1],
                },
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Indexed {len(chunks)} chunks in {time.perf_counter() - started:.2f}s."
            )
        )
