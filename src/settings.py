from pydantic_settings import BaseSettings


class KafkaSettings(BaseSettings):
    """Kafka configuration."""

    # Connection
    BOOTSTRAP_SERVERS: str = "localhost:9092"

    # Topics
    ORDER_EVENTS_TOPIC: str = "student_system-order.events"
    SHIPMENT_EVENTS_TOPIC: str = "student_system-shipment.events"
    SHIPMENT_EVENTS_RETRY_TOPIC: str = "student_system-shipment.events.retry"
    SHIPMENT_EVENTS_DLQ_TOPIC: str = "student_system-shipment.events.dlq"

    # Retry delays
    RETRY_DELAYS: list[int] = [5, 30, 120, 600]  # 5s, 30s, 2min, 10min
    MAX_RETRIES: int = 4

    # Consumer
    CONSUMER_GROUP_ID: str = "order-service-group"

    # Producer
    ACKS: str = "all"
    ENABLE_IDEMPOTENCE: bool = True
    RETRY_BACKOFF_MS: int = 200
    BATCH_SIZE: int = 16384
    LINGER_MS: int = 10
    COMPRESSION_TYPE: str = "gzip"
    REQUEST_TIMEOUT_MS: int = 30000

    # Consumer batch
    MIN_BATCH_SIZE: int = 10
    MAX_BATCH_SIZE: int = 100
    MAX_WAIT_TIME: float = 1.0
    POLL_TIMEOUT_MS: int = 100

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        env_prefix = "KAFKA_"


class Settings(BaseSettings):
    # Service configuration
    SERVICE_NAME: str = "order-service"
    DEBUG: bool = False

    # HTTP server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    POSTGRES_DATABASE_NAME: str = "order_service"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USERNAME: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # Capashino Services
    CAPASHINO_BASE_URL: str = ""
    CAPASHINO_API_KEY: str = ""
    INTERNAL_HOSTNAME: str = "http://order-service.order-service.svc:8000"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USERNAME}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
kafka_settings = KafkaSettings()
