from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = Field(default="dev", alias="APP_ENV")
    app_name: str = Field(default="yk-hospital-data-review-agent", alias="APP_NAME")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")

    database_url: str = Field(default="sqlite+pysqlite:///./demo.db", alias="DATABASE_URL")
    llm_model: str = Field(default="qwen-plus", alias="LLM_MODEL")
    llm_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        alias="LLM_BASE_URL",
    )
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")

    session_store_backend: str = Field(default="memory", alias="SESSION_STORE_BACKEND")
    host_allowed_origins: str = Field(default="http://localhost:5173", alias="HOST_ALLOWED_ORIGINS")
    demo_mode: bool = Field(default=True, alias="DEMO_MODE")
    pgta_detail_file: str = Field(
        default="docs/PGTA数据统计输出-2025年.xlsx",
        alias="PGTA_DETAIL_FILE",
    )
    pgtah_snapshot_file: str = Field(
        default="docs/PGTAH数据统计输出-2025年-上传微盘.xlsx",
        alias="PGTAH_SNAPSHOT_FILE",
    )
    pgtsr_snapshot_file: str = Field(
        default="docs/PGTSR数据统计输出-2025年.xlsx",
        alias="PGTSR_SNAPSHOT_FILE",
    )
    pgtm_snapshot_file: str = Field(
        default="docs/2025-PGTM类全年输出.xlsx",
        alias="PGTM_SNAPSHOT_FILE",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.host_allowed_origins.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
