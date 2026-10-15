"""Replaceable vector interface; FAISS persistence uses no pickle."""

import hashlib
import json
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from core.rag.documents import Chunk


class VectorStore(ABC):
    @abstractmethod
    def search(
        self, query: np.ndarray, top_k: int, filters: dict | None = None
    ) -> list[tuple[Chunk, float]]:
        """Search only documents satisfying the scheme/section metadata filter."""

    @abstractmethod
    def save(self, directory: Path, metadata: dict):
        """Persist a complete version and atomically switch the current pointer."""


class FAISSVectorStore(VectorStore):
    def __init__(self, vectors: np.ndarray, chunks: list[Chunk]):
        import faiss

        self.vectors = np.ascontiguousarray(vectors, dtype="float32")
        if len(chunks) != len(vectors) or not len(chunks):
            raise ValueError("Embedding count must match nonempty chunk count.")
        self.chunks = chunks
        self.index = faiss.IndexFlatIP(self.vectors.shape[1])
        self.index.add(self.vectors)

    def search(self, query, top_k, filters=None):
        import faiss

        if top_k < 1:
            raise ValueError("top_k must be positive.")
        candidates = [
            i
            for i, c in enumerate(self.chunks)
            if not filters or all(getattr(c, key) in value for key, value in filters.items())
        ]
        if not candidates:
            return []
        # Metadata filtering happens BEFORE nearest-neighbor search.
        subset = faiss.IndexFlatIP(self.vectors.shape[1])
        subset.add(self.vectors[candidates])
        scores, positions = subset.search(
            np.ascontiguousarray(query, dtype="float32"), min(top_k, len(candidates))
        )
        return [
            (self.chunks[candidates[int(i)]], float(score))
            for i, score in zip(positions[0], scores[0])
            if i >= 0
        ]

    def save(self, directory, metadata):
        import faiss

        directory.mkdir(parents=True, exist_ok=True)
        version = uuid.uuid4().hex
        target = directory / version
        target.mkdir()
        faiss.write_index(self.index, str(target / "vectors.faiss"))
        chunks_path = target / "chunks.json"
        chunks_path.write_text(json.dumps([c.to_dict() for c in self.chunks]), encoding="utf-8")
        metadata = dict(
            metadata,
            chunks_sha256=hashlib.sha256(chunks_path.read_bytes()).hexdigest(),
            index_sha256=hashlib.sha256((target / "vectors.faiss").read_bytes()).hexdigest(),
            chunk_count=len(self.chunks),
        )
        (target / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        pointer = directory / (version + ".tmp")
        pointer.write_text(version, encoding="utf-8")
        os.replace(pointer, directory / "CURRENT")

    @classmethod
    def load(cls, directory: Path):
        import faiss

        version = (directory / "CURRENT").read_text(encoding="utf-8").strip()
        if len(version) != 32 or any(c not in "0123456789abcdef" for c in version):
            raise ValueError("Invalid index version pointer.")
        target = directory / version
        metadata = json.loads((target / "metadata.json").read_text(encoding="utf-8"))
        for file, key in [("chunks.json", "chunks_sha256"), ("vectors.faiss", "index_sha256")]:
            if hashlib.sha256((target / file).read_bytes()).hexdigest() != metadata[key]:
                raise ValueError("Vector index integrity check failed.")
        index = faiss.read_index(str(target / "vectors.faiss"))
        chunks = [
            Chunk(**c) for c in json.loads((target / "chunks.json").read_text(encoding="utf-8"))
        ]
        if index.ntotal != len(chunks):
            raise ValueError("Index and chunk counts disagree.")
        return cls(index.reconstruct_n(0, index.ntotal), chunks), metadata
