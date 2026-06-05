from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MongoDB
    mongodb_uri: str
    mongodb_db: str = "RetailCustomer360"

    # Voyage AI
    voyage_api_key: str
    voyage_index_model: str = "voyage-4-large"
    voyage_query_model: str = "voyage-4-lite"
    voyage_rerank_model: str = "rerank-2.5"
    voyage_dimensions: int = 1024

    # GCP / Vertex AI
    gcp_project_id: str
    gcp_location: str = "asia-southeast1"
    vertex_ai_model: str = "gemini-2.5-flash"

    # JWT
    jwt_secret: str = "RetailCustomer360-demo-secret-key-not-for-production"

    # MCP Server
    mcp_connection_string: str = ""
    mcp_server_command: str = "npx"
    mcp_server_args: list[str] = ["-y", "mongodb-mcp-server"]

    # Kafka
    kafka_bootstrap_servers: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
