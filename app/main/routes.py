from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for, session
from flask_login import login_required, current_user
from app.main import bp
from app.models import UserSearchHistory, SearchResult
from app.extensions import db
from app.services.firecrawl_service import search_website, get_best_results, FirecrawlAPIManager, FirecrawlService
from tqdm import tqdm
from datetime import datetime
import json
import uuid
import time
import threading

# Store search results in memory (you might want to use Redis or a database in production)
search_results = {}
search_status = {}

@bp.route('/', methods=['GET'])
def index():
    return render_template('main/index.html', title='The ONE - Find the Best of Everything')

@bp.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        website = request.form.get('website')
        query = request.form.get('query')
        search_type = request.form.get('search_type', 'simple')
        
        if not website or not query:
            return redirect(url_for('main.index'))
        
        # Generate a unique search ID
        search_id = f"{website}_{query}_{int(time.time())}"
        
        # Initialize search status
        search_status[search_id] = {
            'complete': False,
            'start_time': time.time(),
            'website': website,
            'query': query,
            'search_type': search_type
        }
        
        # Start search in background
        thread = threading.Thread(target=perform_search, args=(search_id,))
        thread.start()
        
        # Redirect to loading page
        return redirect(url_for('main.loading', search_id=search_id))
    
    return render_template('index.html')

@bp.route('/loading/<search_id>')
def loading(search_id):
    if search_id not in search_status:
        return redirect(url_for('main.index'))
    return render_template('loading.html')

@bp.route('/check_search_status')
def check_search_status():
    search_id = request.args.get('search_id')
    if not search_id or search_id not in search_status:
        return jsonify({'complete': False})
    
    status = search_status[search_id]
    if status['complete']:
        # Clean up the status
        del search_status[search_id]
        return jsonify({
            'complete': True,
            'redirect_url': url_for('main.results', search_id=search_id)
        })
    
    return jsonify({'complete': False})

@bp.route('/results/<search_id>')
def results(search_id):
    if search_id not in search_results:
        return redirect(url_for('main.index'))
    
    results = search_results[search_id]
    # Clean up the results
    del search_results[search_id]
    
    return render_template('results.html', results=results)

def perform_search(search_id):
    """Perform the search in a background thread"""
    try:
        status = search_status[search_id]
        firecrawl = FirecrawlService()
        
        if status['search_type'] == 'simple':
            results = firecrawl.search(status['website'], status['query'])
        else:
            results = firecrawl.extract(status['website'], status['query'])
        
        # Store results
        search_results[search_id] = results
        # Mark as complete
        search_status[search_id]['complete'] = True
        
    except Exception as e:
        # Handle error
        search_status[search_id]['error'] = str(e)
        search_status[search_id]['complete'] = True

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