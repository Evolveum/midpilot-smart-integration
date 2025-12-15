# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """
    Log level settings for the application.

    :cvar debug: Debug-level logging, most verbose.
    :cvar info: Informational messages, default level.
    :cvar warning: Warning messages, potential issues.
    :cvar error: Error messages, serious problems.
    :cvar critical: Critical errors, application shutdown scenarios.
    """

    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class LoggingSettings(BaseModel):
    """
    Configuration for application logging.

    :param level: LogLevel enum specifying the logging threshold.
    :param access_log: Enable or disable access logs.
    :param colors: Enable or disable colored log output.
    :param live_reload: Enable live reloading of logs on code changes.
    """

    level: LogLevel = LogLevel.info
    access_log: bool = True
    colors: bool = False
    live_reload: bool = False


class LLMSettings(BaseModel):
    """
    Configuration for the LLM client.

    :param openai_api_key: API key for OpenAI-compatible services.
    :param openai_api_base: Base URL for the API endpoint.
    :param model_name: Default model identifier to use.
    :param request_timeout: Timeout for API requests in seconds.
    :param extra_body: Extra body used for provider-specific requests.
    """

    openai_api_key: str = ""
    openai_api_base: str = "https://openrouter.ai/api/v1"
    model_name: str = "openai/gpt-oss-20b"
    request_timeout: int = 120
    # extra_body is used for provider-specific requests
    extra_body: Dict[str, Any] = Field(
        default_factory=lambda: {
            "provider": {"order": ["groq", "parasail", "deepinfra"]},
        }
    )


class LangfuseSettings(BaseModel):
    """
    Configuration for the Langfuse client.

    :param public_key: Public Langfuse host key.
    :param secret_key: Secret Langfuse host key.
    :param host: Langfuse host.
    :param tracing_enabled: Enable/disable langfuse tracing.
    :param environment: Environment name e.g. demo, dev-myname.
    """

    public_key: str = "emptykey"
    secret_key: str = "emptykey"
    host: str = ""
    tracing_enabled: bool = False
    environment: str = "dev-whoami"


class AppSettings(BaseModel):
    """
    Core application settings for the API service.

    :param title: API title shown in docs.
    :param version: API version string.
    :param description: API description displayed in docs.
    :param api_base_url: Base path for all routes.
    :param host: Host address for Uvicorn server.
    :param port: Port number for Uvicorn server.
    :param live_reload: Enable Uvicorn live reload on changes.
    :param workers: Number of worker processes.
    :param proxy_headers: Trust proxy headers.
    :param forwarded_allow_ips: IPs allowed to be forwarded.
    :param root_path: Root path for mounting.
    :param timeout_keep_alive: Keep-alive timeout for connections.
    :param timeout_graceful_shutdown: Graceful shutdown timeout.
    :param limit_concurrency: Optional limit on concurrent requests.
    :param limit_max_requests: Optional max requests per worker.
    :param ssl_certfile: Optional path to SSL certificate file.
    :param ssl_keyfile: Optional path to SSL key file.
    """

    title: str = "Smart Integration Microservice"
    version: str = "0.1.0"
    git_commit: str = ""
    description: str = "Smart Integration Microservice for schema matching and mapping"
    api_base_url: str = "/api/v1"

    host: str = "0.0.0.0"
    port: int = 8090
    live_reload: bool = False
    workers: int = 1
    proxy_headers: bool = True
    forwarded_allow_ips: str = "*"
    root_path: str = ""
    timeout_keep_alive: int = 10
    timeout_graceful_shutdown: int = 15
    limit_concurrency: Optional[int] = None
    limit_max_requests: Optional[int] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None


class Settings(BaseSettings):
    """
    Application settings loaded from environment or defaults.

    Uses nested environment variables with '__' delimiter.

    Example: LOGGING__LEVEL=error
    """

    model_config = SettingsConfigDict(env_nested_delimiter="__")

    app: AppSettings = AppSettings()
    logging: LoggingSettings = LoggingSettings()
    llm: LLMSettings = LLMSettings()
    langfuse: LangfuseSettings = LangfuseSettings()


config = Settings()
