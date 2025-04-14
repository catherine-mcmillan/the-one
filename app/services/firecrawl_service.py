import time
from flask import current_app
from datetime import datetime, timedelta
import json
from tqdm import tqdm  # For progress tracking
from app.models import SearchCache, UserSearchHistory, SearchResult
from app.extensions import db, cache
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from firecrawl import FirecrawlApp
import requests
import hashlib
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
import backoff  # For exponential backoff
import gc  # For garbage collection
import logging
import threading
import psutil  # For memory monitoring
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('firecrawl_service')

# DEVELOPMENT MODE SETTINGS - REMOVE IN PRODUCTION
DEV_MODE = True  # Set to False in production
MAX_RESULTS_DEV = 2  # Limit results during development (1 credit per page)
USE_SMALLER_MODEL = True  # Use smaller model for development
CACHE_DURATION = timedelta(hours=24)  # Cache results for 24 hours
REQUEST_TIMEOUT = 600  # 10 minutes for complex searches
MAX_RETRIES = 3
RETRY_DELAY = 30  # 30 seconds between retries
BACKOFF_FACTOR = 2  # Exponential backoff factor
MAX_CONCURRENT_REQUESTS = 1  # Limit concurrent requests to avoid concurrency limits
MEMORY_THRESHOLD = 70  # 70% memory usage threshold

class RecipeResult(BaseModel):
    """Model for recipe search results"""
    title: str
    rating: Optional[float] = None
    description: str
    url: Optional[str] = None
    imageUrl: Optional[str] = None
    summary: Optional[str] = None
    prosCons: Optional[Dict[str, str]] = None
    tipsTricks: Optional[str] = None
    keyTakeaways: Optional[str] = None
    uniqueAspect: Optional[str] = None

class SearchResponse(BaseModel):
    """Model for the search response"""
    success: bool
    data: Dict[str, Any]  # Changed from List[RecipeResult] to Dict[str, Any]
    status: str
    expiresAt: str

class SearchResultItem(BaseModel):
    """Schema for individual search results"""
    rank: float = Field(description="Ranking of the result")
    title: str = Field(description="Title of the result")
    summary: str = Field(description="Summary of the result")
    big_difference: Optional[str] = Field(None, description="What makes this result unique")
    key_takeaways: Optional[str] = Field(None, description="Key takeaways from the result")
    pros: Optional[str] = Field(None, description="Positive aspects")
    cons: Optional[str] = Field(None, description="Negative aspects")
    tips_and_tricks: Optional[str] = Field(None, description="Tips and tricks")
    url: Optional[str] = Field(None, description="URL of the result")
    image_url: Optional[str] = Field(None, description="Image URL if available")
    rating: Optional[float] = Field(None, description="Rating if available")

class ExtractSchema(BaseModel):
    """Schema for detailed content extraction"""
    title: str = Field(description="Title of the content")
    summary: str = Field(description="Detailed summary")
    big_difference: Optional[str] = Field(None, description="What makes this unique")
    key_takeaways: Optional[str] = Field(None, description="Key takeaways")
    pros: Optional[str] = Field(None, description="Positive aspects")
    cons: Optional[str] = Field(None, description="Negative aspects")
    tips_and_tricks: Optional[str] = Field(None, description="Tips and tricks")
    rating: Optional[float] = Field(None, description="Rating if available")
    url: Optional[str] = Field(None, description="URL of the result")
    image_url: Optional[str] = Field(None, description="Image URL if available")

class NestedModel(BaseModel):
    """Schema for individual search results"""
    rank: float = Field(description="Ranking of the result")
    title: str = Field(description="Title of the result")
    summary: str = Field(description="Summary of the result")
    big_difference: Optional[str] = Field(None, description="What makes this result unique")
    key_takeaways: Optional[str] = Field(None, description="Key takeaways from the result")
    pros: Optional[str] = Field(None, description="Positive aspects")
    cons: Optional[str] = Field(None, description="Negative aspects")
    tips_and_tricks: Optional[str] = Field(None, description="Tips and tricks")
    url: Optional[str] = Field(None, description="URL of the result")
    image_url: Optional[str] = Field(None, description="Image URL if available")
    rating: Optional[float] = Field(None, description="Rating if available")

class ResultsContainer(BaseModel):
    """Container for results with dynamic key"""
    results: List[NestedModel] = Field(description="List of search results")

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

class FirecrawlAPIManager:
    """Manager for Firecrawl API requests with rate limit handling"""
    
    def __init__(self):
        self.api_key = current_app.config.get('FIRECRAWL_API_KEY')
        self.app = FirecrawlApp(api_key=self.api_key)
        self.daily_requests = 0
        self.daily_reset_time = datetime.now() + timedelta(days=1)
        self.daily_limit = current_app.config.get('FIRECRAWL_DAILY_LIMIT', 100)
        self.executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS)
        self._request_semaphore = threading.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    def _check_memory_usage(self):
        """Check if memory usage is too high"""
        memory_percent = psutil.Process().memory_percent()
        if memory_percent > MEMORY_THRESHOLD:
            logger.warning(f"Memory usage {memory_percent}% exceeds threshold {MEMORY_THRESHOLD}%")
            gc.collect()  # Force garbage collection
            time.sleep(5)  # Wait for memory to be freed
    
    def _log_api_response(self, response, operation):
        """Log detailed API response information"""
        try:
            if isinstance(response, dict):
                logger.info(f"Firecrawl {operation} Response: {json.dumps(response, indent=2)}")
                if 'error' in response:
                    logger.error(f"Firecrawl {operation} Error: {response['error']}")
                if 'status' in response:
                    logger.info(f"Firecrawl {operation} Status: {response['status']}")
                if 'message' in response:
                    logger.info(f"Firecrawl {operation} Message: {response['message']}")
            elif isinstance(response, list):
                logger.info(f"Firecrawl {operation} Response: {json.dumps(response, indent=2)}")
            else:
                logger.warning(f"Unexpected response type in {operation}: {type(response)}")
                logger.warning(f"Response content: {str(response)}")
        except Exception as e:
            logger.error(f"Error logging API response: {str(e)}")
    
    @backoff.on_exception(backoff.expo, 
                         (APIError, TimeoutError, requests.exceptions.RequestException),
                         max_tries=MAX_RETRIES,
                         max_time=REQUEST_TIMEOUT)
    def _execute_with_timeout(self, func, *args, **kwargs):
        """Execute a function with a timeout and exponential backoff retries"""
        with self._request_semaphore:
            try:
                self._check_memory_usage()
                logger.info(f"Starting Firecrawl API request: {func.__name__}")
                future = self.executor.submit(func, *args, **kwargs)
                result = future.result(timeout=REQUEST_TIMEOUT)
                
                # Log the API response
                self._log_api_response(result, func.__name__)
                
                # Force garbage collection after each request
                gc.collect()
                return result
            except TimeoutError:
                logger.warning("Request timed out, retrying with backoff")
                raise
            except Exception as e:
                logger.error(f"API request failed: {str(e)}")
                if "concurrency" in str(e).lower():
                    logger.error("Concurrency limit reached, waiting before retry")
                    time.sleep(RETRY_DELAY * 3)  # Wait longer for concurrency issues
                elif "500" in str(e):
                    logger.error("Server error (500), waiting before retry")
                    time.sleep(RETRY_DELAY * 2)
                raise APIError(f"API request failed: {str(e)}")
    
    def search(self, website, query):
        """Search a website using Firecrawl API with improved error handling"""
        self._check_rate_limit()
        
        try:
            logger.info(f"Starting search for '{query}' on {website}")
            
            # Use the SDK to perform the search with wildcard URL
            data = self._execute_with_timeout(
                self.app.extract,
                [f"https://{website}/*"],
                {
                    'prompt': f'Search for the top 5 results related to "{query}" on {website}. For each result, provide:\n'
                             f'1. A clear title\n'
                             f'2. A detailed summary\n'
                             f'3. What makes this result unique (big difference)\n'
                             f'4. Key takeaways\n'
                             f'5. Pros and cons\n'
                             f'6. Tips and tricks\n'
                             f'7. Rating if available\n'
                             f'8. URL and image URL if available',
                    'schema': SearchResponse.model_json_schema(),
                    'enable_web_search': True,
                    'max_results': 5,
                    'include_comments': True,
                    'summarize_comments': True,
                    'timeout': REQUEST_TIMEOUT,  # Pass timeout to API
                    'retry_on_error': True,  # Enable retry on error
                    'max_retries': 3  # Maximum number of retries for the API
                }
            )
            
            self.daily_requests += 1
            logger.info(f"Search completed successfully. Daily requests: {self.daily_requests}")
            
            # Parse and validate response against our schema
            try:
                search_response = SearchResponse(**data)
                return search_response.dict()
            except Exception as e:
                logger.warning(f"Failed to parse response as SearchResponse: {str(e)}")
                logger.warning(f"Raw response: {json.dumps(data, indent=2)}")
                return data  # Return raw data if parsing fails
            
        except Exception as e:
            logger.error(f"Search API error: {str(e)}")
            if "concurrency" in str(e).lower():
                logger.error("Concurrency limit reached, using cached results if available")
                cache_key = get_cache_key("search", website=website, query=query)
                cached_result = cache.get(cache_key)
                if cached_result:
                    logger.info("Using cached result due to concurrency limit")
                    return cached_result
            elif "500" in str(e):
                logger.error("Server error (500), using cached results if available")
                cache_key = get_cache_key("search", website=website, query=query)
                cached_result = cache.get(cache_key)
                if cached_result:
                    logger.info("Using cached result due to API error")
                    return cached_result
            raise APIError(f"Firecrawl API error: {str(e)}")
    
    def extract(self, url, include_comments=True, summarize_comments=True):
        """Extract content from a URL with optional comment analysis"""
        self._check_rate_limit()
        
        try:
            # Use the SDK to extract content
            data = self._execute_with_timeout(
                self.app.extract,
                [url],
                {
                    'prompt': 'Extract detailed information from this page, including any user comments or reviews. Provide:\n'
                             '1. A clear title\n'
                             '2. A detailed summary\n'
                             f'3. What makes this result unique (big difference)\n'
                             f'4. Key takeaways\n'
                             f'5. Pros and cons\n'
                             f'6. Tips and tricks\n'
                             f'7. Rating if available',
                    'schema': NestedModel.model_json_schema(),
                    'enable_web_search': True,
                    'include_comments': include_comments,
                    'summarize_comments': summarize_comments
                }
            )
            
            self.daily_requests += 1
            
            # Parse and validate response against our schema
            result = NestedModel(**data)
            return result.dict()
            
        except Exception as e:
            current_app.logger.error(f"Extract API error: {str(e)}")
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
        cache_key = get_cache_key("search", website=website, query=query)
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
        response = api_manager.search(website, query)
        
        # For debugging - log the raw response
        current_app.logger.debug(f"Raw API response: {json.dumps(response, indent=2)}")
        
        # Process results into a consistent format
        processed_results = []
        
        # Handle the response based on its type
        if isinstance(response, list):
            # If response is already a list of results
            for idx, item in enumerate(response, start=1):
                result = {
                    "rank": idx,
                    "title": getattr(item, 'title', "Untitled"),
                    "summary": getattr(item, 'summary', ""),
                    "big_difference": getattr(item, 'big_difference', ""),
                    "key_takeaways": getattr(item, 'key_takeaways', []),
                    "pros": getattr(item, 'pros', []),
                    "cons": getattr(item, 'cons', []),
                    "tips_and_tricks": getattr(item, 'tips_and_tricks', []),
                    "url": getattr(item, 'url', ""),
                    "image_url": getattr(item, 'image_url', ""),
                    "rating": float(getattr(item, 'rating', 0)) if getattr(item, 'rating', None) else None
                }
                processed_results.append(result)
        elif isinstance(response, dict):
            # If response is a dictionary
            data = response.get('data', {})
            if isinstance(data, dict):
                inner_data = data.get('data', {})
                if isinstance(inner_data, dict):
                    # Handle the main result
                    result = {
                        "rank": 1,
                        "title": inner_data.get("title", "Untitled"),
                        "summary": inner_data.get("summary", ""),
                        "big_difference": inner_data.get("big_difference", ""),
                        "key_takeaways": inner_data.get("key_takeaways", []),
                        "pros": inner_data.get("pros", []),
                        "cons": inner_data.get("cons", []),
                        "tips_and_tricks": inner_data.get("tips", []),
                        "url": inner_data.get("url", ""),
                        "image_url": inner_data.get("image_url", ""),
                        "rating": float(inner_data.get("rating", 0)) if inner_data.get("rating") else None
                    }
                    processed_results.append(result)
                    
                    # Handle additional results
                    results = inner_data.get('results', [])
                    if isinstance(results, list):
                        for idx, item in enumerate(results, start=2):
                            result = {
                                "rank": idx,
                                "title": item.get("title", "Untitled"),
                                "summary": item.get("summary", ""),
                                "big_difference": item.get("big_difference", ""),
                                "key_takeaways": item.get("key_takeaways", []),
                                "pros": item.get("pros", []),
                                "cons": item.get("cons", []),
                                "tips_and_tricks": item.get("tips", []),
                                "url": item.get("url", ""),
                                "image_url": item.get("image_url", ""),
                                "rating": float(item.get("rating", 0)) if item.get("rating") else None
                            }
                            processed_results.append(result)
        else:
            # If response is neither list nor dict, return it as is for debugging
            current_app.logger.warning(f"Unexpected response type: {type(response)}")
            return [{"raw_response": str(response)}]
        
        # If ratings-based ranking is requested, sort by rating
        if ranking_type == "ratings":
            processed_results.sort(key=lambda x: x.get('rating', 0) or 0, reverse=True)
        
        # Cache the results
        cache.set(cache_key, processed_results)
        return processed_results
    
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
        current_app.logger.error(f"Unexpected error in search_website_internal: {str(e)}")
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
            if not result.get('url'):
                enhanced_results.append(result)
                continue
                
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
                result['pros'] = data['commentSummary'].get('pros', '')
                result['cons'] = data['commentSummary'].get('cons', '')
                result['tips'] = data['commentSummary'].get('tips', '')
            
            # Update rating if available in detailed data
            if 'rating' in data and data['rating']:
                result['rating'] = data['rating']
                
            enhanced_results.append(result)
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error getting details for {result.get('url', 'unknown URL')}: {str(e)}")
            enhanced_results.append(result)  # Add the basic result without enhancements
    
    # Sort by rating if available
    enhanced_results.sort(key=lambda x: x.get('rating', 0) or 0, reverse=True)
    
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
        results.sort(key=lambda x: x.get('rating', 0) or 0, reverse=True)
        return results[:max_results]

class FirecrawlService:
    def __init__(self):
        self.api_key = os.getenv('FIRECRAWL_API_KEY')
        if not self.api_key:
            raise ValueError("FIRECRAWL_API_KEY not found in environment variables")
        self.app = FirecrawlApp(api_key=self.api_key)
        self.executor = ThreadPoolExecutor(max_workers=1)

    def _check_memory_usage(self):
        """Check memory usage and trigger garbage collection if needed"""
        import psutil
        import gc
        
        process = psutil.Process()
        memory_percent = process.memory_percent()
        
        if memory_percent > MEMORY_THRESHOLD:
            logger.warning(f"Memory usage high: {memory_percent:.1f}%")
            gc.collect()
            memory_percent = process.memory_percent()
            logger.info(f"Memory after cleanup: {memory_percent:.1f}%")

    def _execute_with_timeout(self, func, *args, **kwargs):
        """Execute a function with timeout and retry logic"""
        self._check_memory_usage()
        
        for attempt in range(MAX_RETRIES):
            try:
                future = self.executor.submit(func, *args, **kwargs)
                return future.result(timeout=REQUEST_TIMEOUT)
            except TimeoutError:
                logger.warning(f"Request timed out (attempt {attempt + 1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    raise
            except Exception as e:
                logger.error(f"Error during request: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    raise

    def _log_api_response(self, response: Dict[str, Any], is_complex: bool = False):
        """Log API response details"""
        search_type = "Complex" if is_complex else "Simple"
        logger.info(f"{search_type} Search Response:")
        logger.info(f"Status: {response.get('status')}")
        logger.info(f"Success: {response.get('success')}")
        
        if 'data' in response:
            for category, items in response['data'].items():
                logger.info(f"Found {len(items)} items in {category}")
                for item in items:
                    logger.info(f"Title: {item.get('title', 'N/A')}")
                    logger.info(f"Rating: {item.get('rating', 'N/A')}")
                    if is_complex:
                        logger.info(f"Summary: {item.get('summary', 'N/A')}")
                        logger.info(f"Unique Aspect: {item.get('uniqueAspect', 'N/A')}")
                    logger.info("---")

    def _process_api_response(self, response: Dict[str, Any]) -> List[RecipeResult]:
        """Process the API response and extract recipe results"""
        try:
            # First level validation
            search_response = SearchResponse(**response)
            
            if not search_response.success:
                logger.warning("API response indicated failure")
                return []
            
            # Extract recipes from the nested data structure
            recipes = []
            
            # The response has a nested structure: response -> data -> data -> results
            if isinstance(search_response.data, dict):
                inner_data = search_response.data.get('data', {})
                if isinstance(inner_data, dict):
                    # Handle the main recipe data
                    main_recipe = {
                        'title': inner_data.get('title', ''),
                        'description': inner_data.get('summary', ''),
                        'rating': float(inner_data.get('rating', 0)) if inner_data.get('rating') else None,
                        'url': inner_data.get('url'),
                        'imageUrl': inner_data.get('image_url'),
                        'summary': inner_data.get('summary'),
                        'prosCons': {
                            'pros': inner_data.get('pros', ''),
                            'cons': inner_data.get('cons', '')
                        },
                        'tipsTricks': inner_data.get('tips'),
                        'keyTakeaways': inner_data.get('key_takeaways'),
                        'uniqueAspect': inner_data.get('unique')
                    }
                    recipes.append(RecipeResult(**main_recipe))
                    
                    # Handle additional results if present
                    results = inner_data.get('results', [])
                    if isinstance(results, list):
                        for result in results:
                            try:
                                recipe = RecipeResult(
                                    title=result.get('title', ''),
                                    description=result.get('summary', ''),
                                    rating=float(result.get('rating', 0)) if result.get('rating') else None,
                                    url=result.get('url'),
                                    imageUrl=result.get('image_url'),
                                    summary=result.get('summary'),
                                    prosCons={
                                        'pros': result.get('pros', ''),
                                        'cons': result.get('cons', '')
                                    },
                                    tipsTricks=result.get('tips'),
                                    keyTakeaways=result.get('key_takeaways'),
                                    uniqueAspect=result.get('unique')
                                )
                                recipes.append(recipe)
                            except Exception as e:
                                logger.error(f"Error processing additional recipe: {str(e)}")
                                continue
            
            logger.info(f"Successfully processed {len(recipes)} recipes")
            return recipes
            
        except Exception as e:
            logger.error(f"Error processing API response: {str(e)}")
            logger.error(f"Response structure: {json.dumps(response, indent=2)}")
            return []

    def search(self, website: str, query: str, max_results: int = 3) -> List[RecipeResult]:
        """Perform a simple search"""
        try:
            logger.info(f"Starting simple search for '{query}' on {website}")
            
            response = self._execute_with_timeout(
                self.app.extract,
                [f"https://{website}/*"],
                {
                    'prompt': f'Find the top {max_results} {query} recipes on {website}. For each recipe, provide:\n'
                             f'1. Recipe title\n'
                             f'2. Brief description\n'
                             f'3. Rating if available',
                    'enable_web_search': True,
                    'max_results': max_results,
                    'include_comments': False,
                    'summarize_comments': False,
                    'timeout': REQUEST_TIMEOUT,
                    'retry_on_error': True,
                    'max_retries': MAX_RETRIES
                }
            )
            
            self._log_api_response(response)
            
            # Process the response
            recipes = []
            if response.get('success'):
                data = response.get('data', {})
                if isinstance(data, dict):
                    inner_data = data.get('data', {})
                    if isinstance(inner_data, dict):
                        # Handle the main recipe
                        main_recipe = {
                            'title': inner_data.get('title', ''),
                            'description': inner_data.get('summary', ''),
                            'rating': float(inner_data.get('rating', 0)) if inner_data.get('rating') else None,
                            'url': inner_data.get('url'),
                            'imageUrl': inner_data.get('image_url'),
                            'summary': inner_data.get('summary'),
                            'prosCons': {
                                'pros': inner_data.get('pros', ''),
                                'cons': inner_data.get('cons', '')
                            },
                            'tipsTricks': inner_data.get('tips'),
                            'keyTakeaways': inner_data.get('key_takeaways'),
                            'uniqueAspect': inner_data.get('unique')
                        }
                        recipes.append(RecipeResult(**main_recipe))
                        
                        # Handle additional results
                        results = inner_data.get('results', [])
                        if isinstance(results, list):
                            for result in results:
                                try:
                                    recipe = RecipeResult(
                                        title=result.get('title', ''),
                                        description=result.get('summary', ''),
                                        rating=float(result.get('rating', 0)) if result.get('rating') else None,
                                        url=result.get('url'),
                                        imageUrl=result.get('image_url'),
                                        summary=result.get('summary'),
                                        prosCons={
                                            'pros': result.get('pros', ''),
                                            'cons': result.get('cons', '')
                                        },
                                        tipsTricks=result.get('tips'),
                                        keyTakeaways=result.get('key_takeaways'),
                                        uniqueAspect=result.get('unique')
                                    )
                                    recipes.append(recipe)
                                except Exception as e:
                                    logger.error(f"Error processing additional recipe: {str(e)}")
                                    continue
            
            logger.info(f"Successfully processed {len(recipes)} recipes")
            return recipes
            
        except Exception as e:
            logger.error(f"Error during simple search: {str(e)}")
            raise

    def extract(self, website: str, query: str, max_results: int = 3) -> List[RecipeResult]:
        """Perform a complex search with detailed summaries"""
        try:
            logger.info(f"Starting complex search for '{query}' on {website}")
            
            response = self._execute_with_timeout(
                self.app.extract,
                [f"https://{website}/*"],
                {
                    'prompt': f'Search for the top {max_results} {query} recipes on {website}. For each recipe, provide:\n'
                             f'1. A clear title\n'
                             f'2. A detailed summary\n'
                             f'3. What makes this recipe unique (big difference)\n'
                             f'4. Key takeaways\n'
                             f'5. Pros and cons\n'
                             f'6. Tips and tricks\n'
                             f'7. Rating if available\n'
                             f'8. URL and image URL if available',
                    'enable_web_search': True,
                    'max_results': max_results,
                    'include_comments': True,
                    'summarize_comments': True,
                    'timeout': REQUEST_TIMEOUT,
                    'retry_on_error': True,
                    'max_retries': MAX_RETRIES
                }
            )
            
            self._log_api_response(response, is_complex=True)
            return self._process_api_response(response)
            
        except Exception as e:
            logger.error(f"Error during complex search: {str(e)}")
            raise