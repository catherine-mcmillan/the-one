import requests
from flask import current_app
from app.models.search import SearchResult
from tqdm import tqdm  # For progress tracking

# DEVELOPMENT MODE SETTINGS - REMOVE IN PRODUCTION
DEV_MODE = True  # Set to False in production
MAX_RESULTS_DEV = 2  # Limit results during development (1 credit per page)
USE_SMALLER_MODEL = True  # Use smaller model for development

def search_website(website, query, ranking_type="relevance"):
    """
    Search for products/content on the specified website using Firecrawl API
    
    Args:
        website (str): Website to search (e.g., allrecipes.com)
        query (str): Search query
        ranking_type (str): 'relevance' or 'ratings'
        
    Returns:
        list: List of SearchResult objects
    """
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
        # DEVELOPMENT MODE OPTIMIZATIONS - REMOVE IN PRODUCTION
        "max_results": MAX_RESULTS_DEV if DEV_MODE else 10,  # 1 credit per page
        "format": "basic" if DEV_MODE else "json"  # Basic format uses fewer credits
    }
    
    try:
        response = requests.post(search_url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        # Process the search results
        results = []
        if 'results' in data:
            for item in tqdm(data['results'], desc="Processing search results"):
                result = SearchResult(
                    title=item.get('title', 'No Title'),
                    url=item.get('url', ''),
                    rating=item.get('rating'),
                    image_url=item.get('imageUrl')
                )
                results.append(result)
        
        # DEVELOPMENT MODE: Skip detailed results in dev to save credits
        if ranking_type == "ratings" and results and not DEV_MODE:
            results = get_detailed_results(results, website)
            
        return results
    
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error calling Firecrawl API: {str(e)}")
        return []

def get_detailed_results(basic_results, website):
    """
    Get detailed information for each result including comment summaries
    
    Args:
        basic_results (list): List of basic SearchResult objects
        website (str): Website domain
        
    Returns:
        list: Enhanced SearchResult objects with comments analysis
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
            # Extract prompt to identify the big difference
            extract_prompt = """
            Analyze this content and identify:
            1. Key features and benefits
            2. What makes this THE ONE (the big difference)
            3. User experiences and feedback
            4. Tips and recommendations
            """
            
            payload = {
                "url": result.url,
                "include_comments": True,
                "summarize_comments": True,
                "prompt": extract_prompt,  # Custom prompt for extraction
                # DEVELOPMENT MODE OPTIMIZATIONS - REMOVE IN PRODUCTION
                "format": "basic" if DEV_MODE else "json",  # Basic format uses fewer credits
                "max_comments": 3 if DEV_MODE else None,  # Limit comments in dev
                "token_limit": 1000 if DEV_MODE else None  # Limit tokens in dev
            }
            
            response = requests.post(extract_url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            if 'commentSummary' in data:
                summary = data['commentSummary'].get('summary', '')
                pros = data['commentSummary'].get('pros', [])
                cons = data['commentSummary'].get('cons', [])
                tips = data['commentSummary'].get('tips', [])
                big_difference = data.get('bigDifference', '')  # Extract the big difference
                
                result.summary = summary
                result.pros = pros
                result.cons = cons
                result.tips = tips
                result.big_difference = big_difference  # Store the big difference
                
                # Add key features if available
                if 'features' in data:
                    result.key_features = data['features']
            
            if 'rating' in data and data['rating']:
                result.rating = data['rating']
                
            enhanced_results.append(result)
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error getting details for {result.url}: {str(e)}")
            enhanced_results.append(result)
    
    # Sort by rating and big difference significance
    enhanced_results.sort(
        key=lambda x: (
            x.rating if x.rating else 0,
            len(x.big_difference) if hasattr(x, 'big_difference') else 0
        ),
        reverse=True
    )
    
    return enhanced_results

def get_best_results(results, ranking_type="relevance"):
    """
    Process and rank search results based on ranking type
    
    Args:
        results (list): List of SearchResult objects
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
        # Sort by both rating and big difference significance
        results.sort(
            key=lambda x: (
                x.rating if x.rating else 0,
                len(x.big_difference) if hasattr(x, 'big_difference') else 0
            ),
            reverse=True
        )
        return results[:max_results]