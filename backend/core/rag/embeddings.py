"""Configurable CPU sentence-transformer embeddings with bounded query caching."""

import os
import threading
from functools import lru_cache

import numpy as np

MODEL_DEFAULT = "sentence-transformers/all-MiniLM-L6-v2"
_lock = threading.Lock()


def model_name() -> str:
    return os.getenv("EMBEDDING_MODEL", MODEL_DEFAULT)


@lru_cache(maxsize=2)
def get_model(name, allow_download=False):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(name, device="cpu", local_files_only=not allow_download)


def embed_documents(texts: list[str]) -> np.ndarray:
    with _lock:
        return np.asarray(
            get_model(model_name(), allow_download=True).encode(
                texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32
            ),
            dtype="float32",
        )


@lru_cache(maxsize=256)
def _embed_query(name: str, text: str):
    with _lock:
        return np.asarray(
            get_model(name).encode([text], normalize_embeddings=True, show_progress_bar=False),
            dtype="float32",
        )


def embed_query(text: str):
    return _embed_query(model_name(), text).copy()


def embed_local_texts(texts: list[str]) -> np.ndarray:
    """Embed classifier descriptions locally; request handling never downloads models."""
    with _lock:
        return np.asarray(
            get_model(model_name()).encode(
                texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32
            ),
            dtype="float32",
        )
