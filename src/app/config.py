from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central place for config so nothing hardcodes a key or model name.

    Values are read from environment variables / a .env file. Add new
    settings here rather than reading os.environ directly elsewhere.
    """

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    database_path: str = "risk_workbench.db"
    prompt_version: str = "extract_change_request_v1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
