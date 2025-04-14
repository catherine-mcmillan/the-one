import os
import json
import logging
import time
from firecrawl import FirecrawlApp
from dotenv import load_dotenv
from tqdm import tqdm
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('firecrawl_test')

# Load environment variables
load_dotenv()

class RecipeResult(BaseModel):
    """Model for recipe search results"""
    title: str
    rating: Optional[float] = None
    description: str

class SearchResponse(BaseModel):
    """Model for the search response"""
    success: bool
    data: Dict[str, List[RecipeResult]]
    status: str
    expiresAt: str

def test_simple_search():
    """Test a simple search with the Firecrawl SDK"""
    api_key = os.getenv('FIRECRAWL_API_KEY')
    if not api_key:
        raise ValueError("FIRECRAWL_API_KEY not found in environment variables")

    # Initialize the SDK
    logger.info("Initializing Firecrawl SDK")
    app = FirecrawlApp(api_key=api_key)

    # Simple test parameters
    website = "allrecipes.com"
    query = "chocolate chip cookies"
    
    try:
        logger.info(f"Starting test search for '{query}' on {website}")
        
        # Perform the search with verbose logging
        response = app.extract(
            [f"https://{website}/*"],
            {
                'prompt': f'Find the top 3 chocolate chip cookie recipes on {website}. For each recipe, provide:\n'
                         f'1. Recipe title\n'
                         f'2. Brief description\n'
                         f'3. Rating if available',
                'enable_web_search': True,
                'max_results': 3,
                'include_comments': False,
                'summarize_comments': False,
                'timeout': 300,  # 5 minutes
                'retry_on_error': True,
                'max_retries': 3
            }
        )
        
        # Log the raw response
        logger.info("Raw API Response:")
        logger.info(json.dumps(response, indent=2))
        
        # Parse and validate response
        search_response = SearchResponse(**response)
        
        # Process and log the results
        if search_response.success and search_response.data:
            logger.info("Processing results:")
            for category, items in search_response.data.items():
                logger.info(f"Found {len(items)} items in {category}")
                for item in items:
                    logger.info(f"Recipe: {item.title}")
                    logger.info(f"Rating: {item.rating}")
                    logger.info(f"Description: {item.description}")
                    logger.info("---")
        
        return search_response
        
    except Exception as e:
        logger.error(f"Error during test search: {str(e)}")
        raise

def test_complex_search():
    """Test a more complex search with detailed summaries"""
    api_key = os.getenv('FIRECRAWL_API_KEY')
    if not api_key:
        raise ValueError("FIRECRAWL_API_KEY not found in environment variables")

    # Initialize the SDK
    logger.info("Initializing Firecrawl SDK for complex search")
    app = FirecrawlApp(api_key=api_key)

    # Complex test parameters
    website = "allrecipes.com"
    query = "chocolate chip cookies"
    
    try:
        logger.info(f"Starting complex search for '{query}' on {website}")
        
        # Perform the search with verbose logging
        response = app.extract(
            [f"https://{website}/*"],
            {
                'prompt': f'Search for the top 3 chocolate chip cookie recipes on {website}. For each recipe, provide:\n'
                         f'1. A clear title\n'
                         f'2. A detailed summary\n'
                         f'3. What makes this recipe unique (big difference)\n'
                         f'4. Key takeaways\n'
                         f'5. Pros and cons\n'
                         f'6. Tips and tricks\n'
                         f'7. Rating if available\n'
                         f'8. URL and image URL if available',
                'enable_web_search': True,
                'max_results': 3,
                'include_comments': True,
                'summarize_comments': True,
                'timeout': 600,  # 10 minutes
                'retry_on_error': True,
                'max_retries': 3
            }
        )
        
        # Log the raw response
        logger.info("Raw API Response (Complex Search):")
        logger.info(json.dumps(response, indent=2))
        
        # Save the result to a file for inspection
        with open('complex_test_result.json', 'w') as f:
            json.dump(response, f, indent=2)
        logger.info("Complex search results saved to complex_test_result.json")
        
        return response
        
    except Exception as e:
        logger.error(f"Error during complex search: {str(e)}")
        raise

def main():
    """Main function to run the tests"""
    try:
        logger.info("Starting Firecrawl SDK tests")
        
        # Run simple test
        logger.info("Running simple search test...")
        start_time = time.time()
        simple_result = test_simple_search()
        end_time = time.time()
        logger.info(f"Simple test completed in {end_time - start_time:.2f} seconds")
        
        # Run complex test
        logger.info("\nRunning complex search test...")
        start_time = time.time()
        complex_result = test_complex_search()
        end_time = time.time()
        logger.info(f"Complex test completed in {end_time - start_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    main() 