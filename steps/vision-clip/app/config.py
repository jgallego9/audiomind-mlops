from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the vision-clip step.

    :param vision_model: FastEmbed image model name.
    :param model_cache_dir: Local directory where model files are cached.
    """

    model_config = SettingsConfigDict(env_prefix="VISION_STEP_")

    vision_model: str = "Qdrant/resnet50-onnx"
    model_cache_dir: str = "/models"
