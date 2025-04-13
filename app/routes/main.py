from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from app.services.firecrawl_service import search_website
from app.models.search import UserSearchHistory
from app import db

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        website = request.form.get('website')
        query = request.form.get('query')
        save_to_history = request.form.get('save_to_history', False)
        
        if not website or not query:
            flash('Please provide both a website and search query.', 'error')
            return redirect(url_for('main.index'))
            
        results = search_website(
            website=website,
            query=query,
            save_to_history=save_to_history,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        
        return render_template(
            'search_results.html',
            results=results,
            query=query,
            website=website
        )
        
    return redirect(url_for('main.index'))

@bp.route('/history')
@login_required
def search_history():
    searches = UserSearchHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(UserSearchHistory.created_at.desc()).all()
    
    return render_template('search_history.html', searches=searches)

@bp.route('/save-to-history', methods=['POST'])
@login_required
def save_to_history():
    website = request.form.get('website')
    query = request.form.get('query')
    notes = request.form.get('notes')
    
    if not website or not query:
        flash('Invalid request.', 'error')
        return redirect(url_for('main.index'))
    
    # Perform the search again to get fresh results
    results = search_website(website, query)
    
    # Save to history
    history_entry = UserSearchHistory(
        user_id=current_user.id,
        website=website,
        query=query,
        results=results,
        notes=notes
    )
    
    db.session.add(history_entry)
    db.session.commit()
    
    flash('Search saved to history!', 'success')
    return redirect(url_for('main.search_history'))

@bp.route('/delete-search/<int:search_id>')
@login_required
def delete_search(search_id):
    search = UserSearchHistory.query.get_or_404(search_id)
    
    # Ensure the search belongs to the current user
    if search.user_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('main.search_history'))
    
    db.session.delete(search)
    db.session.commit()
    
    flash('Search deleted from history.', 'success')
    return redirect(url_for('main.search_history')) 