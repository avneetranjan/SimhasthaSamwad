from functools import lru_cache
import os


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Simhastha Samwad")
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Backend host/port
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Database
    SQLITE_PATH: str = os.getenv("SQLITE_PATH", os.path.join(os.getcwd(), "simhastha.db"))

    # CORS
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

    # SAMWAD API (stubbed/injectable)
    SAMWAD_BASE_URL: str = os.getenv("SAMWAD_BASE_URL", "https://api.samwad.example.com")
    SAMWAD_API_KEY: str = os.getenv("SAMWAD_API_KEY", "changeme")
    # Samwad send endpoint + token (prefer SAMWAD_TOKEN, fallback to SAMWAD_API_KEY)
    SAMWAD_SEND_URL: str = os.getenv("SAMWAD_SEND_URL", "https://www.app.samwad.tech/api/wpbox/sendmessage")
    SAMWAD_TOKEN: str = os.getenv("SAMWAD_TOKEN") or os.getenv("SAMWAD_API_KEY", "changeme")
    # Samwad location endpoints
    SAMWAD_LOCATION_URL: str = os.getenv("SAMWAD_LOCATION_URL", "https://www.app.samwad.tech/api/wpbox/sendlocation")
    SAMWAD_LOCATION_REQUEST_URL: str = os.getenv("SAMWAD_LOCATION_REQUEST_URL", "https://www.app.samwad.tech/api/wpbox/sendlocationrequest")

    # AI (Ollama/OpenAI-compatible) chat settings
    # Base URL should end at /v1 (the client appends /chat/completions)
    AI_BASE_URL: str = os.getenv("AI_BASE_URL", "http://127.0.0.1:11434/v1")
    AI_MODEL: str = os.getenv("AI_MODEL", "gemma3:12b")
    AI_API_KEY: str = os.getenv("AI_API_KEY", "ollama")
    AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.4"))
    AI_MAX_TOKENS: int = int(os.getenv("AI_MAX_TOKENS", "500"))
    AI_KEEP_ALIVE: str = os.getenv("AI_KEEP_ALIVE", "600m")
    AI_AUTOREPLY: bool = os.getenv("AI_AUTOREPLY", "false").lower() == "true"

    # Ops / escalation
    ESCALATION_NUMBERS: str = os.getenv("ESCALATION_NUMBERS", "")  # comma-separated

    # Auto-assignment defaults (labels/usernames handled externally)
    ASSIGNEE_SANITATION: str = os.getenv("ASSIGNEE_SANITATION", "")
    ASSIGNEE_EMERGENCY: str = os.getenv("ASSIGNEE_EMERGENCY", "")
    ASSIGNEE_INFO: str = os.getenv("ASSIGNEE_INFO", "")

    # Messaging ETAs (minutes)
    SANITATION_ETA_MINUTES: int = int(os.getenv("SANITATION_ETA_MINUTES", "12"))
    MEDICAL_ETA_MINUTES: int = int(os.getenv("MEDICAL_ETA_MINUTES", "7"))

    # Agent approvals
    AGENT_AUTO_APPROVE_HIGHRISK: bool = os.getenv("AGENT_AUTO_APPROVE_HIGHRISK", "false").lower() == "true"


@lru_cache
def get_settings() -> Settings:
    return Settings()
