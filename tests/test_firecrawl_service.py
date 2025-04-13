import pytest
import json
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from tqdm import tqdm
from app import create_app
from app.models import SearchResult
from app.services.firecrawl_service import (
    search_website, FirecrawlAPIManager, 
    RateLimitExceeded, APIError, AuthenticationError
)
from tests.config import TestConfig


def load_mock_data(filename):
    """Load mock data from JSON file"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'mock_data', filename)
    with open(file_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def app():
    """Create test application"""
    app = create_app(TestConfig)
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def mock_search_response():
    """Load mock search response"""
    return load_mock_data('search_response.json')


@pytest.fixture
def mock_extract_response():
    """Load mock extract response"""
    return load_mock_data('extract_response.json')


class TestFirecrawlService:
    """Test suite for Firecrawl service"""
    
    @patch.object(FirecrawlAPIManager, 'search')
    def test_search_website_relevance(self, mock_search, app, mock_search_response):
        """Test search_website with relevance ranking"""
        # Setup mock
        mock_search.return_value = mock_search_response
        
        # Call the function with progress bar
        with tqdm(total=1, desc="Testing search") as pbar:
            results = search_website('example.com', 'chocolate chip cookies', 'relevance')
            pbar.update(1)
        
        # Assertions
        mock_search.assert_called_once_with('example.com', 'chocolate chip cookies')
        assert len(results) == 3
        assert results[0].title == "Best Chocolate Chip Cookies"
        assert results[0].rating == 4.8
        assert results[1].title == "Ultimate Chocolate Chip Cookies"
        assert results[2].title == "Easy Chocolate Chip Cookies"
    
    @patch.object(FirecrawlAPIManager, 'extract')
    @patch.object(FirecrawlAPIManager, 'search')
    def test_search_website_ratings(self, mock_search, mock_extract, app, mock_search_response, mock_extract_response):
        """Test search_website with ratings ranking"""
        # Setup mocks
        mock_search.return_value = mock_search_response
        mock_extract.return_value = mock_extract_response
        
        # Call the function with progress bar
        with tqdm(total=2, desc="Testing ratings search") as pbar:
            results = search_website('example.com', 'chocolate chip cookies', 'ratings')
            pbar.update(2)
        
        # Assertions
        mock_search.assert_called_once()
        assert mock_extract.call_count > 0
        assert len(results) > 0
        
        # Check first result details
        first_result = results[0]
        assert first_result.title == mock_extract_response['title']
        assert first_result.rating == mock_extract_response['rating']
        assert first_result.summary == mock_extract_response['commentSummary']['summary']
        assert len(first_result.pros) == len(mock_extract_response['commentSummary']['pros'])
        assert len(first_result.cons) == len(mock_extract_response['commentSummary']['cons'])
        assert len(first_result.tips) == len(mock_extract_response['commentSummary']['tips'])
    
    @patch.object(FirecrawlAPIManager, 'search')
    def test_search_website_rate_limit(self, mock_search, app):
        """Test rate limit handling"""
        # Setup mock to raise RateLimitExceeded
        mock_search.side_effect = RateLimitExceeded("API rate limit exceeded")
        
        # Call the function and expect exception
        with pytest.raises(RateLimitExceeded):
            with tqdm(total=1, desc="Testing rate limit") as pbar:
                search_website('example.com', 'chocolate chip cookies')
                pbar.update(1)
    
    @patch.object(FirecrawlAPIManager, 'search')
    def test_search_website_api_error(self, mock_search, app):
        """Test API error handling"""
        # Setup mock to raise APIError
        mock_search.side_effect = APIError("API request failed")
        
        # Call the function and expect exception
        with pytest.raises(APIError):
            with tqdm(total=1, desc="Testing API error") as pbar:
                search_website('example.com', 'chocolate chip cookies')
                pbar.update(1)
    
    @patch.object(FirecrawlAPIManager, 'search')
    def test_search_website_auth_error(self, mock_search, app):
        """Test authentication error handling"""
        # Setup mock to raise AuthenticationError
        mock_search.side_effect = AuthenticationError("Invalid API key")
        
        # Call the function and expect exception
        with pytest.raises(AuthenticationError):
            with tqdm(total=1, desc="Testing auth error") as pbar:
                search_website('example.com', 'chocolate chip cookies')
                pbar.update(1)
    
    def test_api_manager_rate_limit_tracking(self, app):
        """Test API manager rate limit tracking"""
        api_manager = FirecrawlAPIManager()
        
        # Test initial state
        assert api_manager.daily_requests == 0
        
        # Simulate requests
        for _ in tqdm(range(5), desc="Testing rate limit tracking"):
            api_manager._increment_request_count()
        
        assert api_manager.daily_requests == 5
        
        # Test reset
        api_manager.last_reset = datetime.now() - timedelta(days=1, minutes=1)
        api_manager._check_rate_limit()
        assert api_manager.daily_requests == 0
    
    @patch('requests.get')
    def test_api_manager_search_request(self, mock_get, app):
        """Test API manager search request formatting"""
        api_manager = FirecrawlAPIManager()
        mock_get.return_value.json.return_value = {"results": []}
        mock_get.return_value.status_code = 200
        
        # Make a search request
        with tqdm(total=1, desc="Testing search request") as pbar:
            api_manager.search("example.com", "test query")
            pbar.update(1)
        
        # Verify request
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert "example.com" in kwargs['params']['website']
        assert "test query" in kwargs['params']['query']
        assert api_manager.api_key in kwargs['headers']['Authorization'] 