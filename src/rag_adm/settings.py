from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(slots=True)
class Settings:
    llm_api_key: str | None
    llm_base_url: str | None
    llm_model: str | None
    llm_timeout_seconds: float

    @property
    def llm_mode(self) -> str:
        if self.llm_api_key and self.llm_base_url and self.llm_model:
            return "remote"
        return "mock"


def get_settings() -> Settings:
    timeout_value = os.getenv("LLM_TIMEOUT_SECONDS", "20")
    return Settings(
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL"),
        llm_model=os.getenv("LLM_MODEL"),
        llm_timeout_seconds=float(timeout_value),
    )
