import pytest
from app.auth.forms import LoginForm, RegistrationForm
from app.models import User

def test_login_form_validation(app):
    """Test login form validation."""
    with app.app_context():
        # Test valid form
        form = LoginForm(email='test@example.com', password='TestPass123!')
        assert form.validate()
        
        # Test invalid email format
        form = LoginForm(email='invalid-email', password='TestPass123!')
        assert not form.validate()
        
        # Test missing email
        form = LoginForm(password='TestPass123!')
        assert not form.validate()
        
        # Test missing password
        form = LoginForm(email='test@example.com')
        assert not form.validate()

def test_registration_form_validation(app):
    """Test registration form validation."""
    with app.app_context():
        # Test valid form
        form = RegistrationForm(
            username='newuser',
            email='newuser@example.com',
            password='TestPass123!',
            password2='TestPass123!'
        )
        assert form.validate()
        
        # Test existing username
        form = RegistrationForm(
            username='testuser',  # Existing username from fixtures
            email='newuser@example.com',
            password='TestPass123!',
            password2='TestPass123!'
        )
        assert not form.validate()
        assert 'Username already taken' in str(form.username.errors)
        
        # Test existing email
        form = RegistrationForm(
            username='newuser',
            email='test@example.com',  # Existing email from fixtures
            password='TestPass123!',
            password2='TestPass123!'
        )
        assert not form.validate()
        assert 'Email already registered' in str(form.email.errors)
        
        # Test password mismatch
        form = RegistrationForm(
            username='newuser',
            email='newuser@example.com',
            password='TestPass123!',
            password2='DifferentPass123!'
        )
        assert not form.validate()
        assert 'Passwords must match' in str(form.password2.errors)
        
        # Test invalid username format
        form = RegistrationForm(
            username='a',  # Too short
            email='newuser@example.com',
            password='TestPass123!',
            password2='TestPass123!'
        )
        assert not form.validate()
        
        # Test invalid email format
        form = RegistrationForm(
            username='newuser',
            email='invalid-email',
            password='TestPass123!',
            password2='TestPass123!'
        )
        assert not form.validate()
        
        # Test missing fields
        form = RegistrationForm()
        assert not form.validate()
        assert 'This field is required' in str(form.username.errors)
        assert 'This field is required' in str(form.email.errors)
        assert 'This field is required' in str(form.password.errors)
        assert 'This field is required' in str(form.password2.errors) 