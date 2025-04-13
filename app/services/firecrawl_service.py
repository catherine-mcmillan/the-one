import time
from flask import current_app
from datetime import datetime, timedelta
import json
from tqdm import tqdm  # For progress tracking
from app.models import SearchCache, UserSearchHistory, SearchResult
from app.extensions import db
from pydantic import BaseModel, Field
from typing import List, Optional
from firecrawl import FirecrawlApp

# DEVELOPMENT MODE SETTINGS - REMOVE IN PRODUCTION
DEV_MODE = True  # Set to False in production
MAX_RESULTS_DEV = 2  # Limit results during development (1 credit per page)
USE_SMALLER_MODEL = True  # Use smaller model for development
CACHE_DURATION = timedelta(hours=24)  # Cache results for 24 hours

class ProductSchema(BaseModel):
    """Schema for product information"""
    title: str
    url: str
    rating: Optional[float] = None
    image_url: Optional[str] = None
    summary: Optional[str] = None
    pros: Optional[List[str]] = None
    cons: Optional[List[str]] = None
    tips: Optional[List[str]] = None

class SearchResultsSchema(BaseModel):
    """Schema for list of search results"""
    results: List[ProductSchema] = Field(..., max_items=10)

class FirecrawlAPIManager:
    """Manager for Firecrawl API requests that handles rate limits"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.app = FirecrawlApp(api_key=api_key)
        self.daily_requests = 0
        self.daily_reset_time = datetime.now() + timedelta(days=1)
        # Free tier limit is 100 requests per day
        self.daily_limit = 100
    
    def _check_rate_limit(self):
        """Check if we're within rate limits and reset counter if needed"""
        now = datetime.now()
        if now >= self.daily_reset_time:
            # Reset counter for new day
            self.daily_requests = 0
            self.daily_reset_time = now + timedelta(days=1)
            
        if self.daily_requests >= self.daily_limit:
            raise Exception("Daily API request limit reached")
    
    def search(self, website, query):
        """
        Perform a search request to Firecrawl using the extraction endpoint
        
        Args:
            website (str): Website domain to search
            query (str): Search query
            
        Returns:
            dict: API response
        """
        self._check_rate_limit()
        
        # First, navigate to the search page and perform the search
        search_actions = [
            {"type": "wait", "milliseconds": 2000},
            {"type": "click", "selector": "input[type='search']"},
            {"type": "wait", "milliseconds": 1000},
            {"type": "write", "text": query},
            {"type": "wait", "milliseconds": 1000},
            {"type": "press", "key": "ENTER"},
            {"type": "wait", "milliseconds": 3000},
            {"type": "scrape"}
        ]
        
        try:
            data = self.app.extract(
                [f"https://{website}"],
                {
                    "prompt": f"Extract search results for {query} from the page, including title, URL, rating, and any available product information",
                    "schema": SearchResultsSchema.model_json_schema(),
                    "actions": search_actions
                }
            )
            self.daily_requests += 1
            return data
        except Exception as e:
            current_app.logger.error(f"Firecrawl API error: {str(e)}")
            return {"error": str(e)}
    
    def extract(self, url):
        """
        Extract detailed information from a specific URL
        
        Args:
            url (str): Specific URL to extract content from
            
        Returns:
            dict: API response
        """
        self._check_rate_limit()
        
        # Add actions to ensure we're on the product page and content is loaded
        extract_actions = [
            {"type": "wait", "milliseconds": 2000},
            {"type": "scroll", "selector": "body", "amount": "full"},
            {"type": "wait", "milliseconds": 1000},
            {"type": "scrape"}
        ]
        
        try:
            data = self.app.extract(
                [url],
                {
                    "prompt": "Extract detailed product information including title, rating, pros, cons, and tips from user reviews",
                    "schema": ProductSchema.model_json_schema(),
                    "actions": extract_actions
                }
            )
            self.daily_requests += 1
            return data
        except Exception as e:
            current_app.logger.error(f"Firecrawl API error: {str(e)}")
            return {"error": str(e)}

def search_website(website, query, ranking_type='relevance'):
    """Search a specific website for recipes"""
    try:
        # Check cache first
        query_hash = str(hash(f"{website}:{query}"))
        cached = SearchCache.query.filter_by(
            query_hash=query_hash,
            website=website
        ).first()
        
        if cached and cached.expires_at > datetime.utcnow():
            results = json.loads(cached.results)
            current_app.logger.info(f"Serving cached results for {query_hash}")
            return results
        
        # If not in cache, perform search
        results = api_manager.search(website, query, ranking_type)
        
        # Cache the results
        cache_results(website, query, results)
        
        return results
    except Exception as e:
        logger.error(f"Error searching website {website}: {str(e)}")
        raise

def cache_results(website, query, results):
    """Cache the search results"""
    expires_at = datetime.utcnow() + CACHE_DURATION
    results_json = json.dumps(results)
    
    # Generate a unique hash for the query
    query_hash = str(hash(f"{website}:{query}"))
    
    cache_entry = SearchCache(
        website=website,
        query=query,
        query_hash=query_hash,
        results=results_json,
        expires_at=expires_at
    )
    
    db.session.add(cache_entry)
    db.session.commit()

def save_to_user_history(user_id, website, query, results):
    """Save search results to user's history"""
    results_json = json.dumps(results)
    
    history_entry = UserSearchHistory(
        user_id=user_id,
        website=website,
        search_query=query,
        results=results_json
    )
    
    db.session.add(history_entry)
    db.session.commit()

def get_detailed_results(basic_results, website):
    """
    Get detailed information for each result including comment summaries
    
    Args:
        basic_results (list): List of basic search results
        website (str): Website domain
        
    Returns:
        list: Enhanced search results with comments analysis
    """
    # DEVELOPMENT MODE: Skip detailed results in dev to save credits
    if DEV_MODE:
        return basic_results[:MAX_RESULTS_DEV]  # Return limited results in dev
        
    api_key = current_app.config.get('FIRECRAWL_API_KEY')
    base_url = current_app.config.get('FIRECRAWL_BASE_URL')
    
    extract_url = f"{base_url}/v1/extract"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    enhanced_results = []
    
    for result in tqdm(basic_results, desc="Analyzing detailed results"):
        try:
            payload = {
                "url": result['url'],
                "include_comments": True,
                "summarize_comments": True,
                # DEVELOPMENT MODE OPTIMIZATIONS - REMOVE IN PRODUCTION
                "format": "basic" if DEV_MODE else "json",  # Basic format uses fewer credits
                "max_comments": 3 if DEV_MODE else None,  # Limit comments in dev
                "token_limit": 1000 if DEV_MODE else None  # Limit tokens in dev
            }
            
            response = requests.post(extract_url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract comment summaries and organization
            if 'commentSummary' in data:
                result['summary'] = data['commentSummary'].get('summary', '')
                result['pros'] = data['commentSummary'].get('pros', [])
                result['cons'] = data['commentSummary'].get('cons', [])
                result['tips'] = data['commentSummary'].get('tips', [])
            
            # Update rating if available in detailed data
            if 'rating' in data and data['rating']:
                result['rating'] = data['rating']
                
            enhanced_results.append(result)
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error getting details for {result['url']}: {str(e)}")
            enhanced_results.append(result)  # Add the basic result without enhancements
    
    # Sort by rating if available
    enhanced_results.sort(key=lambda x: x.get('rating', 0), reverse=True)
    
    return enhanced_results

def get_best_results(results, ranking_type="relevance"):
    """
    Process and rank search results based on ranking type
    
    Args:
        results (list): List of search results
        ranking_type (str): 'relevance' or 'ratings'
        
    Returns:
        list: Top results, possibly reordered
    """
    if not results:
        return []
    
    # DEVELOPMENT MODE: Return fewer results in dev
    max_results = MAX_RESULTS_DEV if DEV_MODE else 10
    
    if ranking_type == "relevance":
        return results[:max_results]
    else:
        # Sort by rating if available
        results.sort(key=lambda x: x.get('rating', 0), reverse=True)
        return results[:max_results]