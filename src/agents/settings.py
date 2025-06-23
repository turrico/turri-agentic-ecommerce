from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(".env", override=False)


class Settings(BaseSettings):
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    GEMINI_TIME_OUT: int = 15
    GOOGLE_API_KEY: str

    def get_postgres_dsn(self, driver_name=None) -> str:
        return f"postgresql{f'+{driver_name}' if driver_name else ''}://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
