from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for, session
from flask_login import login_required, current_user
from app.main import bp
from app.models import UserSearchHistory, SearchResult
from app.extensions import db
from app.services.firecrawl_service import search_website, get_best_results, FirecrawlAPIManager
from tqdm import tqdm
from datetime import datetime
import json
import uuid

@bp.route('/', methods=['GET'])
def index():
    return render_template('main/index.html', title='The ONE - Find the Best of Everything')

@bp.route('/search', methods=['POST'])
@login_required
def search():
    website = request.form.get('website')
    query = request.form.get('query')
    ranking_type = request.form.get('ranking_type', 'relevance')
    
    if not website or not query:
        flash('Please provide both a website and a search query', 'error')
        return redirect(url_for('main.index'))
    
    # Store search history
    search_history = UserSearchHistory(
        user_id=current_user.id,
        website=website,
        search_query=query,
        ranking_type=ranking_type,
        created_at=datetime.utcnow()
    )
    db.session.add(search_history)
    db.session.commit()
    
    # Perform the search
    results = search_website(website, query, ranking_type)
    
    return render_template('main/results.html', 
                         results=results,
                         website=website,
                         query=query,
                         ranking_type=ranking_type)

@bp.route('/results/<search_id>')
@login_required
def results(search_id):
    search_data = session.get(f'search_{search_id}')
    
    if not search_data:
        flash('Search results not found or expired. Please try a new search.', 'warning')
        return redirect(url_for('main.index'))
    
    return render_template(
        'main/results.html',
        title='Search Results',
        website=search_data['website'],
        query=search_data['query'],
        ranking_type=search_data['ranking_type'],
        results=search_data['results']
    )

@bp.route('/search_history')
@login_required
def search_history():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get user's search history with pagination
    search_history = UserSearchHistory.query.filter_by(user_id=current_user.id)\
        .order_by(UserSearchHistory.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('main/search_history.html', 
                         search_history=search_history,
                         title='Search History')

@bp.route('/api-usage', methods=['GET'])
@login_required
def api_usage():
    """Display API usage statistics"""
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('main.index'))
    
    # Get the API manager and usage stats
    api_manager = FirecrawlAPIManager(current_app.config.get('FIRECRAWL_API_KEY'))
    
    # Get usage history from database
    usage_history = UserSearchHistory.query.order_by(UserSearchHistory.created_at.desc()).limit(30).all()
    
    # Format for chart display
    dates = [entry.created_at.strftime('%Y-%m-%d') for entry in usage_history]
    counts = [entry.count() for entry in usage_history]
    
    return render_template(
        'admin/api_usage.html',
        title='API Usage Dashboard',
        daily_requests=api_manager.daily_requests,
        daily_limit=api_manager.daily_limit,
        percentage_used=(api_manager.daily_requests / api_manager.daily_limit) * 100,
        reset_time=api_manager.daily_reset_time.strftime('%Y-%m-%d %H:%M:%S'),
        history_dates=dates,
        history_counts=counts
    )

@bp.route('/api-error/rate-limit')
def api_rate_limit_error():
    """Display the API rate limit error page"""
    api_manager = FirecrawlAPIManager(current_app.config.get('FIRECRAWL_API_KEY'))
    return render_template(
        'errors/api_limit.html',
        title='API Limit Reached',
        reset_time=api_manager.daily_reset_time.strftime('%Y-%m-%d %H:%M:%S')
    )

@bp.route('/api-error')
def api_error():
    """Display a generic API error page"""
    error_message = request.args.get('message', 'Unknown API error')
    return render_template(
        'errors/api_error.html',
        title='API Error',
        error_message=error_message
    )

def clean_website_input(website):
    """Clean website input by removing protocol and www"""
    website = website.lower()
    if website.startswith('http://'):
        website = website[7:]
    if website.startswith('https://'):
        website = website[8:]
    if website.startswith('www.'):
        website = website[4:]
    return website 