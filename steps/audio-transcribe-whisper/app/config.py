from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the audio-transcribe-whisper step.

    :param whisper_url: Base URL of the Whisper ASR Webservice.
    """

    model_config = SettingsConfigDict(env_prefix="WHISPER_STEP_")

    whisper_url: str = "http://whisper:9000"
