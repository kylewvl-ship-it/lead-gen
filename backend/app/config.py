"""Configuration management with environment variables."""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


class Settings:
    """Application settings loaded from environment variables."""
    
    # Google Maps API
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    
    # API usage limits (to stay within free tier)
    MONTHLY_API_LIMIT: int = int(os.getenv("MONTHLY_API_LIMIT", "500"))
    
    # Firecrawl API
    FIRECRAWL_API_KEY: str = os.getenv("FIRECRAWL_API_KEY", "")
    FIRECRAWL_MONTHLY_LIMIT: int = int(os.getenv("FIRECRAWL_MONTHLY_LIMIT", "400"))
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./leads.db")
    
    def validate(self) -> list[str]:
        """Validate required settings. Returns list of errors."""
        errors = []
        if not self.GOOGLE_MAPS_API_KEY:
            errors.append("GOOGLE_MAPS_API_KEY is not set")
        if not self.FIRECRAWL_API_KEY:
            errors.append("FIRECRAWL_API_KEY is not set (company research/SEO disabled)")
        return errors


settings = Settings()
