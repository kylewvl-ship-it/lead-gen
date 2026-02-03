"""API router for SEO analysis."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from app.database import get_db, Business, SEOAnalysis
from services.firecrawl_api import (
    FirecrawlService,
    FirecrawlError,
    FirecrawlLimitExceeded
)
from services.seo_analyzer import SEOAnalyzer

router = APIRouter(prefix="/api/seo", tags=["seo"])


@router.post("/analyze/{business_id}")
def run_seo_analysis(business_id: int, db: Session = Depends(get_db)):
    """
    Run SEO analysis on a business's website.
    
    Analyzes:
    - Title and meta tags
    - Heading structure
    - Content quality
    - Image optimization
    - Link analysis
    - Technical SEO factors
    
    Returns a score (0-100) and grade (A+ to F) with detailed issues.
    """
    # Get the business
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    if not business.website:
        raise HTTPException(
            status_code=400,
            detail="Business has no website to analyze"
        )
    
    try:
        # Use Firecrawl to get the HTML
        firecrawl = FirecrawlService(db)
        scraped = firecrawl.scrape_website(business.website)
        
        # Run SEO analysis
        analyzer = SEOAnalyzer(
            html=scraped.get("html", ""),
            url=business.website
        )
        report = analyzer.analyze()
        
        if not report.get("success"):
            raise HTTPException(
                status_code=500,
                detail=report.get("error", "Analysis failed")
            )
        
        # Check if we already have analysis for this business
        existing = db.query(SEOAnalysis).filter(
            SEOAnalysis.business_id == business_id
        ).first()
        
        scores = report.get("scores", {})
        
        if existing:
            # Update existing record
            existing.overall_score = report.get("overall_score")
            existing.title_score = scores.get("title")
            existing.meta_score = scores.get("meta")
            existing.heading_score = scores.get("headings")
            existing.content_score = scores.get("content")
            existing.image_score = scores.get("images")
            existing.link_score = scores.get("links")
            existing.technical_score = scores.get("technical")
            existing.grade = report.get("grade")
            existing.metrics = json.dumps(report.get("metrics", {}))
            existing.issues = json.dumps(report.get("issues", []))
            existing.recommendations = json.dumps(report.get("recommendations", []))
            analysis = existing
        else:
            # Create new record
            analysis = SEOAnalysis(
                business_id=business_id,
                overall_score=report.get("overall_score"),
                title_score=scores.get("title"),
                meta_score=scores.get("meta"),
                heading_score=scores.get("headings"),
                content_score=scores.get("content"),
                image_score=scores.get("images"),
                link_score=scores.get("links"),
                technical_score=scores.get("technical"),
                grade=report.get("grade"),
                metrics=json.dumps(report.get("metrics", {})),
                issues=json.dumps(report.get("issues", [])),
                recommendations=json.dumps(report.get("recommendations", []))
            )
            db.add(analysis)
        
        db.commit()
        db.refresh(analysis)
        
        return {
            "success": True,
            "business_id": business_id,
            "business_name": business.name,
            "website": business.website,
            "analysis": analysis.to_dict(),
            "firecrawl_usage": firecrawl.get_usage_stats()
        }
        
    except FirecrawlLimitExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except FirecrawlError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{business_id}")
def get_seo_analysis(business_id: int, db: Session = Depends(get_db)):
    """Get stored SEO analysis for a business."""
    # Get the business
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get analysis
    analysis = db.query(SEOAnalysis).filter(
        SEOAnalysis.business_id == business_id
    ).first()
    
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="No SEO analysis found. Run POST /api/seo/analyze/{id} first."
        )
    
    return {
        "business_id": business_id,
        "business_name": business.name,
        "website": business.website,
        "analysis": analysis.to_dict()
    }


@router.get("/issues/{business_id}")
def get_seo_issues(business_id: int, db: Session = Depends(get_db)):
    """Get prioritized SEO issues for a business."""
    # Get the business
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get analysis
    analysis = db.query(SEOAnalysis).filter(
        SEOAnalysis.business_id == business_id
    ).first()
    
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="No SEO analysis found. Run POST /api/seo/analyze/{id} first."
        )
    
    issues = json.loads(analysis.issues) if analysis.issues else []
    recommendations = json.loads(analysis.recommendations) if analysis.recommendations else []
    
    # Group issues by severity
    critical = [i for i in issues if i.get("severity") == "critical"]
    warnings = [i for i in issues if i.get("severity") == "warning"]
    info = [i for i in issues if i.get("severity") == "info"]
    
    return {
        "business_id": business_id,
        "business_name": business.name,
        "overall_score": analysis.overall_score,
        "grade": analysis.grade,
        "summary": {
            "critical_count": len(critical),
            "warning_count": len(warnings),
            "info_count": len(info),
            "total_issues": len(issues)
        },
        "critical_issues": critical,
        "warnings": warnings,
        "info": info,
        "recommendations": recommendations
    }
