"""
Centralized application configuration
"""
import os
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # ============================================
    # Application Settings
    # ============================================
    APP_NAME: str = "Wedding Reservation API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"

    # ============================================
    # Database Settings
    # ============================================
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://postgres:032023@localhost:5432/wedding_db")

    # ============================================
    # Security Settings
    # ============================================
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey2")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Super Admin Default Password
    SUPER_ADMIN_PASSWORD: str = os.getenv(
        "SUPER_ADMIN_PASSWORD", "M.superadmin")

    # ============================================
    # CORS Settings
    # ============================================
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # ============================================
    # Twilio SMS Settings
    # ============================================
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    TWILIO_ENABLED: bool = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN)

    # ============================================
    # Server Settings
    # ============================================
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    WORKERS: int = int(os.getenv("WEB_CONCURRENCY", 2))

    # ============================================
    # Rate Limiting
    # ============================================
    RATE_LIMIT_ENABLED: bool = ENVIRONMENT == "production"
    RATE_LIMIT_PER_MINUTE: int = 60

    # ============================================
    # File Upload Settings
    # ============================================
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".pdf"]

    class Config:
        case_sensitive = True
        env_file = ".env"

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"

    def validate_settings(self) -> List[str]:
        """Validate critical settings and return warnings"""
        warnings = []

        if self.is_production:
            if self.SECRET_KEY == "supersecretkey2":
                warnings.append(
                    "⚠️ CRITICAL: Using default SECRET_KEY in production!")

            if self.SUPER_ADMIN_PASSWORD == "M.superadmin":
                warnings.append(
                    "⚠️ WARNING: Using default super admin password!")

            if not self.TWILIO_ENABLED:
                warnings.append("⚠️ WARNING: Twilio SMS is not configured!")

            if self.DATABASE_URL.startswith("sqlite"):
                warnings.append("⚠️ WARNING: Using SQLite in production!")

        return warnings


# Create global settings instance
settings = Settings()

# Validate settings on import
validation_warnings = settings.validate_settings()
if validation_warnings:
    print("\n" + "="*60)
    print("⚠️  CONFIGURATION WARNINGS:")
    for warning in validation_warnings:
        print(f"  {warning}")
    print("="*60 + "\n")

# Print configuration summary in development
if settings.is_development:
    print("\n" + "="*60)
    print("🔧 DEVELOPMENT CONFIGURATION:")
    print(f"  Environment: {settings.ENVIRONMENT}")
    print(f"  Database: {settings.DATABASE_URL[:50]}...")
    print(f"  Secret Key: {'***' + settings.SECRET_KEY[-4:]}")
    print(f"  Twilio Enabled: {settings.TWILIO_ENABLED}")
    print(f"  CORS Origins: {settings.CORS_ORIGINS}")
    print("="*60 + "\n")
