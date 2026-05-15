"""Vector indexing step using Qdrant."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from inferflow_step_sdk.base import BaseStep
from inferflow_step_sdk.models import (
    InferRequest,
    InferResponse,
    MetadataTensor,
    Tensor,
)
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


def _get_bytes(tensors: list[Tensor], name: str, default: str | None = None) -> str:
    """Extract a UTF-8 string from a named BYTES tensor.

    :param tensors: List of input tensors.
    :param name: Tensor name to look up.
    :param default: Value returned when the tensor is absent (``None`` raises).
    :returns: Decoded string value.
    :raises ValueError: If the tensor is not found and *default* is ``None``.
    """
    for t in tensors:
        if t.name == name:
            data = t.data
            return data[0] if isinstance(data, list) else data
    if default is not None:
        return default
    raise ValueError(f"Missing required tensor: {name!r}")


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


class VectorIndexQdrantStep(BaseStep):
    """KServe V2 step that upserts a vector + metadata into Qdrant.

    The target collection is created automatically if it does not exist,
    using ``settings.vector_size`` as the vector dimension and cosine distance.

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
        return "vector-index-qdrant"

    @property
    def version(self) -> str:
        """Return the step version."""
        return "1"

    @property
    def task(self) -> str:
        """Return the inferflow task name."""
        return "vector-index"

    @property
    def implementation(self) -> str:
        """Return the implementation identifier."""
        return "qdrant"

    @property
    def inputs(self) -> list[MetadataTensor]:
        """Return input tensor descriptors from the vector-index task schema."""
        return [
            MetadataTensor(name="id", datatype="BYTES", shape=[1]),
            MetadataTensor(name="vector", datatype="FP32", shape=[-1]),
            MetadataTensor(name="metadata", datatype="BYTES", shape=[1]),
        ]

    @property
    def outputs(self) -> list[MetadataTensor]:
        """Return output tensor descriptors from the vector-index task schema."""
        return [MetadataTensor(name="indexed", datatype="BOOL", shape=[1])]

    async def _ensure_collection(self) -> None:
        """Create the Qdrant collection if it does not already exist."""
        collections = await self._client.get_collections()
        names = {c.name for c in collections.collections}
        if self._settings.qdrant_collection not in names:
            await self._client.create_collection(
                collection_name=self._settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=self._settings.vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(
                "qdrant_collection_created collection=%s size=%d",
                self._settings.qdrant_collection,
                self._settings.vector_size,
            )

    async def predict(self, request: InferRequest) -> InferResponse:
        """Upsert the input vector and metadata into Qdrant.

        :param request: KServe V2 request with ``id``, ``vector``, and
            optionally ``metadata`` tensors.
        :returns: KServe V2 response with an ``indexed`` BOOL tensor.
        :raises ValueError: If a required tensor is missing.
        """
        doc_id = _get_bytes(request.inputs, "id")
        vector = _get_floats(request.inputs, "vector")
        metadata_raw = _get_bytes(request.inputs, "metadata", default="{}")
        payload: dict[str, Any] = json.loads(metadata_raw)

        await self._ensure_collection()
        await self._client.upsert(
            collection_name=self._settings.qdrant_collection,
            points=[PointStruct(id=doc_id, vector=vector, payload=payload)],
        )
        logger.info(
            "vector_indexed id=%s collection=%s",
            doc_id,
            self._settings.qdrant_collection,
        )

        return InferResponse(
            model_name=self.name,
            outputs=[Tensor(name="indexed", datatype="BOOL", shape=[1], data=[True])],
        )
