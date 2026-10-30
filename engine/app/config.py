import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://localhost:8080/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "local")
    # Empty = use the first model served by the endpoint.
    llm_model: str = os.getenv("LLM_MODEL", "")
    llm_timeout: float = float(os.getenv("LLM_TIMEOUT", "600"))
    llm_concurrency: int = int(os.getenv("LLM_CONCURRENCY", "6"))
    # Ask the model to skip its <think> phase (Qwen3.x). Ignored by models without thinking.
    llm_disable_thinking: bool = os.getenv("LLM_DISABLE_THINKING", "1") == "1"

    # Comma-separated API keys accepted in the X-API-Key header. Empty disables auth (local dev only).
    api_keys: set[str] = {k.strip() for k in os.getenv("ENGINE_API_KEYS", "").split(",") if k.strip()}
    # Shared secret used to verify short-lived upload tokens minted by the web app.
    token_secret: str = os.getenv("ENGINE_TOKEN_SECRET", "")
    cors_origins: list[str] = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

    data_dir: Path = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
    template_path: Path = Path(os.getenv("TEMPLATE_PATH", str(BASE_DIR / "templates" / "admind_master.pptx")))
    assets_dir: Path = Path(os.getenv("ASSETS_DIR", str(BASE_DIR / "assets")))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "50"))
    job_retention_hours: int = int(os.getenv("JOB_RETENTION_HOURS", "72"))
    render_previews: bool = os.getenv("RENDER_PREVIEWS", "1") == "1"
    contact_line: str = os.getenv("CONTACT_LINE", "admindagency.com")


settings = Settings()
