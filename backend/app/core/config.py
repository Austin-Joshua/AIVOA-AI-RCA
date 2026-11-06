from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import List, Optional
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "AIVOA.AI – RCA Intelligence"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database configuration
    # Default to PostgreSQL 16, with fail-fast enforcement
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://aivoa_user:aivoa_password@localhost:5432/aivoa_rca"
    )
    
    # LLM & AI configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_BACKUP_API_KEY: Optional[str] = os.getenv("GROQ_BACKUP_API_KEY", None)
    GROQ_PROJECT_ID: Optional[str] = os.getenv("GROQ_PROJECT_ID", None)
    GROQ_BACKUP_PROJECT_ID: Optional[str] = os.getenv("GROQ_BACKUP_PROJECT_ID", None)
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_MODEL_AUTODISCOVER: bool = os.getenv("GROQ_MODEL_AUTODISCOVER", "false").lower() in ("true", "1", "yes")

    @property
    def has_separate_groq_projects(self) -> bool:
        """Returns True only when primary and backup keys are explicitly assigned to different project IDs."""
        p1 = (self.GROQ_PROJECT_ID or "").strip()
        p2 = (self.GROQ_BACKUP_PROJECT_ID or "").strip()
        return bool(p1 and p2 and p1 != p2)
    
    # CORS Origin Allowlist (Explicit origins; wildcards forbidden when credentials enabled)
    CORS_ORIGINS: Optional[str] = None
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    @property
    def cors_origins(self) -> List[str]:
        raw = self.CORS_ORIGINS or os.getenv("CORS_ORIGINS")
        if raw:
            return [o.strip() for o in raw.split(",") if o.strip()]
        return self.BACKEND_CORS_ORIGINS
    
    # Safe database URL representation for logging and telemetry (masks credentials)
    @property
    def safe_database_url(self) -> str:
        if "@" in self.DATABASE_URL:
            return self.DATABASE_URL.split("@")[-1]
        return "configured"

    # Storage (Anchored absolutely to eliminate CWD dependency)
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", str(BACKEND_DIR / "uploads"))
    EVIDENCE_STORAGE_DIR: str = str((BACKEND_DIR / os.getenv("EVIDENCE_STORAGE_DIR", "storage/evidences")).resolve()) if not Path(os.getenv("EVIDENCE_STORAGE_DIR", "")).is_absolute() else os.getenv("EVIDENCE_STORAGE_DIR")
    MAX_UPLOAD_SIZE_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(10 * 1024 * 1024)))  # 10 MB default

    # Deployment Environment (development, test, production)
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    # Demo Account Provisioning (Controlled via explicit flag; strictly disabled in production)
    ENABLE_DEMO_PROVISIONING: bool = os.getenv("ENABLE_DEMO_PROVISIONING", "true").lower() in ("true", "1", "yes")
    ALLOW_DEMO_LOGIN: bool = os.getenv("ALLOW_DEMO_LOGIN", "false").lower() in ("true", "1", "yes")

    @property
    def allows_demo_seeding(self) -> bool:
        if self.is_production:
            return False
        return self.ENABLE_DEMO_PROVISIONING and self.ENVIRONMENT.lower() in ("development", "test")

    @property
    def demo_login_allowed(self) -> bool:
        if self.is_production:
            return False
        return self.ALLOW_DEMO_LOGIN and self.ENVIRONMENT.lower() != "production"

    # AI Request Rate Limiting
    AI_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("AI_RATE_LIMIT_PER_MINUTE", "20"))
    AI_RATE_LIMIT_PER_HOUR: int = int(os.getenv("AI_RATE_LIMIT_PER_HOUR", "200"))

    # Initial Admin Provisioning (Used solely for initial bootstrap; never hardcoded in production)
    INITIAL_ADMIN_USERNAME: Optional[str] = os.getenv("INITIAL_ADMIN_USERNAME", None)
    INITIAL_ADMIN_PASSWORD: Optional[str] = os.getenv("INITIAL_ADMIN_PASSWORD", None)
    INITIAL_ADMIN_EMAIL: Optional[str] = os.getenv("INITIAL_ADMIN_EMAIL", None)
    INITIAL_ADMIN_FULL_NAME: Optional[str] = os.getenv("INITIAL_ADMIN_FULL_NAME", None)

    # Authentication & Security
    # Hardcoded default signing-secret fallbacks have been removed.
    # Non-test execution strictly requires an explicit, cryptographically secure secret (>= 32 chars).
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))  # 24 hours

    @model_validator(mode="after")
    def validate_configuration(self) -> "Settings":
        """
        Enforce fail-fast security rules across environments:
        - In test environments: falls back to an isolated deterministic test secret if unset.
        - In non-test environments (development, production): requires an explicit, high-entropy SECRET_KEY (>= 32 chars).
        - Rejects insecure defaults, placeholders, and template values without leaking secret contents.
        - In production: strictly forbids development database credentials ('aivoa_password') and SQLite URLs.
        """
        env = self.ENVIRONMENT.lower().strip()

        # Handle test isolation fallback
        if env == "test":
            if not self.SECRET_KEY or not self.SECRET_KEY.strip():
                self.SECRET_KEY = "test-isolated-deterministic-signing-secret-key-32chars-minimum!"
            return self

        # Non-test environments (development, production) require explicit configuration
        if not self.SECRET_KEY or not self.SECRET_KEY.strip():
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY must be explicitly configured "
                "in environment or .env for non-test execution. Hardcoded defaults have been eliminated."
            )

        insecure_exact_defaults = {
            "secret",
            "changeme",
            "change_me",
            "password",
            "placeholder",
            "example",
            "default_secret",
            "aivoa-rca-secret-key-2026-pharma-gmp-demo",
            "replace_with_a_cryptographically_secure_random_key_in_production",
            "replace_with_a_cryptographically_secure_random_key_min_32_chars",
            "your_secret_key_here",
        }
        lower_secret = self.SECRET_KEY.strip().lower()
        if lower_secret in insecure_exact_defaults:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: Insecure placeholder or development default "
                "detected in SECRET_KEY. You must provide an explicit, independent cryptographically secure secret."
            )

        insecure_prefixes_and_substrings = [
            "aivoa-rca-secret-key-2026-pharma-gmp-demo",
            "replace_with_",
            "your_secret_key",
            "changeme",
            "change_me",
            "default_secret",
        ]
        for pattern in insecure_prefixes_and_substrings:
            if pattern in lower_secret:
                raise RuntimeError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: Insecure placeholder or development default "
                    "detected in SECRET_KEY. You must provide an explicit, independent cryptographically secure secret."
                )

        if len(self.SECRET_KEY.strip()) < 32:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY must be at least 32 characters in length "
                "to provide sufficient cryptographic entropy for HMAC-SHA256 signing."
            )

        if self.is_production:
            if "aivoa_password" in self.DATABASE_URL or "your_secure_db_password_here" in self.DATABASE_URL:
                raise RuntimeError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: In production mode (ENVIRONMENT='production'), "
                    "DATABASE_URL cannot use default development credentials or template placeholders."
                )
            if self.DATABASE_URL.startswith("sqlite"):
                raise RuntimeError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: In production mode, PostgreSQL 16 is mandatory. "
                    "SQLite URLs are strictly prohibited."
                )

        return self
    
    # Environment variable loading architecture:
    # 1. System environment variables (os.environ) hold highest priority.
    # 2. backend/.env overrides root .env for backend-specific settings.
    # 3. <root>/.env supplies base/shared variables (e.g. from Docker Compose).
    # Both paths are absolute to eliminate working directory ambiguity.
    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore",
        env_file=(
            str(ROOT_DIR / ".env"),
            str(BACKEND_DIR / ".env"),
        ),
    )

settings = Settings()

