from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the vector-search-qdrant step.

    :param qdrant_url: Base URL of the Qdrant HTTP API.
    :param qdrant_collection: Collection to query.
    :param default_top_k: Number of results to return when the ``top_k``
        tensor is absent from the request.
    :param score_threshold: Minimum similarity score for returned results.
        Results below this threshold are excluded.
    """

    model_config = SettingsConfigDict(env_prefix="SEARCH_STEP_")

    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "transcriptions"
    default_top_k: int = 5
    score_threshold: float = 0.0
