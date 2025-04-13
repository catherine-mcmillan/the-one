import pytest
from flask import Flask
from app import create_app
from app.extensions import db
from app.auth.login import login_manager
from app.models.user import User, UserSearchHistory
from tests.config import TestConfig
import json
import os
from datetime import datetime, timedelta
from flask_login import login_user

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app('testing')
    
    # Create the database and tables
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def test_user(app):
    """Create a test user."""
    with app.app_context():
        user = User(
            email='test@example.com',
            password='testpassword',
            first_name='Test',
            last_name='User',
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        return user

@pytest.fixture
def auth_client(client, test_user):
    """Create an authenticated test client."""
    with client:
        with client.session_transaction() as session:
            login_user(test_user)
        yield client

@pytest.fixture
def mock_search_response():
    """Load mock search response data."""
    with open('tests/mock_data/search_response.json') as f:
        return json.load(f)

@pytest.fixture
def search_history(app):
    """Create test search history entries."""
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        history = [
            UserSearchHistory(
                user_id=user.id,
                website='allrecipes.com',
                search_query='chocolate chip cookies',
                ranking_type='relevance',
                created_at=datetime(2024, 1, 1, 12, 0, 0)
            ),
            UserSearchHistory(
                user_id=user.id,
                website='allrecipes.com',
                search_query='brownies',
                ranking_type='rating',
                created_at=datetime(2024, 1, 2, 12, 0, 0)
            )
        ]
        db.session.add_all(history)
        db.session.commit()
        return history 