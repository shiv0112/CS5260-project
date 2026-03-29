from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    runway_api_key: str = ""
    max_cost_per_session_sgd: float = 8.0
    cache_dir: str = "./cache"

    model_config = {"env_file": ".env"}


settings = Settings()
