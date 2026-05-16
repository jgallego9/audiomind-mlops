"""Vector search step using Qdrant."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from moiraweave_step_sdk.base import BaseStep
from moiraweave_step_sdk.models import (
    InferRequest,
    InferResponse,
    MetadataTensor,
    Tensor,
)
from qdrant_client import AsyncQdrantClient

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


def _get_floats(tensors: list[Tensor], name: str) -> list[float]:
    """Extract a float list from a named FP32 tensor.

    :param tensors: List of input tensors.
    :param name: Tensor name to look up.
    :returns: List of float values.
    :raises ValueError: If the tensor is not found.
    """
    for t in tensors:
        if t.name == name:
            return list(t.data)
    raise ValueError(f"Missing required tensor: {name!r}")


def _get_int(tensors: list[Tensor], name: str, default: int) -> int:
    """Extract an integer from a named INT64 tensor.

    :param tensors: List of input tensors.
    :param name: Tensor name to look up.
    :param default: Value returned when the tensor is absent.
    :returns: Integer value.
    """
    for t in tensors:
        if t.name == name:
            data = t.data
            return int(data[0] if isinstance(data, list) else data)
    return default


def _get_bytes(tensors: list[Tensor], name: str, default: str) -> str:
    """Extract a UTF-8 string from a named BYTES tensor.

    :param tensors: List of input tensors.
    :param name: Tensor name to look up.
    :param default: Value returned when the tensor is absent.
    :returns: Decoded string value.
    """
    for t in tensors:
        if t.name == name:
            data = t.data
            return data[0] if isinstance(data, list) else data
    return default


class VectorSearchQdrantStep(BaseStep):
    """KServe V2 step that retrieves nearest-neighbour vectors from Qdrant.

    :param settings: Runtime configuration.
    :param client: Async Qdrant client (injected for testing).
    """

    def __init__(
        self,
        settings: Settings,
        client: AsyncQdrantClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client or AsyncQdrantClient(url=settings.qdrant_url)

    @property
    def name(self) -> str:
        """Return the canonical step name."""
        return "vector-search-qdrant"

    @property
    def version(self) -> str:
        """Return the step version."""
        return "1"

    @property
    def task(self) -> str:
        """Return the inferflow task name."""
        return "vector-search"

    @property
    def implementation(self) -> str:
        """Return the implementation identifier."""
        return "qdrant"

    @property
    def inputs(self) -> list[MetadataTensor]:
        """Return input tensor descriptors from the vector-search task schema."""
        return [
            MetadataTensor(name="vector", datatype="FP32", shape=[-1]),
            MetadataTensor(name="top_k", datatype="INT64", shape=[1]),
            MetadataTensor(name="filters", datatype="BYTES", shape=[1]),
        ]

    @property
    def outputs(self) -> list[MetadataTensor]:
        """Return output tensor descriptors from the vector-search task schema."""
        return [MetadataTensor(name="results", datatype="BYTES", shape=[1])]

    async def predict(self, request: InferRequest) -> InferResponse:
        """Search for nearest-neighbour vectors in Qdrant.

        :param request: KServe V2 request with a ``vector`` tensor and
            optional ``top_k`` and ``filters`` tensors.
        :returns: KServe V2 response with a ``results`` BYTES tensor
            containing a JSON-encoded list of ``{id, score, metadata}`` dicts.
        :raises ValueError: If the ``vector`` tensor is missing.
        """
        query_vector = _get_floats(request.inputs, "vector")
        top_k = _get_int(request.inputs, "top_k", self._settings.default_top_k)
        filters_raw = _get_bytes(request.inputs, "filters", "{}")
        qdrant_filter = (
            json.loads(filters_raw) if filters_raw.strip() not in ("{}", "") else None
        )

        hits = await self._client.search(
            collection_name=self._settings.qdrant_collection,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=self._settings.score_threshold or None,
            query_filter=qdrant_filter,
        )

        results = [
            {"id": str(hit.id), "score": hit.score, "metadata": hit.payload or {}}
            for hit in hits
        ]
        logger.info(
            "vector_search_done collection=%s top_k=%d hits=%d",
            self._settings.qdrant_collection,
            top_k,
            len(results),
        )

        return InferResponse(
            model_name=self.name,
            outputs=[
                Tensor(
                    name="results",
                    datatype="BYTES",
                    shape=[1],
                    data=[json.dumps(results)],
                )
            ],
        )
