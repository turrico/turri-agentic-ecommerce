import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(".env", override=False)


class WoocommerceSettings(BaseSettings):
    big_query_dataset_name: str = "wordpress_data"
    url: str = "https://turri.cr"
    WOOCOMERCE_CLIENT_KEY: str
    WOOCOMERCE_SECRET_KEY: str


class GoogleCloudSettings(BaseSettings):
    GC_PROJECT_ID: str
    ANALYTICS_BG_TABLE_NAME: str


class DataBaseSettings(BaseSettings):
    GOOGLE_API_KEY: str
    embedding_model: str = "models/text-embedding-004"
    POSTGRES_HOST: str
    POSTGRES_PORT: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_NAME: str
    DB_CONNECTION_NAME: str | None = None

    def get_postgres_dsn(self, driver_name: str = "asyncpg") -> str:
        if self.DB_CONNECTION_NAME:
            return (
                f"postgresql+{driver_name}://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@/{self.POSTGRES_NAME}"
                f"?host=/cloudsql/{self.DB_CONNECTION_NAME}"
            )
        else:
            return (
                f"postgresql+{driver_name}://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_NAME}"
            )


# Environment: 'local' or 'cloud'
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

database_settings = DataBaseSettings()
