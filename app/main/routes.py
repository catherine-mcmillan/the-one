from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.main import bp
from app.models import UserSearchHistory, SearchResult
from app.extensions import db
from app.services.firecrawl_service import search_website, get_best_results
from tqdm import tqdm
from datetime import datetime
import json

@bp.route('/')
@bp.route('/index')
def index():
    return render_template('main/index.html')

@bp.route('/search', methods=['POST'])
@login_required
def search():
    website = request.form.get('website')
    query = request.form.get('query')
    ranking_type = request.form.get('ranking_type', 'relevance')
    
    if not website or not query:
        flash('Please provide both website and search query', 'error')
        return redirect(url_for('main.index'))
    
    # Clean website input (remove https://, www., etc.)
    website = website.lower()
    if website.startswith('http://'):
        website = website[7:]
    if website.startswith('https://'):
        website = website[8:]
    if website.startswith('www.'):
        website = website[4:]
    
    try:
        # Store the search in history
        search_history = UserSearchHistory(
            user_id=current_user.id,
            website=website,
            search_query=query,
            ranking_type=ranking_type,
            created_at=datetime.utcnow()
        )
        db.session.add(search_history)
        db.session.commit()
        
        # Perform the search using Firecrawl API with development mode optimizations
        with tqdm(total=1, desc="Processing search") as pbar:
            results = search_website(
                website=website,
                query=query,
                ranking_type=ranking_type,
                save_to_history=True,
                user_id=current_user.id
            )
            pbar.update(1)
        
        # Store results in the database
        for result in results:
            search_result = SearchResult(
                search_id=search_history.id,
                title=result.get('title', ''),
                url=result.get('url', ''),
                description=result.get('summary', ''),
                rating=result.get('rating')
            )
            db.session.add(search_result)
        
        db.session.commit()
        
        flash('Search completed successfully!', 'success')
        return redirect(url_for('main.results', search_id=search_history.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred during the search: {str(e)}', 'error')
        return redirect(url_for('main.index'))

@bp.route('/results/<int:search_id>')
@login_required
def results(search_id):
    search_history = UserSearchHistory.query.get_or_404(search_id)
    
    # Verify the search belongs to the current user
    if search_history.user_id != current_user.id:
        flash('You do not have permission to view these results.', 'error')
        return redirect(url_for('main.index'))
    
    # Get the search results
    results = SearchResult.query.filter_by(search_id=search_id).all()
    
    return render_template('main/results.html',
                         title='Search Results',
                         search_history=search_history,
                         results=results)

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