import pytest
from unittest.mock import patch
from flask import url_for
from app.models import UserSearchHistory, SearchResult

def test_index_route(client):
    """Test the index route returns 200 OK."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Welcome to The One' in response.data

def test_search_route_unauthorized(client):
    """Test search route requires authentication."""
    response = client.post('/search', data={
        'website': 'allrecipes.com',
        'query': 'cookies',
        'ranking_type': 'relevance'
    })
    assert response.status_code == 302  # Redirect to login
    assert '/auth/login' in response.location

@patch('app.main.routes.search_website')
def test_search_route_missing_fields(mock_search, auth_client):
    """Test search route handles missing fields."""
    response = auth_client.post('/search', data={
        'website': 'allrecipes.com'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Please provide both a website and a search query' in response.data

@patch('app.main.routes.search_website')
def test_search_route_success(mock_search, auth_client):
    """Test search route success."""
    mock_search.return_value = [
        SearchResult(
            title="Best Chocolate Chip Cookies",
            url="https://example.com/recipe/1",
            rating=4.8,
            image_url="https://example.com/image1.jpg"
        )
    ]
    
    response = auth_client.post('/search', data={
        'website': 'allrecipes.com',
        'query': 'chocolate chip cookies',
        'ranking_type': 'relevance'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Best Chocolate Chip Cookies' in response.data

def test_search_history_route_unauthorized(client):
    """Test search history route requires authentication."""
    response = client.get('/search_history')
    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']

def test_search_history_route(auth_client, search_history):
    """Test search history route displays history."""
    response = auth_client.get('/search_history')
    assert response.status_code == 200
    assert b'chocolate chip cookies' in response.data
    assert b'brownies' in response.data 