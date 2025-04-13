from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from app.models.user import User
from app import db
from datetime import datetime, timedelta
from functools import wraps

bp = Blueprint('auth', __name__)
csrf = CSRFProtect()

def check_confirmed(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    return decorated_function

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([username, email, password, confirm_password]):
            flash('Please fill in all fields.', 'error')
            return redirect(url_for('auth.register'))
            
        # Validate username
        is_valid, message = User.validate_username(username)
        if not is_valid:
            flash(message, 'error')
            return redirect(url_for('auth.register'))
            
        # Validate email
        is_valid, message = User.validate_email(email)
        if not is_valid:
            flash(message, 'error')
            return redirect(url_for('auth.register'))
            
        # Validate password
        is_valid, message = User.validate_password(password)
        if not is_valid:
            flash(message, 'error')
            return redirect(url_for('auth.register'))
            
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('auth.register'))
            
        try:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('auth.register'))
        
    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        if not username or not password:
            flash('Please provide both username and password.', 'error')
            return redirect(url_for('auth.login'))
            
        user = User.query.filter_by(username=username).first()
        
        # Check for account lockout
        if user and user.is_locked_out:
            flash('Account is temporarily locked due to too many failed attempts. Please try again later.', 'error')
            return redirect(url_for('auth.login'))
            
        if user is None or not user.check_password(password):
            if user:
                user.record_failed_login()
            flash('Invalid username or password.', 'error')
            return redirect(url_for('auth.login'))
            
        # Set secure session settings
        session.permanent = True
        session.permanent_session_lifetime = timedelta(days=30 if remember else 1)
        
        login_user(user, remember=remember)
        user.update_last_login()
        
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.index')
            
        flash('Welcome back!', 'success')
        return redirect(next_page)
        
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/profile')
@login_required
@check_confirmed
def profile():
    return render_template('auth/profile.html')

@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@check_confirmed
def edit_profile():
    if request.method == 'POST':
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if email and email != current_user.email:
            # Validate new email
            is_valid, message = User.validate_email(email)
            if not is_valid:
                flash(message, 'error')
                return redirect(url_for('auth.edit_profile'))
                
            if User.query.filter_by(email=email).first():
                flash('Email already registered.', 'error')
            else:
                current_user.email = email
                db.session.commit()
                flash('Email updated successfully.', 'success')
                
        if current_password and new_password:
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'error')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'error')
            else:
                try:
                    current_user.set_password(new_password)
                    db.session.commit()
                    flash('Password updated successfully. Please log in with your new password.', 'success')
                    return redirect(url_for('auth.logout'))
                except ValueError as e:
                    flash(str(e), 'error')
                
        return redirect(url_for('auth.profile'))
        
    return render_template('auth/edit_profile.html') 