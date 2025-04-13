import pytest
from flask import Flask
from app.extensions import db, cache, migrate
from app.auth.login import login_manager
from app.models import User
from flask_login import current_user

def test_extensions_initialization(app):
    """Test that all extensions are properly initialized."""
    assert 'sqlalchemy' in app.extensions
    assert 'cache' in app.extensions
    assert 'migrate' in app.extensions
    assert 'login_manager' in app.extensions

def test_db_initialization(app):
    """Test that the database is properly initialized."""
    assert db.app == app
    assert db.engine.url.database.endswith('test.db')

def test_cache_initialization(app):
    """Test that the cache is properly initialized."""
    assert cache.app == app
    assert cache.config['CACHE_TYPE'] == 'simple'

def test_migrate_initialization(app):
    """Test that migrations are properly initialized."""
    assert migrate.app == app
    assert migrate.db == db

def test_login_manager_initialization(app):
    """Test that the login manager is properly initialized."""
    assert login_manager.app == app
    assert login_manager.login_view == 'auth.login'
    assert login_manager.login_message == 'Please log in to access this page.'
    assert login_manager.login_message_category == 'info'

def test_db_extension(app):
    """Test SQLAlchemy extension."""
    with app.app_context():
        # Test database initialization
        assert db.engine.url.database == ':memory:'
        
        # Test model creation
        user = User(username='testuser3', email='test3@example.com')
        user.set_password('TestPass123!')
        db.session.add(user)
        db.session.commit()
        
        # Test model query
        user = User.query.filter_by(email='test3@example.com').first()
        assert user is not None
        assert user.username == 'testuser3'

def test_login_manager_extension(app, client):
    """Test LoginManager extension."""
    # Test login view configuration
    assert login_manager.login_view == 'auth.login'
    assert login_manager.login_message == 'Please log in to access this page.'
    assert login_manager.login_message_category == 'info'
    
    # Test user loader
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        
        # Test user loader function
        loaded_user = login_manager.user_loader(user.id)
        assert loaded_user is not None
        assert loaded_user.id == user.id
        
        # Test unauthorized access
        response = client.get('/search_history')
        assert response.status_code == 302
        assert '/auth/login' in response.location
        
        # Test login required decorator
        response = client.get('/profile')
        assert response.status_code == 302
        assert '/auth/login' in response.location

def test_cache_extension(app):
    """Test Cache extension."""
    with app.app_context():
        # Test cache initialization
        assert cache.config['CACHE_TYPE'] == 'simple'
        
        # Test cache operations
        cache.set('test_key', 'test_value')
        assert cache.get('test_key') == 'test_value'
        
        # Test cache timeout
        cache.set('timeout_key', 'timeout_value', timeout=1)
        assert cache.get('timeout_key') == 'timeout_value'
        
        # Test cache deletion
        cache.delete('test_key')
        assert cache.get('test_key') is None

def test_migrate_extension(app):
    """Test Migrate extension."""
    with app.app_context():
        # Test migrate initialization
        assert migrate.db == db
        assert migrate.directory == 'migrations' 