"""RecoverAI backend configuration.

All settings are loaded from environment variables.
Never hard-code secrets.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Mode ──
    recovery_mode: str = Field(default="simulation", description="simulation | razorpay_test")
    demo_mode: bool = Field(default=True)

    # ── Database ──
    database_url: str = Field(default="sqlite:///./recoverai.db")

    # ── LLM ──
    llm_provider: str = Field(default="gemini", description="gemini | openai | anthropic")
    gemini_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")

    # ── Razorpay ──
    razorpay_key_id: str = Field(default="")
    razorpay_key_secret: str = Field(default="")
    razorpay_webhook_secret: str = Field(default="")

    # ── Policy Engine Thresholds ──
    recovery_probability_threshold: float = Field(default=0.60)
    scorer_confidence_threshold: float = Field(default=0.70)
    auto_recovery_amount_limit: float = Field(default=50000.0)
    max_retries: int = Field(default=2)
    max_llm_calls: int = Field(default=3)
    max_agent_steps: int = Field(default=10)
    agent_step_timeout: int = Field(default=30)

    # ── Server ──
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=True)

    # ── Frontend ──
    frontend_url: str = Field(default="http://localhost:3000")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
