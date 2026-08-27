"""Numpy-only TF-IDF transform matching scikit-learn's TfidfVectorizer defaults."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from engine.analyzer import tokenize


@dataclass(frozen=True)
class TfidfModel:
    vocabulary: dict[str, int]
    idf: np.ndarray
    norm: str = "l2"

    @property
    def vocab_size(self) -> int:
        return len(self.idf)

    def transform(self, text: str) -> np.ndarray:
        tokens = tokenize(text)
        vector = np.zeros(self.vocab_size, dtype=np.float64)
        if not tokens:
            return vector.astype(np.float32)

        for token in tokens:
            index = self.vocabulary.get(token)
            if index is not None:
                vector[index] += 1.0

        nonzero = vector > 0
        if not np.any(nonzero):
            return vector.astype(np.float32)

        vector[nonzero] *= self.idf[nonzero]

        if self.norm == "l2":
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector /= norm

        return vector.astype(np.float32)

    def transform_many(self, texts: list[str]) -> np.ndarray:
        return np.vstack([self.transform(text) for text in texts])

    def sparse_matvec(
        self,
        data: np.ndarray,
        indices: np.ndarray,
        indptr: np.ndarray,
        vector: np.ndarray,
    ) -> np.ndarray:
        """Multiply a CSR matrix by a dense vector without scipy."""
        row_count = len(indptr) - 1
        output = np.zeros(row_count, dtype=np.float32)
        for row in range(row_count):
            start = indptr[row]
            end = indptr[row + 1]
            if start == end:
                continue
            row_indices = indices[start:end]
            row_data = data[start:end]
            output[row] = float(np.dot(row_data, vector[row_indices]))
        return output
