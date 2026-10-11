import os
from typing import Dict, Any

class Settings:
    """Application configuration loaded from environment variables."""
    def __init__(self):
        self.app_env: str = os.getenv("APP_ENV", "development")
        self.port: int = int(os.getenv("APP_PORT", "8000"))
        self.model_name: str = os.getenv("MODEL_NAME", "gemini-1.5-pro-latest")
        self.default_ttl: int = int(os.getenv("DEFAULT_CACHE_TTL_SECONDS", "3600"))
        self.min_token_threshold: int = int(os.getenv("MIN_CACHE_TOKEN_THRESHOLD", "2048"))
        self.uncached_input_price_per_m: float = float(os.getenv("UNCACHED_INPUT_PRICE_PER_M", "3.50"))
        self.cached_input_price_per_m: float = float(os.getenv("CACHED_INPUT_PRICE_PER_M", "0.875"))
        self.output_price_per_m: float = float(os.getenv("OUTPUT_PRICE_PER_M", "10.50"))

def load_settings(env_file_path: str = ".env") -> Settings:
    if os.path.exists(env_file_path):
        with open(env_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
    return Settings()
