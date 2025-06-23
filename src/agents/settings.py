from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(".env", override=False)


class GeminiSettings(BaseSettings):
    GEMINI_TIME_OUT: int = 30
    GOOGLE_API_KEY: str


settings = GeminiSettings()
