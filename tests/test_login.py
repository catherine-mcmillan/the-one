import pytest
from flask_login import current_user
from app.models import User
from datetime import datetime, timedelta
from app.extensions import db

def test_user_loader(app):
    """Test user loader function."""
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        
        # Test valid user ID
        loaded_user = app.login_manager.user_loader(user.id)
        assert loaded_user is not None
        assert loaded_user.id == user.id
        
        # Test invalid user ID
        loaded_user = app.login_manager.user_loader(999)  # Non-existent ID
        assert loaded_user is None

def test_login_required_views(client):
    """Test login required views."""
    # Test protected views
    protected_views = [
        '/search_history',
        '/profile',
        '/api-usage'
    ]
    
    for view in protected_views:
        response = client.get(view)
        assert response.status_code == 302
        assert '/auth/login' in response.location

def test_login_lockout(app, client):
    """Test login lockout functionality."""
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        
        # Test failed login attempts
        for _ in range(5):
            response = client.post('/auth/login', data={
                'email': 'test@example.com',
                'password': 'WrongPass123!'
            })
            assert response.status_code == 200
            assert b'Invalid email or password' in response.data
        
        # Test lockout
        user = User.query.filter_by(email='test@example.com').first()
        assert user.failed_login_attempts == 5
        assert user.is_locked_out
        
        # Test login during lockout
        response = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'TestPass123!'
        })
        assert response.status_code == 200
        assert b'Invalid email or password' in response.data
        
        # Test lockout reset
        user.last_failed_login = datetime.utcnow() - timedelta(minutes=6)
        db.session.commit()
        
        response = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Welcome back' in response.data
        
        # Verify lockout reset
        user = User.query.filter_by(email='test@example.com').first()
        assert user.failed_login_attempts == 0
        assert user.last_failed_login is None

def test_remember_me(app, client):
    """Test remember me functionality."""
    with app.app_context():
        # Test login without remember me
        response = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'remember_me': False
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Welcome back' in response.data
        assert 'session' in client.cookie_jar._cookies['localhost.local']['/']
        assert 'remember_token' not in client.cookie_jar._cookies['localhost.local']['/']
        
        # Test login with remember me
        client.delete_cookie('localhost.local', 'session')
        response = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'remember_me': True
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Welcome back' in response.data
        assert 'remember_token' in client.cookie_jar._cookies['localhost.local']['/']

def test_login_page(client):
    """Test that the login page loads correctly."""
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert b'Login' in response.data

def test_login_success(client, test_user):
    """Test successful login."""
    response = client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'testpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Welcome' in response.data

def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post('/auth/login', data={
        'email': 'wrong@example.com',
        'password': 'wrongpassword'
    })
    assert response.status_code == 200
    assert b'Invalid email or password' in response.data

def test_logout(auth_client):
    """Test logout functionality."""
    response = auth_client.get('/auth/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data

def test_authenticated_user_redirect(auth_client):
    """Test that authenticated users are redirected from login page."""
    response = auth_client.get('/auth/login', follow_redirects=True)
    assert response.status_code == 200
    assert b'Welcome' in response.data 