from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    #Configuración global
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # APP CORE
    APP_NAME: str = "hee-hee"
    ENV: str = "dev"
    DEBUG: bool = True
    VERSION: str = "0.1.0"

    # DATABASE
    DATABASE_URL: str # async fastapi
    DATABASE_URL_SYNC: str # sync alembic

    # Pool tuning
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # LLM
    GEMINI_MODEL: str = ""

    # embeddings
    GEMINI_API_KEY: str = ""
    EMBEDDING_MODEL: str = ""
    EMBEDDING_DIMENSION: int = 768

    # RAG CONFIG
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    TOP_K_RETRIEVAL: int = 5

    # AUTH
    AUTH0_DOMAIN: str | None = None
    AUTH0_AUDIENCE: str | None = None
    JWT_SECRET: str | None = None

    # VECTOR STORE
    VECTOR_DB_TYPE: str = "pgvector"

settings = Settings()