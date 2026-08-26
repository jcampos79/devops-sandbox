"""
Application configuration.

Every environment-specific value is read from the environment (never
hard-coded) -- in-cluster these come from the ConfigMap/Secret the Helm
chart wires up; locally, from a `.env` file (see .env.example).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "sandbox"
    postgres_user: str = "sandbox"
    postgres_password: str = "changeme"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # --- Auth / secrets ---
    backend_secret_key: str = "dev-only-change-me"

    # --- Sandbox lifecycle ---
    sandbox_namespace_prefix: str = "sandbox-"
    max_instance_duration_minutes: int = 30
    cleanup_interval_seconds: int = 30
    ticket_ttl_seconds: int = 45

    # --- Sandbox distributions (image references, filled in via Helm values) ---
    sandbox_image_ubuntu: str = ""
    sandbox_image_rocky: str = ""
    sandbox_image_debian: str = ""
    sandbox_image_alpine: str = ""

    # Fixed platform resource profile -- never user-configurable.
    sandbox_cpu: str = "1"
    sandbox_memory: str = "512Mi"

    # --- Kubernetes client ---
    # Empty string -> use in-cluster config (the normal in-Kubernetes case).
    kubeconfig_path: str = ""

    # --- Misc ---
    log_level: str = "INFO"

    @property
    def supported_distributions(self) -> dict[str, str]:
        """Maps stable API distribution identifiers to configured images."""
        return {
            "ubuntu": self.sandbox_image_ubuntu,
            "rocky": self.sandbox_image_rocky,
            "debian": self.sandbox_image_debian,
            "alpine": self.sandbox_image_alpine,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
