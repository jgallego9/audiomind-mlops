"""Text embedding step using FastEmbed."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastembed import TextEmbedding
from moiraweave_step_sdk.base import BaseStep
from moiraweave_step_sdk.models import (
    InferRequest,
    InferResponse,
    MetadataTensor,
    Tensor,
)

if TYPE_CHECKING:
    from app.config import Settings


def _get_bytes(tensors: list[Tensor], name: str) -> str:
    """Extract a UTF-8 string from a named BYTES tensor.

    :param tensors: List of input tensors.
    :param name: Tensor name to look up.
    :returns: Decoded string value.
    :raises ValueError: If the tensor is not found.
    """
    for t in tensors:
        if t.name == name:
            data = t.data
            return data[0] if isinstance(data, list) else data
    raise ValueError(f"Missing required tensor: {name!r}")


class TextEmbedFastEmbedStep(BaseStep):
    """KServe V2 step that embeds text using FastEmbed.

    The embedding model is loaded once at construction time and cached in
    ``settings.model_cache_dir`` so that container restarts do not re-download.

    :param settings: Runtime configuration.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = TextEmbedding(
            model_name=settings.embed_model,
            cache_dir=settings.model_cache_dir,
        )

    @property
    def name(self) -> str:
        """Return the canonical step name."""
        return "text-embed-fastembed"

    @property
    def version(self) -> str:
        """Return the step version."""
        return "1"

    @property
    def task(self) -> str:
        """Return the moiraweave task name."""
        return "text-embed"

    @property
    def implementation(self) -> str:
        """Return the implementation identifier."""
        return "fastembed"

    @property
    def inputs(self) -> list[MetadataTensor]:
        """Return input tensor descriptors from the text-embed task schema."""
        return [MetadataTensor(name="text", datatype="BYTES", shape=[1])]

    @property
    def outputs(self) -> list[MetadataTensor]:
        """Return output tensor descriptors from the text-embed task schema."""
        return [MetadataTensor(name="embedding", datatype="FP32", shape=[-1])]

    async def predict(self, request: InferRequest) -> InferResponse:
        """Embed the input text and return its dense vector representation.

        :param request: KServe V2 inference request containing a ``text`` tensor.
        :returns: KServe V2 response with an ``embedding`` FP32 tensor.
        :raises ValueError: If the ``text`` tensor is missing.
        """
        text = _get_bytes(request.inputs, "text")
        embeddings = list(self._model.embed([text]))
        vector: list[float] = embeddings[0].tolist()
        return InferResponse(
            model_name=self.name,
            outputs=[
                Tensor(
                    name="embedding",
                    datatype="FP32",
                    shape=[len(vector)],
                    data=vector,
                )
            ],
        )
