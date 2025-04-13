import requests
from flask import current_app
from datetime import datetime, timedelta
import json
from tqdm import tqdm  # For progress tracking
from app.models import SearchCache, UserSearchHistory, SearchResult
from app.extensions import db

# DEVELOPMENT MODE SETTINGS - REMOVE IN PRODUCTION
DEV_MODE = True  # Set to False in production
MAX_RESULTS_DEV = 2  # Limit results during development (1 credit per page)
USE_SMALLER_MODEL = True  # Use smaller model for development
CACHE_DURATION = timedelta(hours=24)  # Cache results for 24 hours

def search_website(website, query, ranking_type="relevance", save_to_history=False, user_id=None):
    """
    Search for products/content on the specified website using Firecrawl API
    
    Args:
        website (str): Website to search (e.g., allrecipes.com)
        query (str): Search query
        ranking_type (str): 'relevance' or 'ratings'
        save_to_history (bool): Whether to save to user's history
        user_id (int): User ID if saving to history
        
    Returns:
        list: List of search results
    """
    # Check cache first
    cache_key = f"{website}:{query}"
    cached_results = SearchCache.query.filter_by(
        website=website,
        query=query
    ).first()
    
    if cached_results and not cached_results.is_expired:
        results = json.loads(cached_results.results)
        current_app.logger.info(f"Serving cached results for {cache_key}")
        
        if save_to_history and user_id:
            save_to_user_history(user_id, website, query, results)
            
        return results
    
    api_key = current_app.config.get('FIRECRAWL_API_KEY')
    base_url = current_app.config.get('FIRECRAWL_BASE_URL')
    
    # Construct URL for the search API endpoint
    search_url = f"{base_url}/v1/search"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "url": f"https://{website}",
        "query": query,
        "max_results": MAX_RESULTS_DEV if DEV_MODE else 10,
        "format": "basic" if DEV_MODE else "json"
    }
    
    try:
        with tqdm(total=1, desc="Searching website") as pbar:
            response = requests.post(search_url, headers=headers, json=payload)
            response.raise_for_status()  # Raise an exception for HTTP errors
            pbar.update(1)
        
        data = response.json()
        
        # Process the search results
        results = []
        if 'results' in data:
            for item in data['results']:
                result = {
                    'title': item.get('title', 'No Title'),
                    'url': item.get('url', ''),
                    'rating': item.get('rating'),
                    'image_url': item.get('imageUrl')
                }
                results.append(result)
        
        # If ratings-based ranking is requested, get additional details
        if ranking_type == "ratings" and results and not DEV_MODE:
            results = get_detailed_results(results, website)
        
        # Cache the results
        cache_results(website, query, results)
        
        # Save to user history if requested
        if save_to_history and user_id:
            save_to_user_history(user_id, website, query, results)
            
        return results
    
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error calling Firecrawl API: {str(e)}")
        return []

def cache_results(website, query, results):
    """Cache the search results"""
    expires_at = datetime.utcnow() + CACHE_DURATION
    results_json = json.dumps(results)
    
    cache_entry = SearchCache(
        website=website,
        query=query,
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