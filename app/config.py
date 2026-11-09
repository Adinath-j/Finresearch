"""Application Configuration Management using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Central application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    app_name: str = "Multi-Agent Financial Research System"
    app_version: str = "0.1.0"
    app_env: str = Field(default="development")
    debug: bool = Field(default=True)
    port: int = Field(default=8000)

    # Database: Supabase PostgreSQL / SQLite Dual-Mode
    database_url: Optional[str] = Field(
        default=None,
        description="Supabase or PostgreSQL connection string (postgresql+psycopg://...)",
    )
    supabase_url: Optional[str] = Field(default=None)
    supabase_key: Optional[str] = Field(default=None)
    supabase_storage_bucket: str = Field(default="financial-documents")
    sqlite_db_path: str = Field(default=str(BASE_DIR / "documents.db"))

    # Storage Provider: 'local' or 'supabase'
    storage_provider: str = Field(default="local")
    upload_dir: str = Field(default=str(BASE_DIR / "uploads"))
    seed_docs_dir: str = Field(default=str(BASE_DIR / "seed_documents"))
    max_file_size: int = Field(
        default=22 * 1024 * 1024,
        description="Maximum upload size in bytes (22MB)",
    )

    # Vector Database: Qdrant with ChromaDB fallback
    vector_store_type: str = Field(
        default="auto",
        description="Vector store provider: 'qdrant', 'chroma', or 'auto'",
    )
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_api_key: Optional[str] = Field(default=None)
    qdrant_collection: str = Field(default="financial_chunks_openai_te3small_v1")

    chroma_db_dir: str = Field(default=str(BASE_DIR / "chroma_db"))
    chroma_collection: str = Field(default="financial_chunks_local_minilm_v1")

    # Embeddings Provider: 'openai' (default) or 'sentence-transformers' / 'local'
    embedding_provider: str = Field(
        default="openai",
        description="Embedding provider: 'openai' or 'sentence-transformers'",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI or HuggingFace model identifier for embeddings",
    )
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Legacy alias for embedding model name",
    )
    embedding_dimension: int = Field(default=1536)

    # LLM Provider Configuration
    llm_provider: str = Field(
        default="openai",
        description="LLM provider: 'openai', 'gemini', or 'mock'",
    )
    llm_model: str = Field(default="gpt-6.1-sol", description="Primary reasoning LLM model name")
    llm_reasoning_effort: str = Field(default="high", description="Reasoning effort: 'low', 'medium', or 'high'")
    llm_api_key: Optional[str] = Field(default=None, description="API key for cloud LLM")
    openai_api_key: Optional[str] = Field(default=None, description="Direct OpenAI API key alias")
    openai_base_url: str = Field(default="https://api.openai.com/v1")
    openai_enable_pdf_vision: bool = Field(default=False)
    llm_temperature: float = Field(default=0.0)

    # Chunking
    chunk_target_tokens: int = Field(default=350)
    chunk_overlap_tokens: int = Field(default=50)

    # Background Persistent Job Worker
    worker_poll_seconds: int = Field(default=3)
    worker_max_retries: int = Field(default=3)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()

