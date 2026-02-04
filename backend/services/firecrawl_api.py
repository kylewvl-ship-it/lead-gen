"""Firecrawl API integration for company research and website scraping."""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)


class FirecrawlError(Exception):
    """Custom exception for Firecrawl API errors."""
    pass


class FirecrawlLimitExceeded(Exception):
    """Raised when monthly Firecrawl limit is reached."""
    pass


class FirecrawlService:
    """Service for interacting with Firecrawl API."""
    
    def __init__(self, db: Session):
        self.db = db
        if not settings.FIRECRAWL_API_KEY:
            raise FirecrawlError("Firecrawl API key not configured")
        
        # Import here to avoid issues if firecrawl not installed
        from firecrawl import Firecrawl
        self.client = Firecrawl(api_key=settings.FIRECRAWL_API_KEY)
    
    def _get_current_month(self) -> str:
        """Get current month string for tracking."""
        return datetime.utcnow().strftime("%Y-%m")
    
    def _check_usage_limit(self) -> tuple[int, int]:
        """Check if we're within usage limits. Returns (current_count, limit)."""
        from app.database import FirecrawlUsage
        
        month = self._get_current_month()
        usage = self.db.query(FirecrawlUsage).filter(
            FirecrawlUsage.month == month
        ).first()
        
        current_count = usage.credit_count if usage else 0
        return current_count, settings.FIRECRAWL_MONTHLY_LIMIT
    
    def _increment_usage(self, credits: int = 1):
        """Increment usage counter."""
        from app.database import FirecrawlUsage
        
        month = self._get_current_month()
        usage = self.db.query(FirecrawlUsage).filter(
            FirecrawlUsage.month == month
        ).first()
        
        if usage:
            usage.credit_count += credits
            usage.last_updated = datetime.utcnow()
        else:
            usage = FirecrawlUsage(month=month, credit_count=credits)
            self.db.add(usage)
        
        self.db.commit()
    
    def get_usage_stats(self) -> dict:
        """Get current Firecrawl usage statistics."""
        current, limit = self._check_usage_limit()
        return {
            "month": self._get_current_month(),
            "credits_used": current,
            "credits_limit": limit,
            "credits_remaining": max(0, limit - current),
            "percentage_used": round((current / limit) * 100, 1) if limit > 0 else 0
        }
    
    def scrape_website(self, url: str) -> dict:
        """
        Scrape a website using Firecrawl.
        
        Args:
            url: The website URL to scrape
            
        Returns:
            Dictionary with scraped content and metadata
        """
        # Check usage limit
        current, limit = self._check_usage_limit()
        if current >= limit:
            raise FirecrawlLimitExceeded(
                f"Monthly Firecrawl limit reached ({current}/{limit}). "
                f"Limit resets next month."
            )
        
        try:
            # Scrape the website
            result = self.client.scrape(
                url,
                formats=['markdown', 'html'],
                only_main_content=True,
                wait_for=2000,  # Wait for JS to render
            )
            
            # Increment usage
            self._increment_usage(1)
            
            # Handle both dict and Pydantic model responses
            if hasattr(result, 'model_dump'):
                result = result.model_dump()
            elif hasattr(result, '__dict__') and not isinstance(result, dict):
                result = vars(result)
            
            # Extract relevant data
            metadata = result.get("metadata", {}) or {}
            if hasattr(metadata, 'model_dump'):
                metadata = metadata.model_dump()
            elif hasattr(metadata, '__dict__') and not isinstance(metadata, dict):
                metadata = vars(metadata)
            
            return {
                "success": True,
                "url": url,
                "title": metadata.get("title", "") or "",
                "description": metadata.get("description", "") or "",
                "markdown": result.get("markdown", "") or "",
                "html": result.get("html", "") or "",
                "metadata": metadata,
                "scraped_at": datetime.utcnow().isoformat(),
                "usage": self.get_usage_stats()
            }
            
        except Exception as e:
            logger.error(f"Firecrawl scrape failed for {url}: {e}")
            raise FirecrawlError(f"Failed to scrape website: {str(e)}")
    
    def extract_company_info(self, scraped_data: dict) -> dict:
        """
        Extract company information from scraped website data.
        
        Args:
            scraped_data: Data returned from scrape_website()
            
        Returns:
            Dictionary with extracted company information
        """
        from bs4 import BeautifulSoup
        import re
        
        html = scraped_data.get("html", "")
        metadata = scraped_data.get("metadata", {})
        
        soup = BeautifulSoup(html, "lxml") if html else None
        
        # Extract social media links
        social_links = {}
        if soup:
            social_patterns = {
                "facebook": r"facebook\.com",
                "twitter": r"(twitter\.com|x\.com)",
                "linkedin": r"linkedin\.com",
                "instagram": r"instagram\.com",
                "youtube": r"youtube\.com",
            }
            
            for link in soup.find_all("a", href=True):
                href = link["href"].lower()
                for platform, pattern in social_patterns.items():
                    if re.search(pattern, href) and platform not in social_links:
                        social_links[platform] = link["href"]
        
        # Extract email addresses
        emails = []
        if html:
            email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            found_emails = re.findall(email_pattern, html)
            # Filter out common non-contact emails
            exclude_patterns = ["example.com", "domain.com", "email.com", "test.com"]
            emails = list(set([
                e for e in found_emails 
                if not any(p in e.lower() for p in exclude_patterns)
            ]))[:5]  # Limit to 5 emails
        
        # Extract phone numbers
        phones = []
        if html:
            phone_pattern = r"[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}"
            found_phones = re.findall(phone_pattern, html)
            phones = list(set([
                p.strip() for p in found_phones 
                if len(p.replace(" ", "").replace("-", "")) >= 10
            ]))[:3]  # Limit to 3 phones
        
        # Detect technologies (basic detection)
        technologies = []
        tech_signatures = {
            "WordPress": ["wp-content", "wp-includes", "wordpress"],
            "Shopify": ["shopify", "cdn.shopify"],
            "Wix": ["wix.com", "wixsite"],
            "Squarespace": ["squarespace"],
            "React": ["react", "__next"],
            "Vue.js": ["vue", "nuxt"],
            "jQuery": ["jquery"],
            "Bootstrap": ["bootstrap"],
            "Google Analytics": ["google-analytics", "gtag"],
            "Google Tag Manager": ["googletagmanager"],
            "Facebook Pixel": ["facebook.net/en_US/fbevents"],
        }
        
        html_lower = html.lower() if html else ""
        for tech, signatures in tech_signatures.items():
            if any(sig in html_lower for sig in signatures):
                technologies.append(tech)
        
        return {
            "title": scraped_data.get("title", ""),
            "description": scraped_data.get("description", ""),
            "social_links": social_links,
            "emails": emails,
            "phones": phones,
            "technologies": technologies,
            "og_image": metadata.get("ogImage", ""),
            "favicon": metadata.get("favicon", ""),
            "language": metadata.get("language", ""),
        }
