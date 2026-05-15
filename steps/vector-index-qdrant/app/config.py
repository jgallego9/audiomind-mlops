from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the vector-index-qdrant step.

    :param qdrant_url: Base URL of the Qdrant HTTP API.
    :param qdrant_collection: Collection to index vectors into.
        The collection is created automatically if it does not exist.
    :param vector_size: Dimensionality of the vectors being indexed.
        Must match the collection's configured vector size.
    """

    model_config = SettingsConfigDict(env_prefix="INDEX_STEP_")

    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "transcriptions"
    vector_size: int = 384
