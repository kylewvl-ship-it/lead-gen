"""SQLite database setup with SQLAlchemy."""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

from .config import settings

# Create engine - for SQLite, check_same_thread=False is needed for FastAPI
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Search(Base):
    """Track search history and API usage."""
    __tablename__ = "searches"
    
    id = Column(Integer, primary_key=True, index=True)
    query = Column(String, nullable=False)  # e.g., "dentists"
    location = Column(String, nullable=False)  # e.g., "Cape Town, South Africa"
    radius_km = Column(Integer, default=10)
    results_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Business(Base):
    """Discovered businesses from Google Places."""
    __tablename__ = "businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    place_id = Column(String, unique=True, index=True)  # Google's unique ID
    name = Column(String, nullable=False)
    address = Column(String)
    phone = Column(String)
    website = Column(String)
    rating = Column(Float)
    review_count = Column(Integer)
    business_types = Column(String)  # JSON array of types
    latitude = Column(Float)
    longitude = Column(Float)
    search_id = Column(Integer)  # Which search found this
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def calculate_lead_score(self) -> int:
        """
        Calculate lead score based on business attributes.
        Higher score = better lead for web dev/marketing services.
        
        Scoring:
        - No website: +50 (hot lead!)
        - Rating >= 4.0: +20 (quality business)
        - Reviews >= 100: +15 (established business)
        - Has phone: +15 (contactable)
        
        Max score: 100
        """
        score = 0
        
        # No website = hot lead for web development services
        if not self.website:
            score += 50
        
        # High rating = quality business worth approaching
        if self.rating and self.rating >= 4.0:
            score += 20
        
        # Established business with reviews
        if self.review_count and self.review_count >= 100:
            score += 15
        
        # Has phone = easier to contact
        if self.phone:
            score += 15
        
        return score
    
    def to_dict(self):
        """Convert to dictionary for JSON response."""
        return {
            "id": self.id,
            "place_id": self.place_id,
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "website": self.website,
            "rating": self.rating,
            "review_count": self.review_count,
            "business_types": json.loads(self.business_types) if self.business_types else [],
            "latitude": self.latitude,
            "longitude": self.longitude,
            "lead_score": self.calculate_lead_score(),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class APIUsage(Base):
    """Track API usage to stay within free tier."""
    __tablename__ = "api_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    month = Column(String, nullable=False)  # Format: "2024-01"
    call_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)


class FirecrawlUsage(Base):
    """Track Firecrawl API usage to stay within free tier."""
    __tablename__ = "firecrawl_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    month = Column(String, nullable=False)  # Format: "2024-01"
    credit_count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)


class CompanyResearch(Base):
    """Store company research data from Firecrawl."""
    __tablename__ = "company_research"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, index=True)  # Links to Business.id
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    # Basic info
    page_title = Column(String)
    meta_description = Column(Text)
    
    # Contact info
    emails = Column(Text)  # JSON array
    phones = Column(Text)  # JSON array
    
    # Social media
    social_links = Column(Text)  # JSON object
    
    # Technical
    technologies = Column(Text)  # JSON array
    
    # Raw content (for future analysis)
    raw_markdown = Column(Text)
    
    def to_dict(self):
        """Convert to dictionary for JSON response."""
        return {
            "id": self.id,
            "business_id": self.business_id,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "page_title": self.page_title,
            "meta_description": self.meta_description,
            "emails": json.loads(self.emails) if self.emails else [],
            "phones": json.loads(self.phones) if self.phones else [],
            "social_links": json.loads(self.social_links) if self.social_links else {},
            "technologies": json.loads(self.technologies) if self.technologies else [],
        }


class SEOAnalysis(Base):
    """Store SEO analysis results."""
    __tablename__ = "seo_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, index=True)  # Links to Business.id
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    
    # Scores (0-100)
    overall_score = Column(Float)
    title_score = Column(Float)
    meta_score = Column(Float)
    heading_score = Column(Float)
    content_score = Column(Float)
    image_score = Column(Float)
    link_score = Column(Float)
    technical_score = Column(Float)
    
    # Grade (A+, A, B, C, D, F)
    grade = Column(String(2))
    
    # Detailed data
    metrics = Column(Text)  # JSON object
    issues = Column(Text)  # JSON array
    recommendations = Column(Text)  # JSON array
    
    def to_dict(self):
        """Convert to dictionary for JSON response."""
        return {
            "id": self.id,
            "business_id": self.business_id,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
            "overall_score": self.overall_score,
            "grade": self.grade,
            "scores": {
                "title": self.title_score,
                "meta": self.meta_score,
                "headings": self.heading_score,
                "content": self.content_score,
                "images": self.image_score,
                "links": self.link_score,
                "technical": self.technical_score,
            },
            "metrics": json.loads(self.metrics) if self.metrics else {},
            "issues": json.loads(self.issues) if self.issues else [],
            "recommendations": json.loads(self.recommendations) if self.recommendations else [],
        }


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
