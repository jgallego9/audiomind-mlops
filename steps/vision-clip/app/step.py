"""Image embedding step using FastEmbed vision models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from moiraweave_step_sdk.base import BaseStep
from moiraweave_step_sdk.models import (
    InferRequest,
    InferResponse,
    MetadataTensor,
    Tensor,
)

try:
    from fastembed import ImageEmbedding
except ImportError:  # pragma: no cover - compatibility fallback
    from fastembed import TextEmbedding as ImageEmbedding

if TYPE_CHECKING:
    from app.config import Settings


def _get_bytes(tensors: list[Tensor], name: str) -> str:
    """Extract a UTF-8 string from a named BYTES tensor.

    :param tensors: List of input tensors.
    :param name: Tensor name to look up.
    :returns: Decoded string value.
    :raises ValueError: If the tensor is not found.
    """
    for tensor in tensors:
        if tensor.name == name:
            data = tensor.data
            return data[0] if isinstance(data, list) else data
    raise ValueError(f"Missing required tensor: {name!r}")


class VisionClipStep(BaseStep):
    """KServe V2 step that embeds images using a CLIP-like model.

    The model is loaded once at construction time and cached in
    ``settings.model_cache_dir``.

    :param settings: Runtime configuration.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = ImageEmbedding(
            model_name=settings.vision_model,
            cache_dir=settings.model_cache_dir,
        )

    @property
    def name(self) -> str:
        """Return the canonical step name."""
        return "vision-clip"

    @property
    def version(self) -> str:
        """Return the step version."""
        return "1"

    @property
    def task(self) -> str:
        """Return the inferflow task name."""
        return "vision-embedding"

    @property
    def implementation(self) -> str:
        """Return the implementation identifier."""
        return "clip"

    @property
    def inputs(self) -> list[MetadataTensor]:
        """Return input tensor descriptors from the image-embed task schema."""
        return [MetadataTensor(name="image_url", datatype="BYTES", shape=[1])]

    @property
    def outputs(self) -> list[MetadataTensor]:
        """Return output tensor descriptors from the vision-embedding schema."""
        return [MetadataTensor(name="vector", datatype="FP32", shape=[-1])]

    async def predict(self, request: InferRequest) -> InferResponse:
        """Generate an image embedding from the incoming request.

        :param request: KServe V2 infer request with ``image_url`` tensor.
        :returns: KServe V2 infer response with ``embedding`` tensor.
        """
        image_url = _get_bytes(request.inputs, "image_url")
        vector = list(self._model.embed([image_url]))[0]
        embedding = [float(value) for value in vector.tolist()]

        return InferResponse(
            model_name=self.name,
            outputs=[
                Tensor(
                    name="vector",
                    datatype="FP32",
                    shape=[len(embedding)],
                    data=embedding,
                )
            ],
        )
