# backend/agents/trend_agent.py
import logging
from typing import List
from crewai import Agent
from pytrends.request import TrendReq
from backend.config import settings

logger = logging.getLogger("vyaparai.agents.trend_agent")

def get_trending_keywords(product_name: str, location: str = "IN") -> List[str]:
    """Helper to fetch trending terms using pytrends with robust fallbacks."""
    keywords = []
    try:
        pytrends = TrendReq(hl="en-US", tz=330, timeout=(10, 25))
        # Get suggestions from Google Trends autocomplete
        suggestions = pytrends.suggestions(product_name)
        if suggestions:
            keywords = [s["title"].lower() for s in suggestions[:5]]
            
        # If no autocomplete terms, search interest by region / related topics
        if not keywords:
            pytrends.build_payload([product_name[:20]], timeframe="today 3-m", geo=location)
            related_queries = pytrends.related_queries()
            if product_name in related_queries and related_queries[product_name]["top"] is not None:
                top_queries = related_queries[product_name]["top"]
                keywords = top_queries["query"].head(5).tolist()
    except Exception as e:
        logger.warning(f"Google Trends query failed/rate-limited: {e}. Falling back to default keywords.")
        
    # Standard Indian micro-business trending tags fallback
    if not keywords:
        keywords = [
            f"best {product_name}",
            f"buy {product_name} online",
            f"organic {product_name}" if "food" in product_name.lower() or "oil" in product_name.lower() else f"handmade {product_name}",
            f"{product_name} near me",
            f"{product_name} shop"
        ]
    return keywords

def make_trend_agent() -> Agent:
    return Agent(
        role="SEO Trend Analyst",
        goal="Discover trending SEO keywords and search terms for a given product and target location in India.",
        backstory="""You are a seasoned digital marketer who understands the Indian local retail market. 
You specialize in finding what local customers are searching for on Google, YouTube, and WhatsApp, and extracting high-traffic, low-competition keywords.""",
        verbose=True,
        allow_delegation=False
    )
