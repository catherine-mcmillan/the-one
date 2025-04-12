import pytest
from app import create_app
from app.models.search import SearchResult
from tests.config import TestConfig
from unittest.mock import patch, MagicMock

@pytest.fixture
def app():
    app = create_app(TestConfig)
    app.config['TESTING'] = True
    
    # This creates a test client
    with app.test_client() as client:
        # Establish an application context
        with app.app_context():
            yield client

def test_index_page(app):
    """Test that the index page loads correctly"""
    response = app.get('/')
    assert response.status_code == 200
    assert b'The ONE' in response.data
    assert b'Find the best of everything' in response.data

def test_search_form_validation(app):
    """Test search form validation"""
    # Test with missing website
    response = app.post('/search', data={
        'query': 'chocolate chip cookies',
        'ranking_type': 'relevance'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Please provide both a website and a search query' in response.data
    
    # Test with missing query
    response = app.post('/search', data={
        'website': 'allrecipes.com',
        'ranking_type': 'relevance'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Please provide both a website and a search query' in response.data

@patch('app.services.firecrawl_service.search_website')
def test_search_results(mock_search, app):
    """Test search results are displayed correctly"""
    # Mock the search_website function
    mock_results = [
        SearchResult(
            title="Best Chocolate Chip Cookies",
            url="https://example.com/recipe/1",
            rating=4.8,
            image_url="https://example.com/image1.jpg",
            summary="These cookies are amazing!",
            pros=["Easy to make", "Delicious"],
            cons=["Takes time"],
            tips=["Use high-quality chocolate"]
        ),
        SearchResult(
            title="Ultimate Chocolate Chip Cookies",
            url="https://example.com/recipe/2",
            rating=4.5,
            image_url="https://example.com/image2.jpg"
        )
    ]
    mock_search.return_value = mock_results
    
    # Test a successful search
    with app.session_transaction() as sess:
        sess['_csrf_token'] = 'dummy_token'
    
    response = app.post('/search', data={
        'website': 'allrecipes.com',
        'query': 'chocolate chip cookies',
        'ranking_type': 'relevance'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Results for "chocolate chip cookies"' in response.data
    assert b'Best Chocolate Chip Cookies' in response.data
    assert b'Ultimate Chocolate Chip Cookies' in response.data

@patch('app.services.firecrawl_service.search_website')
def test_no_results(mock_search, app):
    """Test when search returns no results"""
    # Mock the search_website function to return empty list
    mock_search.return_value = []
    
    # Test a search with no results
    with app.session_transaction() as sess:
        sess['_csrf_token'] = 'dummy_token'
    
    response = app.post('/search', data={
        'website': 'nonexistent.com',
        'query': 'nonexistent item',
        'ranking_type': 'relevance'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'No results found' in response.data

def test_search_result_model():
    """Test the SearchResult model"""
    result = SearchResult(
        title="Test Title",
        url="https://example.com",
        rating=4.5,
        image_url="https://example.com/image.jpg",
        summary="This is a summary",
        pros=["Pro 1", "Pro 2"],
        cons=["Con 1"],
        tips=["Tip 1", "Tip 2", "Tip 3"]
    )
    
    assert result.title == "Test Title"
    assert result.url == "https://example.com"
    assert result.rating == 4.5
    assert result.summary == "This is a summary"
    assert len(result.pros) == 2
    assert len(result.cons) == 1
    assert len(result.tips) == 3
    
    # Test to_dict method
    result_dict = result.to_dict()
    assert result_dict['title'] == "Test Title"
    assert result_dict['rating'] == 4.5
    assert len(result_dict['pros']) == 2