import httpx
from inferflow_step_sdk.base import BaseStep
from inferflow_step_sdk.models import InferRequest, InferResponse, Tensor

from app.config import Settings


class AudioTranscribeWhisperStep(BaseStep):
    """KServe V2 step that transcribes audio via Whisper ASR Webservice.

    :param settings: Runtime configuration (Whisper URL).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        """Return the canonical step name."""
        return "audio-transcribe-whisper"

    @property
    def version(self) -> str:
        """Return the step version."""
        return "1"

    async def predict(self, request: InferRequest) -> InferResponse:
        """Download audio from URL and transcribe it via Whisper ASR.

        :param request: KServe V2 infer request containing ``audio_url``
            (required) and ``language`` (optional, default ``"auto"``) tensors.
        :returns: KServe V2 infer response with ``transcript``, ``language``,
            and ``duration`` output tensors.
        :raises httpx.HTTPStatusError: If the audio download or Whisper
            request returns a non-2xx status.
        :raises ValueError: If the required ``audio_url`` tensor is missing.
        """
        audio_url = _get_bytes_tensor(request, "audio_url")
        language = _get_bytes_tensor(request, "language", default="auto")

        async with httpx.AsyncClient(timeout=30.0) as client:
            audio_resp = await client.get(audio_url)
            audio_resp.raise_for_status()

            params: dict[str, str] = {
                "encode": "true",
                "task": "transcribe",
                "output": "json",
            }
            if language != "auto":
                params["language"] = language

            whisper_resp = await client.post(
                f"{self._settings.whisper_url}/asr",
                params=params,
                files={"audio_file": ("audio", audio_resp.content, "audio/mpeg")},
            )
            whisper_resp.raise_for_status()

        result = whisper_resp.json()
        detected_language: str = result.get("language") or language
        transcript: str = result.get("text", "")
        duration: float = float(result.get("duration", 0.0))

        return InferResponse(
            model_name=self.name,
            id=request.id,
            outputs=[
                Tensor(
                    name="transcript",
                    shape=[1],
                    datatype="BYTES",
                    data=[transcript],
                ),
                Tensor(
                    name="language",
                    shape=[1],
                    datatype="BYTES",
                    data=[detected_language],
                ),
                Tensor(
                    name="duration",
                    shape=[1],
                    datatype="FP32",
                    data=[duration],
                ),
            ],
        )


def _get_bytes_tensor(
    request: InferRequest,
    name: str,
    *,
    default: str | None = None,
) -> str:
    """Extract the first data element from a named BYTES tensor.

    :param request: The infer request to search.
    :param name: Tensor name to look for.
    :param default: Value returned when the tensor is absent.
    :returns: The string value extracted from the tensor data.
    :raises ValueError: If the tensor is absent and no default is provided.
    """
    for tensor in request.inputs:
        if tensor.name == name:
            return str(tensor.data[0])
    if default is not None:
        return default
    raise ValueError(f"Required input tensor '{name}' not found")
