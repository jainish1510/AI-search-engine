"""Application settings, read from environment variables."""
import os
from dataclasses import dataclass, field


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str = field(default_factory=lambda: os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    mongodb_db: str = field(default_factory=lambda: os.getenv("MONGODB_DB", "ai_search"))
    cors_origins: list[str] = field(
        default_factory=lambda: _csv(os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"))
    )
    seed_sample_data: bool = field(default_factory=lambda: os.getenv("SEED_SAMPLE_DATA", "").lower() in {"1", "true", "yes"})
    # BM25F parameters
    bm25_k1: float = 1.2
    title_weight: float = 3.0
    body_weight: float = 1.0
    title_b: float = 0.5
    body_b: float = 0.75


settings = Settings()
