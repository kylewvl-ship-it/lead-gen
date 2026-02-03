"""API router for company research using Firecrawl."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from app.database import get_db, Business, CompanyResearch
from services.firecrawl_api import (
    FirecrawlService,
    FirecrawlError,
    FirecrawlLimitExceeded
)

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("/usage")
def get_firecrawl_usage(db: Session = Depends(get_db)):
    """Get current Firecrawl API usage statistics."""
    try:
        service = FirecrawlService(db)
        return service.get_usage_stats()
    except FirecrawlError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{business_id}")
def run_company_research(business_id: int, db: Session = Depends(get_db)):
    """
    Run company research on a business's website.
    
    Scrapes the website using Firecrawl and extracts:
    - Social media links
    - Contact emails and phones
    - Technologies used
    - Page metadata
    """
    # Get the business
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    if not business.website:
        raise HTTPException(
            status_code=400,
            detail="Business has no website to research"
        )
    
    try:
        service = FirecrawlService(db)
        
        # Scrape the website
        scraped = service.scrape_website(business.website)
        
        # Extract company info
        company_info = service.extract_company_info(scraped)
        
        # Check if we already have research for this business
        existing = db.query(CompanyResearch).filter(
            CompanyResearch.business_id == business_id
        ).first()
        
        if existing:
            # Update existing record
            existing.page_title = company_info.get("title")
            existing.meta_description = company_info.get("description")
            existing.emails = json.dumps(company_info.get("emails", []))
            existing.phones = json.dumps(company_info.get("phones", []))
            existing.social_links = json.dumps(company_info.get("social_links", {}))
            existing.technologies = json.dumps(company_info.get("technologies", []))
            existing.raw_markdown = scraped.get("markdown", "")[:50000]  # Limit size
            research = existing
        else:
            # Create new record
            research = CompanyResearch(
                business_id=business_id,
                page_title=company_info.get("title"),
                meta_description=company_info.get("description"),
                emails=json.dumps(company_info.get("emails", [])),
                phones=json.dumps(company_info.get("phones", [])),
                social_links=json.dumps(company_info.get("social_links", {})),
                technologies=json.dumps(company_info.get("technologies", [])),
                raw_markdown=scraped.get("markdown", "")[:50000]  # Limit size
            )
            db.add(research)
        
        db.commit()
        db.refresh(research)
        
        return {
            "success": True,
            "business_id": business_id,
            "business_name": business.name,
            "website": business.website,
            "research": research.to_dict(),
            "usage": service.get_usage_stats()
        }
        
    except FirecrawlLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except FirecrawlError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{business_id}")
def get_company_research(business_id: int, db: Session = Depends(get_db)):
    """Get stored company research for a business."""
    # Get the business
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get research
    research = db.query(CompanyResearch).filter(
        CompanyResearch.business_id == business_id
    ).first()
    
    if not research:
        raise HTTPException(
            status_code=404,
            detail="No research found for this business. Run POST /api/research/{id} first."
        )
    
    return {
        "business_id": business_id,
        "business_name": business.name,
        "website": business.website,
        "research": research.to_dict()
    }
