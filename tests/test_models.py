import pytest
from app.models import User, UserSearchHistory
from datetime import datetime

def test_user_creation(app):
    """Test user creation and password hashing."""
    with app.app_context():
        user = User(username='testuser2', email='test2@example.com')
        user.set_password('TestPass123!')
        assert user.username == 'testuser2'
        assert user.email == 'test2@example.com'
        assert user.password_hash is not None
        assert user.check_password('TestPass123!')
        assert not user.check_password('WrongPass123!')

def test_user_validation(app):
    """Test user validation methods."""
    # Test username validation
    valid, _ = User.validate_username('validuser')
    assert valid
    valid, _ = User.validate_username('a')  # Too short
    assert not valid
    valid, _ = User.validate_username('invalid@user')  # Invalid character
    assert not valid

    # Test email validation
    valid, _ = User.validate_email('valid@example.com')
    assert valid
    valid, _ = User.validate_email('invalid-email')
    assert not valid

    # Test password validation
    valid, _ = User.validate_password('TestPass123!')
    assert valid
    valid, _ = User.validate_password('weak')  # Too short
    assert not valid
    valid, _ = User.validate_password('nouppercasepass123!')  # No uppercase
    assert not valid
    valid, _ = User.validate_password('NOLOWERCASEPASS123!')  # No lowercase
    assert not valid
    valid, _ = User.validate_password('NoSpecialChars123')  # No special chars
    assert not valid
    valid, _ = User.validate_password('NoNumbers!')  # No numbers
    assert not valid

def test_user_search_history(app):
    """Test user search history relationship."""
    with app.app_context():
        user = User(username='testuser2', email='test2@example.com')
        user.set_password('TestPass123!')
        
        # Create some search history entries
        history1 = UserSearchHistory(
            user_id=user.id,
            website='allrecipes.com',
            search_query='chocolate cake',
            ranking_type='relevance',
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        history2 = UserSearchHistory(
            user_id=user.id,
            website='allrecipes.com',
            search_query='vanilla cupcakes',
            ranking_type='rating',
            created_at=datetime(2024, 1, 2, 12, 0, 0)
        )
        
        # Add to database
        user.search_history.append(history1)
        user.search_history.append(history2)
        
        assert user.total_searches == 2
        recent_searches = user.recent_searches
        assert len(recent_searches) == 2
        assert recent_searches[0].search_query == 'vanilla cupcakes'  # Most recent first
        assert recent_searches[1].search_query == 'chocolate cake'

def test_user_lockout(app):
    """Test user lockout functionality."""
    with app.app_context():
        user = User(username='testuser2', email='test2@example.com')
        user.set_password('TestPass123!')
        
        # Record failed login attempts
        for _ in range(5):
            user.record_failed_login()
        
        assert user.is_locked_out
        
        # Reset failed logins
        user.reset_failed_logins()
        assert not user.is_locked_out
        assert user.failed_login_attempts == 0
        assert user.last_failed_login is None

def test_search_history_model(app):
    """Test UserSearchHistory model."""
    with app.app_context():
        user = User(username='testuser2', email='test2@example.com')
        user.set_password('TestPass123!')
        
        history = UserSearchHistory(
            user_id=user.id,
            website='allrecipes.com',
            search_query='chocolate cake',
            ranking_type='relevance',
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        
        assert history.website == 'allrecipes.com'
        assert history.search_query == 'chocolate cake'
        assert history.ranking_type == 'relevance'
        assert history.created_at == datetime(2024, 1, 1, 12, 0, 0)
        assert str(history) == '<UserSearchHistory allrecipes.com:chocolate cake>' 