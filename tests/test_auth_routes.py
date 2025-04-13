import pytest
from app.models import User

def test_login_route_get(client):
    """Test login page loads correctly."""
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert b'Login' in response.data

def test_login_route_post_success(client, app):
    """Test successful login."""
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        
    response = client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'TestPass123!'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Welcome back' in response.data

def test_login_route_post_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'WrongPass123!'
    })
    
    assert response.status_code == 200
    assert b'Invalid email or password' in response.data

def test_register_route_get(client):
    """Test register page loads correctly."""
    response = client.get('/auth/register')
    assert response.status_code == 200
    assert b'Register' in response.data

def test_register_route_post_success(client, app):
    """Test successful registration."""
    response = client.post('/auth/register', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'TestPass123!',
        'password2': 'TestPass123!'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Registration successful' in response.data
    
    with app.app_context():
        user = User.query.filter_by(email='newuser@example.com').first()
        assert user is not None
        assert user.username == 'newuser'

def test_register_route_post_existing_email(client):
    """Test registration with existing email."""
    response = client.post('/auth/register', data={
        'username': 'testuser2',
        'email': 'test@example.com',
        'password': 'TestPass123!',
        'password2': 'TestPass123!'
    })
    
    assert response.status_code == 200
    assert b'Email already registered' in response.data

def test_register_route_post_password_mismatch(client):
    """Test registration with mismatched passwords."""
    response = client.post('/auth/register', data={
        'username': 'testuser2',
        'email': 'test2@example.com',
        'password': 'TestPass123!',
        'password2': 'DifferentPass123!'
    })
    
    assert response.status_code == 200
    assert b'Passwords must match' in response.data

def test_logout_route(auth_client):
    """Test logout functionality."""
    response = auth_client.get('/auth/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'You have been logged out' in response.data 