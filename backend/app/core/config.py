from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "HumanizeAI FactGuard"
    DEBUG: bool = False
    MODEL_PROVIDER_URL: str = "https://resonate-trimester-glade.ngrok-free.dev"
    MODEL_PROVIDER_TYPE: str = "lightning"
    API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
