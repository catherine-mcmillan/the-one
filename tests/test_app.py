import pytest
from app import create_app
from app.models.search import SearchResult
from tests.config import TestConfig
from unittest.mock import patch, MagicMock
from app.models import User, db

@pytest.fixture
def app():
    app = create_app(TestConfig)
    app.config['TESTING'] = True
    
    # This creates a test client
    with app.test_client() as client:
        # Establish an application context
        with app.app_context():
            # Initialize database
            db.create_all()
            
            # Create test user
            user = User(username='testuser', email='test@example.com')
            user.set_password('TestPass123!')
            db.session.add(user)
            db.session.commit()
            
            yield client
            
            # Clean up
            db.session.remove()
            db.drop_all()

@pytest.fixture
def auth_client(app):
    """Create an authenticated test client"""
    with app.session_transaction() as sess:
        sess['_user_id'] = 1  # Assuming the test user has ID 1
    return app

def test_index_page(app):
    """Test that the index page loads correctly"""
    response = app.get('/')
    assert response.status_code == 200
    assert b'The ONE' in response.data
    assert b'Find the best of everything' in response.data

def test_search_form_validation(auth_client):
    """Test search form validation"""
    # Test with missing website
    response = auth_client.post('/search', data={
        'query': 'chocolate chip cookies',
        'ranking_type': 'relevance'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Please provide both a website and a search query' in response.data
    
    # Test with missing query
    response = auth_client.post('/search', data={
        'website': 'allrecipes.com',
        'ranking_type': 'relevance'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Please provide both a website and a search query' in response.data

@patch('app.services.firecrawl_service.search_website')
def test_search_results(mock_search, auth_client):
    """Test search results are displayed correctly"""
    # Mock the search_website function with Firecrawl API response structure
    mock_results = [
        {
            "url": "https://allrecipes.com/recipe/10813/best-chocolate-chip-cookies/",
            "title": "Best Chocolate Chip Cookies",
            "content": "These cookies are the best! They're crispy on the outside and chewy on the inside...",
            "rating": 4.8,
            "commentSummary": {
                "summary": "Users love these cookies for their perfect texture and rich flavor. Many recommend using high-quality chocolate chips.",
                "pros": ["Quick and easy to make", "Perfect texture - crispy outside, chewy inside", "Rich chocolate flavor"],
                "cons": ["Some found them too sweet", "Require careful timing to avoid overbaking"],
                "tips": ["Add 1/4 teaspoon of espresso powder to enhance chocolate flavor", "Chill the dough for at least 1 hour before baking"]
            }
        },
        {
            "url": "https://allrecipes.com/recipe/25037/award-winning-soft-chocolate-chip-cookies/",
            "title": "Award-Winning Soft Chocolate Chip Cookies",
            "content": "These soft and chewy cookies have won multiple awards...",
            "rating": 4.5,
            "commentSummary": {
                "summary": "These cookies are known for their soft texture and balanced sweetness.",
                "pros": ["Very soft texture", "Not too sweet", "Great for kids"],
                "cons": ["Can be too soft for some", "Requires specific ingredients"],
                "tips": ["Use room temperature butter", "Don't overmix the dough"]
            }
        }
    ]
    mock_search.return_value = mock_results
    
    response = auth_client.post('/search', data={
        'website': 'allrecipes.com',
        'query': 'chocolate chip cookies',
        'ranking_type': 'relevance'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Search Results' in response.data
    assert b'Showing results for "chocolate chip cookies"' in response.data
    assert b'Best Chocolate Chip Cookies' in response.data
    assert b'Award-Winning Soft Chocolate Chip Cookies' in response.data
    assert b'4.8 / 5' in response.data
    assert b'4.5 / 5' in response.data
    assert b'Users love these cookies for their perfect texture' in response.data
    assert b'Quick and easy to make' in response.data
    assert b'Some found them too sweet' in response.data
    assert b'Add 1/4 teaspoon of espresso powder' in response.data

@patch('app.services.firecrawl_service.search_website')
def test_no_results(mock_search, auth_client):
    """Test when search returns no results"""
    # Mock the search_website function to return empty list
    mock_search.return_value = []
    
    response = auth_client.post('/search', data={
        'website': 'nonexistent.com',
        'query': 'nonexistent item',
        'ranking_type': 'relevance'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'No results found for your search' in response.data
    assert b'Try adjusting your search terms' in response.data

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