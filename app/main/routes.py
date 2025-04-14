from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for, session
from flask_login import login_required, current_user
from app.main import bp
from app.models import UserSearchHistory, SearchResult
from app.extensions import db, cache
from app.services.firecrawl_service import search_website, get_best_results, FirecrawlAPIManager
from tqdm import tqdm
from datetime import datetime
import json
import uuid
from threading import Thread

@bp.route('/', methods=['GET'])
def index():
    return render_template('main/index.html', title='The ONE - Find the Best of Everything')

@bp.route('/loading')
def loading():
    return render_template('main/loading.html')

@bp.route('/check_search_status')
def check_search_status():
    # Get the search ID from the session
    search_id = session.get('search_id')
    if not search_id:
        return jsonify({'complete': False})
    
    # Check if there was an error
    error = cache.get(f'search_error_{search_id}')
    if error:
        return jsonify({
            'complete': True,
            'redirect_url': url_for('main.api_error', message=error)
        })
    
    # Check if the search is complete
    result = cache.get(f'search_result_{search_id}')
    if result is not None:
        # Search is complete, return the redirect URL
        return jsonify({
            'complete': True,
            'redirect_url': url_for('main.results', search_id=search_id)
        })
    
    # Search is still in progress
    return jsonify({'complete': False})

@bp.route('/search', methods=['POST'])
def search():
    website = request.form.get('website')
    query = request.form.get('query')
    ranking_type = request.form.get('ranking_type', 'relevance')
    
    # Generate a unique search ID
    search_id = str(uuid.uuid4())
    session['search_id'] = search_id
    
    # Store search parameters
    search_data = {
        'website': website,
        'query': query,
        'ranking_type': ranking_type
    }
    try:
        cache.set(f'search_params_{search_id}', search_data)
    except Exception as e:
        current_app.logger.error(f"Failed to store search parameters in cache: {str(e)}")
        flash("Failed to initialize search. Please try again.", "error")
        return redirect(url_for('main.index'))
    
    # Start the search in a background thread
    def do_search():
        # Create an application context for the thread
        with current_app.app_context():
            try:
                current_app.logger.info(f"Starting search for query: {query} on website: {website}")
                current_app.logger.info(f"Search ID: {search_id}")
                
                # Log the start of the API call
                current_app.logger.info("Making API call to search_website...")
                results = search_website(website, query)
                
                # Log the completion and results summary
                result_count = len(results) if isinstance(results, list) else 0
                current_app.logger.info(f"Search completed with {result_count} results")
                
                # Store results in cache with detailed logging
                try:
                    cache.set(f'search_result_{search_id}', results)
                    current_app.logger.info("Successfully stored results in cache")
                except Exception as cache_error:
                    current_app.logger.error(f"Failed to store results in cache: {str(cache_error)}")
                    cache.set(f'search_error_{search_id}', "Failed to store search results")
                    return
                
                # Store in user history if authenticated
                if current_user.is_authenticated:
                    try:
                        search_history = UserSearchHistory(
                            user_id=current_user.id,
                            website=website,
                            search_query=query,
                            ranking_type=ranking_type,
                            created_at=datetime.utcnow()
                        )
                        db.session.add(search_history)
                        db.session.commit()
                        current_app.logger.info("Successfully stored search in user history")
                    except Exception as db_error:
                        current_app.logger.error(f"Failed to store search history: {str(db_error)}")
                        # Don't fail the whole search if history storage fails
            
            except Exception as e:
                error_msg = str(e)
                current_app.logger.error(f"Search error: {error_msg}")
                current_app.logger.exception("Full traceback:")
                try:
                    cache.set(f'search_error_{search_id}', error_msg)
                except Exception as cache_error:
                    current_app.logger.error(f"Failed to store error in cache: {str(cache_error)}")
    
    # Start the thread
    try:
        thread = Thread(target=do_search)
        thread.start()
        current_app.logger.info(f"Started background search thread for ID: {search_id}")
    except Exception as e:
        current_app.logger.error(f"Failed to start search thread: {str(e)}")
        flash("Failed to start search. Please try again.", "error")
        return redirect(url_for('main.index'))
    
    # Redirect to loading page
    return redirect(url_for('main.loading'))

@bp.route('/results/<search_id>')
def results(search_id):
    # Get search parameters and results from cache
    search_params = cache.get(f'search_params_{search_id}')
    search_results = cache.get(f'search_result_{search_id}')
    
    if not search_params or not search_results:
        flash('Search results not found or expired. Please try a new search.', 'warning')
        return redirect(url_for('main.index'))
    
    # Check for errors in the results
    if isinstance(search_results, dict) and 'error' in search_results:
        flash(f"An error occurred: {search_results['error']}", 'error')
        return redirect(url_for('main.index'))
    
    current_app.logger.info(f"Displaying results for search_id: {search_id}")
    current_app.logger.debug(f"Results data: {json.dumps(search_results, indent=2)}")
    
    return render_template(
        'main/results.html',
        title='Search Results',
        website=search_params['website'],
        query=search_params['query'],
        ranking_type=search_params.get('ranking_type', 'relevance'),
        results=search_results
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