"""SEO Analysis service for website auditing."""
import logging
import re
from typing import Optional
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)


class SEOAnalyzer:
    """
    Analyzes website HTML for SEO issues and opportunities.
    
    Scoring breakdown (100 points total):
    - Title & Meta: 20 points
    - Headings: 15 points
    - Content: 15 points
    - Images: 15 points
    - Links: 15 points
    - Technical: 20 points
    """
    
    def __init__(self, html: str, url: str):
        """
        Initialize analyzer with HTML content.
        
        Args:
            html: Raw HTML content of the page
            url: The URL of the page (for link analysis)
        """
        self.html = html
        self.url = url
        self.soup = BeautifulSoup(html, "lxml") if html else None
        self.parsed_url = urlparse(url)
        self.domain = self.parsed_url.netloc
        
        # Store analysis results
        self.issues = []
        self.recommendations = []
        self.metrics = {}
    
    def analyze(self) -> dict:
        """
        Run full SEO analysis and return comprehensive report.
        
        Returns:
            Dictionary containing scores, issues, and recommendations
        """
        if not self.soup:
            return {
                "success": False,
                "error": "No HTML content to analyze",
                "overall_score": 0
            }
        
        # Run all analysis components
        title_score = self._analyze_title()
        meta_score = self._analyze_meta()
        heading_score = self._analyze_headings()
        content_score = self._analyze_content()
        image_score = self._analyze_images()
        link_score = self._analyze_links()
        technical_score = self._analyze_technical()
        
        # Calculate overall score
        overall_score = (
            title_score * 0.10 +
            meta_score * 0.10 +
            heading_score * 0.15 +
            content_score * 0.15 +
            image_score * 0.15 +
            link_score * 0.15 +
            technical_score * 0.20
        )
        
        # Sort issues by severity
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        self.issues.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 3))
        
        return {
            "success": True,
            "url": self.url,
            "analyzed_at": datetime.utcnow().isoformat(),
            "overall_score": round(overall_score, 1),
            "scores": {
                "title": round(title_score, 1),
                "meta": round(meta_score, 1),
                "headings": round(heading_score, 1),
                "content": round(content_score, 1),
                "images": round(image_score, 1),
                "links": round(link_score, 1),
                "technical": round(technical_score, 1)
            },
            "metrics": self.metrics,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "grade": self._score_to_grade(overall_score)
        }
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"
    
    def _analyze_title(self) -> float:
        """Analyze page title tag."""
        score = 100
        title_tag = self.soup.find("title")
        title = title_tag.get_text().strip() if title_tag else ""
        
        self.metrics["title"] = title
        self.metrics["title_length"] = len(title)
        
        if not title:
            score = 0
            self.issues.append({
                "severity": "critical",
                "category": "title",
                "message": "Missing title tag",
                "impact": "Title is crucial for search rankings and click-through rates"
            })
            self.recommendations.append("Add a descriptive title tag between 50-60 characters")
        elif len(title) < 30:
            score -= 30
            self.issues.append({
                "severity": "warning",
                "category": "title",
                "message": f"Title too short ({len(title)} characters)",
                "impact": "Short titles may not fully describe your page content"
            })
            self.recommendations.append("Expand your title to 50-60 characters")
        elif len(title) > 60:
            score -= 20
            self.issues.append({
                "severity": "warning",
                "category": "title",
                "message": f"Title too long ({len(title)} characters)",
                "impact": "Title will be truncated in search results"
            })
            self.recommendations.append("Shorten your title to under 60 characters")
        
        return max(0, score)
    
    def _analyze_meta(self) -> float:
        """Analyze meta description and other meta tags."""
        score = 100
        
        # Meta description
        meta_desc = self.soup.find("meta", attrs={"name": "description"})
        description = meta_desc.get("content", "").strip() if meta_desc else ""
        
        self.metrics["meta_description"] = description
        self.metrics["meta_description_length"] = len(description)
        
        if not description:
            score -= 40
            self.issues.append({
                "severity": "critical",
                "category": "meta",
                "message": "Missing meta description",
                "impact": "Search engines may generate their own snippet"
            })
            self.recommendations.append("Add a compelling meta description of 150-160 characters")
        elif len(description) < 120:
            score -= 20
            self.issues.append({
                "severity": "warning",
                "category": "meta",
                "message": f"Meta description too short ({len(description)} characters)",
                "impact": "Not utilizing full snippet space in search results"
            })
        elif len(description) > 160:
            score -= 15
            self.issues.append({
                "severity": "info",
                "category": "meta",
                "message": f"Meta description too long ({len(description)} characters)",
                "impact": "Description will be truncated in search results"
            })
        
        # Canonical URL
        canonical = self.soup.find("link", attrs={"rel": "canonical"})
        self.metrics["has_canonical"] = canonical is not None
        if not canonical:
            score -= 15
            self.issues.append({
                "severity": "warning",
                "category": "meta",
                "message": "Missing canonical URL",
                "impact": "May cause duplicate content issues"
            })
            self.recommendations.append("Add a canonical link to prevent duplicate content issues")
        
        # Robots meta
        robots = self.soup.find("meta", attrs={"name": "robots"})
        robots_content = robots.get("content", "") if robots else ""
        self.metrics["robots_meta"] = robots_content
        
        if "noindex" in robots_content.lower():
            self.issues.append({
                "severity": "critical",
                "category": "meta",
                "message": "Page is set to noindex",
                "impact": "Page will not appear in search results"
            })
        
        # Open Graph
        og_title = self.soup.find("meta", attrs={"property": "og:title"})
        og_image = self.soup.find("meta", attrs={"property": "og:image"})
        self.metrics["has_og_tags"] = og_title is not None
        
        if not og_title:
            score -= 10
            self.issues.append({
                "severity": "info",
                "category": "meta",
                "message": "Missing Open Graph tags",
                "impact": "Social media shares may not display optimally"
            })
        
        return max(0, score)
    
    def _analyze_headings(self) -> float:
        """Analyze heading structure (H1-H6)."""
        score = 100
        
        h1_tags = self.soup.find_all("h1")
        h2_tags = self.soup.find_all("h2")
        h3_tags = self.soup.find_all("h3")
        
        self.metrics["h1_count"] = len(h1_tags)
        self.metrics["h2_count"] = len(h2_tags)
        self.metrics["h3_count"] = len(h3_tags)
        self.metrics["h1_text"] = [h.get_text().strip()[:100] for h in h1_tags]
        
        if len(h1_tags) == 0:
            score -= 50
            self.issues.append({
                "severity": "critical",
                "category": "headings",
                "message": "Missing H1 tag",
                "impact": "H1 is the most important on-page SEO element"
            })
            self.recommendations.append("Add a single, descriptive H1 tag to your page")
        elif len(h1_tags) > 1:
            score -= 25
            self.issues.append({
                "severity": "warning",
                "category": "headings",
                "message": f"Multiple H1 tags ({len(h1_tags)} found)",
                "impact": "Having multiple H1s can dilute page focus"
            })
            self.recommendations.append("Use only one H1 per page")
        
        if len(h2_tags) == 0:
            score -= 20
            self.issues.append({
                "severity": "warning",
                "category": "headings",
                "message": "No H2 tags found",
                "impact": "H2 tags help structure content for users and search engines"
            })
        
        return max(0, score)
    
    def _analyze_content(self) -> float:
        """Analyze page content quality."""
        score = 100
        
        # Get text content
        for script in self.soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        text = self.soup.get_text(separator=" ", strip=True)
        words = text.split()
        word_count = len(words)
        
        self.metrics["word_count"] = word_count
        
        if word_count < 100:
            score -= 50
            self.issues.append({
                "severity": "critical",
                "category": "content",
                "message": f"Thin content ({word_count} words)",
                "impact": "Pages with very little content struggle to rank"
            })
            self.recommendations.append("Add more comprehensive, valuable content (aim for 300+ words minimum)")
        elif word_count < 300:
            score -= 25
            self.issues.append({
                "severity": "warning",
                "category": "content",
                "message": f"Limited content ({word_count} words)",
                "impact": "More content often correlates with better rankings"
            })
        
        # Check for paragraphs
        paragraphs = self.soup.find_all("p")
        self.metrics["paragraph_count"] = len(paragraphs)
        
        if len(paragraphs) < 3:
            score -= 15
            self.issues.append({
                "severity": "info",
                "category": "content",
                "message": "Few paragraphs detected",
                "impact": "Well-structured content is easier to read"
            })
        
        return max(0, score)
    
    def _analyze_images(self) -> float:
        """Analyze images for SEO best practices."""
        score = 100
        
        images = self.soup.find_all("img")
        self.metrics["image_count"] = len(images)
        
        images_without_alt = []
        images_without_src = []
        
        for img in images:
            src = img.get("src", "")
            alt = img.get("alt", "")
            
            if not src:
                images_without_src.append(img)
            if not alt or alt.strip() == "":
                images_without_alt.append(src[:50] if src else "unknown")
        
        self.metrics["images_without_alt"] = len(images_without_alt)
        
        if len(images) > 0:
            missing_alt_ratio = len(images_without_alt) / len(images)
            
            if missing_alt_ratio > 0.5:
                score -= 40
                self.issues.append({
                    "severity": "critical",
                    "category": "images",
                    "message": f"{len(images_without_alt)} of {len(images)} images missing alt text",
                    "impact": "Alt text is crucial for accessibility and image SEO"
                })
                self.recommendations.append("Add descriptive alt text to all images")
            elif missing_alt_ratio > 0:
                score -= 20
                self.issues.append({
                    "severity": "warning",
                    "category": "images",
                    "message": f"{len(images_without_alt)} images missing alt text",
                    "impact": "Some images may not be indexed or accessible"
                })
        
        # Check for lazy loading
        lazy_images = self.soup.find_all("img", loading="lazy")
        self.metrics["lazy_loading_images"] = len(lazy_images)
        
        if len(images) > 5 and len(lazy_images) == 0:
            score -= 10
            self.issues.append({
                "severity": "info",
                "category": "images",
                "message": "No lazy-loaded images detected",
                "impact": "Lazy loading improves page performance"
            })
        
        return max(0, score)
    
    def _analyze_links(self) -> float:
        """Analyze internal and external links."""
        score = 100
        
        links = self.soup.find_all("a", href=True)
        
        internal_links = []
        external_links = []
        broken_links = []  # Links with empty or invalid hrefs
        
        for link in links:
            href = link.get("href", "").strip()
            
            if not href or href == "#" or href.startswith("javascript:"):
                broken_links.append(href)
                continue
            
            # Check if internal or external
            if href.startswith("/") or href.startswith("#"):
                internal_links.append(href)
            elif self.domain in href:
                internal_links.append(href)
            elif href.startswith("http"):
                external_links.append(href)
            else:
                internal_links.append(href)
        
        self.metrics["internal_links"] = len(internal_links)
        self.metrics["external_links"] = len(external_links)
        self.metrics["broken_links"] = len(broken_links)
        
        if len(internal_links) < 3:
            score -= 25
            self.issues.append({
                "severity": "warning",
                "category": "links",
                "message": "Few internal links",
                "impact": "Internal linking helps distribute page authority"
            })
            self.recommendations.append("Add more internal links to related content")
        
        if len(broken_links) > 0:
            score -= min(30, len(broken_links) * 5)
            self.issues.append({
                "severity": "warning",
                "category": "links",
                "message": f"{len(broken_links)} potentially broken links",
                "impact": "Broken links hurt user experience and crawlability"
            })
        
        # Check for links with no text
        empty_links = [l for l in links if not l.get_text().strip() and not l.find("img")]
        if len(empty_links) > 0:
            score -= 10
            self.issues.append({
                "severity": "info",
                "category": "links",
                "message": f"{len(empty_links)} links without anchor text",
                "impact": "Descriptive anchor text helps SEO"
            })
        
        return max(0, score)
    
    def _analyze_technical(self) -> float:
        """Analyze technical SEO factors."""
        score = 100
        
        # Check for viewport meta tag (mobile-friendliness indicator)
        viewport = self.soup.find("meta", attrs={"name": "viewport"})
        self.metrics["has_viewport"] = viewport is not None
        
        if not viewport:
            score -= 30
            self.issues.append({
                "severity": "critical",
                "category": "technical",
                "message": "Missing viewport meta tag",
                "impact": "Page may not be mobile-friendly"
            })
            self.recommendations.append("Add viewport meta tag for mobile responsiveness")
        
        # Check for SSL (based on URL)
        is_https = self.url.startswith("https://")
        self.metrics["is_https"] = is_https
        
        if not is_https:
            score -= 25
            self.issues.append({
                "severity": "critical",
                "category": "technical",
                "message": "Site not using HTTPS",
                "impact": "Google prioritizes secure sites in rankings"
            })
            self.recommendations.append("Migrate to HTTPS for better security and rankings")
        
        # Check charset
        charset = self.soup.find("meta", charset=True)
        self.metrics["has_charset"] = charset is not None
        
        if not charset:
            score -= 10
            self.issues.append({
                "severity": "info",
                "category": "technical",
                "message": "Missing charset declaration",
                "impact": "May cause character encoding issues"
            })
        
        # Check for lang attribute
        html_tag = self.soup.find("html")
        has_lang = html_tag.get("lang") if html_tag else None
        self.metrics["has_lang"] = has_lang is not None
        
        if not has_lang:
            score -= 10
            self.issues.append({
                "severity": "info",
                "category": "technical",
                "message": "Missing lang attribute on HTML tag",
                "impact": "Helps search engines understand page language"
            })
        
        # Estimate page size
        page_size_kb = len(self.html) / 1024
        self.metrics["page_size_kb"] = round(page_size_kb, 2)
        
        if page_size_kb > 500:
            score -= 15
            self.issues.append({
                "severity": "warning",
                "category": "technical",
                "message": f"Large HTML size ({round(page_size_kb)} KB)",
                "impact": "Large pages load slower and may affect rankings"
            })
        
        # Check for structured data
        schema_scripts = self.soup.find_all("script", type="application/ld+json")
        self.metrics["has_structured_data"] = len(schema_scripts) > 0
        
        if len(schema_scripts) == 0:
            score -= 10
            self.issues.append({
                "severity": "info",
                "category": "technical",
                "message": "No structured data (Schema.org) found",
                "impact": "Structured data can enhance search result appearance"
            })
            self.recommendations.append("Add Schema.org structured data for rich snippets")
        
        return max(0, score)
