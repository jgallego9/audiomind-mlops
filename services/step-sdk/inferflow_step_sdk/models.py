"""KServe Open Inference Protocol V2 Pydantic models.

Reference: https://github.com/kserve/open-inference-protocol/blob/main/specification/protocol/inference_rest.md
"""

from typing import Any

from pydantic import BaseModel


class Tensor(BaseModel):
    """A single input or output tensor conforming to the V2 protocol.

    :param name: Tensor name.
    :param shape: Shape of the tensor; use ``-1`` for variable-size dims.
    :param datatype: Element type — ``BYTES``, ``FP32``, ``INT64``, etc.
    :param data: Flat list of tensor elements in row-major order.
    """

    name: str
    shape: list[int]
    datatype: str
    data: list[Any]


class InferRequest(BaseModel):
    """``$inference_request`` — body for ``POST /v2/models/{name}/infer``.

    :param id: Optional request identifier echoed in the response.
    :param inputs: Input tensors.
    :param outputs: Optional list of output tensor names to return.
    """

    id: str | None = None
    inputs: list[Tensor]
    outputs: list[dict[str, str]] | None = None


class InferResponse(BaseModel):
    """``$inference_response`` — body returned by the infer endpoint.

    :param model_name: Name of the model that processed the request.
    :param model_version: Optional model version string.
    :param id: Echo of the request ``id`` (if provided).
    :param outputs: Output tensors.
    """

    model_name: str
    model_version: str | None = None
    id: str | None = None
    outputs: list[Tensor]


class ErrorResponse(BaseModel):
    """``$inference_error_response`` — returned on 4xx/5xx errors.

    :param error: Human-readable error description.
    """

    error: str


class ServerLiveResponse(BaseModel):
    """``$live_server_response`` / ``$ready_server_response``.

    :param live: ``True`` when the server can receive requests.
    """

    live: bool


class ModelReadyResponse(BaseModel):
    """``$ready_model_response`` — returned by model-ready probe.

    :param name: Model name.
    :param ready: ``True`` when the model is loaded and ready to infer.
    """

    name: str
    ready: bool
