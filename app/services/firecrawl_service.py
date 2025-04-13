import time
from flask import current_app
from datetime import datetime, timedelta
import json
from tqdm import tqdm  # For progress tracking
from app.models import SearchCache, UserSearchHistory, SearchResult
from app.extensions import db, cache
from pydantic import BaseModel, Field
from typing import List, Optional
from firecrawl import FirecrawlApp
import requests
import hashlib

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
    """Manager for Firecrawl API requests with rate limit handling"""
    
    def __init__(self):
        self.api_key = current_app.config.get('FIRECRAWL_API_KEY')
        self.base_url = current_app.config.get('FIRECRAWL_BASE_URL')
        self.daily_requests = 0
        self.daily_reset_time = datetime.now() + timedelta(days=1)
        # Free tier limit is 100 requests per day
        self.daily_limit = current_app.config.get('FIRECRAWL_DAILY_LIMIT', 100)
    
    def search(self, website, query):
        """Search a website using Firecrawl API"""
        self._check_rate_limit()
        
        url = f"{self.base_url}/v1/search"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "url": f"https://{website}",
            "query": query
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            self.daily_requests += 1
            return response.json()
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Search API error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 429:
                    raise RateLimitExceeded("Firecrawl API rate limit exceeded")
                elif e.response.status_code == 401:
                    raise AuthenticationError("Invalid Firecrawl API key")
            raise APIError(f"Firecrawl API error: {str(e)}")
    
    def extract(self, url, include_comments=True, summarize_comments=True):
        """Extract content from a URL with optional comment summarization"""
        self._check_rate_limit()
        
        extract_url = f"{self.base_url}/v1/extract"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "url": url,
            "include_comments": include_comments,
            "summarize_comments": summarize_comments
        }
        
        try:
            response = requests.post(extract_url, headers=headers, json=payload)
            response.raise_for_status()
            self.daily_requests += 1
            return response.json()
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Extract API error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 429:
                    raise RateLimitExceeded("Firecrawl API rate limit exceeded")
                elif e.response.status_code == 401:
                    raise AuthenticationError("Invalid Firecrawl API key")
            raise APIError(f"Firecrawl API error: {str(e)}")
    
    def _check_rate_limit(self):
        """Check if we've exceeded rate limits"""
        now = datetime.now()
        if now >= self.daily_reset_time:
            # Reset counter for new day
            self.daily_requests = 0
            self.daily_reset_time = now + timedelta(days=1)
            
        if self.daily_requests >= self.daily_limit:
            raise RateLimitExceeded("Daily API request limit reached")


# Custom exceptions
class APIError(Exception):
    """Base class for API errors"""
    pass

class RateLimitExceeded(APIError):
    """Raised when API rate limit is exceeded"""
    pass

class AuthenticationError(APIError):
    """Raised when API authentication fails"""
    pass

def get_cache_key(prefix, **kwargs):
    """Generate a cache key from prefix and kwargs"""
    key_dict = {k: v for k, v in sorted(kwargs.items())}
    key_str = json.dumps(key_dict, sort_keys=True)
    return f"{prefix}:{hashlib.md5(key_str.encode()).hexdigest()}"

@cache.memoize(timeout=86400)  # Cache for 24 hours
def search_website_cached(website, query, ranking_type="relevance"):
    """Cached version of the search function"""
    return search_website_internal(website, query, ranking_type)

def search_website(website, query, ranking_type="relevance"):
    """Public-facing search function that utilizes caching"""
    # Check if we're close to API limit and should prioritize cache
    api_manager = FirecrawlAPIManager()
    if api_manager.daily_requests > 90:  # 90% of free tier limit
        # Force cache usage when close to limits
        cache_key = get_cache_key("search", website=website, query=query, ranking_type=ranking_type)
        cached_result = cache.get(cache_key)
        if cached_result:
            current_app.logger.info("Using cached result due to API limit constraints")
            return cached_result
    
    # Normal cached function call
    return search_website_cached(website, query, ranking_type)

def search_website_internal(website, query, ranking_type="relevance"):
    """
    Internal implementation of website search with caching
    """
    api_manager = FirecrawlAPIManager()
    
    try:
        # Check cache first
        cache_key = get_cache_key("search", website=website, query=query, ranking_type=ranking_type)
        cached_result = cache.get(cache_key)
        if cached_result:
            current_app.logger.info("Using cached search result")
            return cached_result

        # Perform search request
        search_data = api_manager.search(website, query)
        
        # Process the search results
        results = []
        if 'results' in search_data:
            for item in search_data['results']:
                result = SearchResult(
                    title=item.get('title', 'No Title'),
                    url=item.get('url', ''),
                    rating=item.get('rating'),
                    image_url=item.get('imageUrl')
                )
                results.append(result)
        
        # If ratings-based ranking is requested, get detailed info including comments
        if ranking_type == "ratings" and results:
            # Limit to top 5 results to conserve API usage
            detailed_results = []
            for result in tqdm(results[:5], desc="Analyzing detailed results"):
                # Check cache for detailed result
                detail_cache_key = get_cache_key("detail", url=result.url)
                cached_detail = cache.get(detail_cache_key)
                
                if cached_detail:
                    current_app.logger.info("Using cached detailed result")
                    result = cached_detail
                else:
                    extract_data = api_manager.extract(
                        result.url, 
                        include_comments=True,
                        summarize_comments=True
                    )
                    
                    # Extract comment summaries if available
                    if 'commentSummary' in extract_data:
                        result.summary = extract_data['commentSummary'].get('summary', '')
                        result.pros = extract_data['commentSummary'].get('pros', [])
                        result.cons = extract_data['commentSummary'].get('cons', [])
                        result.tips = extract_data['commentSummary'].get('tips', [])
                    
                    # Update rating if available
                    if 'rating' in extract_data and extract_data['rating']:
                        result.rating = extract_data['rating']
                    
                    # Cache the detailed result
                    cache.set(detail_cache_key, result)
                
                detailed_results.append(result)
            
            # Sort by rating
            detailed_results.sort(key=lambda x: x.rating if x.rating else 0, reverse=True)
            results = detailed_results
        
        # Cache the final results
        cache.set(cache_key, results)
        return results
    
    except RateLimitExceeded as e:
        current_app.logger.error(f"Rate limit exceeded: {str(e)}")
        search_website.last_error = "Rate limit exceeded. Please try again tomorrow."
        return []
    except AuthenticationError as e:
        current_app.logger.error(f"Authentication error: {str(e)}")
        search_website.last_error = "API authentication failed. Please check your API key."
        return []
    except APIError as e:
        current_app.logger.error(f"API error: {str(e)}")
        search_website.last_error = f"An error occurred with the API: {str(e)}"
        return []
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        search_website.last_error = "An unexpected error occurred."
        return []

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