from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(".env", override=True)


class Settings(BaseSettings):
    REDIS_HOST: str
    REDIS_PORT: int
    MESSAGES_PER_MINUTE: int
    MESSAGES_PER_DAY: int
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    def get_postgres_dsn(self, driver_name=None) -> str:
        return f"postgresql{f'+{driver_name}' if driver_name else ''}://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
