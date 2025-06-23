from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(".env", override=True)


class RatelimiterSettings(BaseSettings):
    REDIS_HOST: str
    REDIS_PORT: int
    MESSAGES_PER_MINUTE: int
    MESSAGES_PER_DAY: int


ratelimiter_settings = RatelimiterSettings()
