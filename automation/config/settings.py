import os
from dataclasses import dataclass

_TRUTHY = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    base_url: str
    user_id: str
    headless: bool
    ui_timeout: float
    api_timeout: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            base_url=os.getenv("BASE_URL", "https://qae-assignment-tau.vercel.app").rstrip("/"),
            user_id=os.getenv("USER_ID", "candidate-lK0oEBSF2OFO"),
            headless=os.getenv("HEADLESS", "0").strip().lower() in _TRUTHY,
            ui_timeout=float(os.getenv("UI_TIMEOUT", "15")),
            api_timeout=float(os.getenv("API_TIMEOUT", "10")),
        )
