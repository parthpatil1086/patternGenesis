from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseModel):
    app_name: str = "PatternGenesis"
    backend_url: str = "http://localhost:8000"
    ai_enabled: bool = False
    ai_api_key: str = ""


settings = Settings()
