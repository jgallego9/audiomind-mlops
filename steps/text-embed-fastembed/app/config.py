from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the text-embed-fastembed step.

    :param embed_model: FastEmbed model name. Models are downloaded to
        ``model_cache_dir`` on first use and cached for subsequent requests.
    :param model_cache_dir: Local directory where FastEmbed stores model files.
    """

    model_config = SettingsConfigDict(env_prefix="EMBED_STEP_")

    embed_model: str = "BAAI/bge-small-en-v1.5"
    model_cache_dir: str = "/models"
