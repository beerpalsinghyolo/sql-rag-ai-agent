"""Application configuration loaded from environment variables."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_type: Literal["sqlite", "mysql"] = "sqlite"
    sqlite_path: str = "./data/demo.db"
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "mydb"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    top_k_schema: int = 5
    chroma_path: str = "./chroma_db"

    def sqlalchemy_uri(self) -> str:
        if self.db_type == "sqlite":
            path = Path(self.sqlite_path).resolve()
            return f"sqlite:///{path.as_posix()}"
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    def db_label(self) -> str:
        if self.db_type == "sqlite":
            return Path(self.sqlite_path).stem
        return self.mysql_database

    def chroma_collection_name(self) -> str:
        return f"schema_{self.db_label()}"


def get_settings(db_type: str | None = None) -> Settings:
    settings = Settings()
    if db_type:
        settings = settings.model_copy(update={"db_type": db_type})
    return settings
