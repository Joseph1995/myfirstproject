"""
TF-IDF based in-memory knowledge base for multi-document retrieval.

Documents are chunked and indexed with scikit-learn's TfidfVectorizer.
Queries are answered by returning the most cosine-similar chunks.
"""

import re
from typing import Dict, List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Chunk configuration
_CHUNK_SIZE = 600
_CHUNK_OVERLAP = 100
# Minimum cosine-similarity score to include a result (filters near-zero noise)
_MIN_SCORE = 0.01


def _chunk_text(text: str) -> List[str]:
    """Split *text* into overlapping chunks of roughly _CHUNK_SIZE characters."""
    if not text.strip():
        return []

    # Split on blank lines first to keep logical paragraphs together
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 1 <= _CHUNK_SIZE:
            current = (current + "\n" + para).strip() if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > _CHUNK_SIZE:
                # Large paragraph: split word-by-word
                words = para.split()
                current = ""
                for word in words:
                    if len(current) + len(word) + 1 <= _CHUNK_SIZE:
                        current = (current + " " + word).strip()
                    else:
                        if current:
                            chunks.append(current)
                        current = word
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks


class KnowledgeBase:
    """In-memory TF-IDF index over chunked document text."""

    def __init__(self) -> None:
        self._chunks: List[str] = []
        self._sources: List[str] = []   # one source (filename) per chunk
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._dirty = True

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def add_document(self, text: str, filename: str) -> int:
        """Index *text* from *filename*.  Returns the number of chunks added."""
        new_chunks = _chunk_text(text)
        if not new_chunks:
            return 0
        self._chunks.extend(new_chunks)
        self._sources.extend([filename] * len(new_chunks))
        self._dirty = True
        return len(new_chunks)

    def remove_document(self, filename: str) -> None:
        """Remove all chunks that belong to *filename*."""
        pairs = [
            (c, s)
            for c, s in zip(self._chunks, self._sources)
            if s != filename
        ]
        if pairs:
            self._chunks, self._sources = map(list, zip(*pairs))
        else:
            self._chunks, self._sources = [], []
        self._dirty = True

    def documents(self) -> List[str]:
        """Return deduplicated list of indexed filenames (insertion order)."""
        return list(dict.fromkeys(self._sources))

    def is_empty(self) -> bool:
        return len(self._chunks) == 0

    def clear(self) -> None:
        self._chunks, self._sources = [], []
        self._vectorizer = None
        self._matrix = None
        self._dirty = True

    # ------------------------------------------------------------------
    # Index / search
    # ------------------------------------------------------------------

    def _build_index(self) -> None:
        if not self._chunks:
            self._vectorizer = None
            self._matrix = None
            self._dirty = False
            return
        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            max_features=50_000,
            sublinear_tf=True,
        )
        self._matrix = self._vectorizer.fit_transform(self._chunks)
        self._dirty = False

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Return the *top_k* most relevant chunks for *query*."""
        if self._dirty:
            self._build_index()
        if self._vectorizer is None or self._matrix is None:
            return []

        q_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self._matrix)[0]
        top_idx = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_idx:
            if scores[idx] > _MIN_SCORE:
                results.append(
                    {
                        "text": self._chunks[idx],
                        "source": self._sources[idx],
                        "score": float(scores[idx]),
                    }
                )
        return results
