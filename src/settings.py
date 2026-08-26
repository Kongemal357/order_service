from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Service configuration
    SERVICE_NAME: str = "order-service"
    DEBUG: bool = False

    # HTTP server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    POSTGRES_DATABASE_NAME: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str

    # Capashino Services
    CAPASHINO_BASE_URL: str
    CAPASHINO_API_KEY: str = ""  # Required in production
    INTERNAL_HOSTNAME: str = "http://order-service.order-service.svc:8000"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka.kafka.svc.cluster.local:9092"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USERNAME}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
