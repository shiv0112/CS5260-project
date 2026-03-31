from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    runway_api_key: str = ""
    max_cost_per_session_sgd: float = 8.0
    cache_dir: str = "./cache"
    chroma_persist_dir: str = "./chroma_db"
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o"
    chunk_size: int = 1500
    chunk_overlap: int = 200

    model_config = {"env_file": ".env"}


settings = Settings()
